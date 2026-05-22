# app/main.py
import os
import uuid
import time
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from typing import Optional, Any

from app.agent_card import build_agent_card
from app.handlers import route_task
from app.logging_config import setup_logging, get_logger, set_task_id, set_trace_id, clear_context
from app.observability import (
    setup_opentelemetry,
    prometheus_metrics,
    task_counter,
    task_duration,
    active_tasks,
    CONTENT_TYPE_LATEST
)
from app.k8s_client import check_k8s_connectivity

# Setup logging first
setup_logging()
logger = get_logger(__name__)

app = FastAPI(title="SRE Kubernetes Agent", version="1.0.0")

# Setup OpenTelemetry
setup_opentelemetry(app)

# URL агента — берём из env или дефолт
BASE_URL = os.getenv("AGENT_BASE_URL", "http://sre-agent.default.svc.cluster.local")
AGENT_CARD = build_agent_card(BASE_URL)


# ──────────────────────────────────────────────
# A2A Protocol Models
# ──────────────────────────────────────────────

class TextPart(BaseModel):
    type: str = "text"
    text: str

class Message(BaseModel):
    role: str
    parts: list[TextPart]

class TaskSendRequest(BaseModel):
    id: Optional[str] = None
    message: Message

class TaskState(BaseModel):
    id: str
    status: dict
    result: Optional[Any] = None
    createdAt: str
    updatedAt: str


# In-memory store задач (для продакшна — Redis)
tasks: dict[str, dict] = {}


# ──────────────────────────────────────────────
# Well-Known endpoint — Agent Card
# ──────────────────────────────────────────────

@app.get("/.well-known/agent.json")
async def get_agent_card():
    """
    Стандартный Well-Known URI для Agent Card.
    Используется другими агентами и оркестраторами для autodiscovery.
    """
    return AGENT_CARD.model_dump()


# ──────────────────────────────────────────────
# A2A Task endpoints
# ──────────────────────────────────────────────

@app.post("/tasks/send")
async def send_task(payload: TaskSendRequest):
    """Принять задачу и вернуть результат."""
    task_id = payload.id or str(uuid.uuid4())
    now = datetime.utcnow().isoformat() + "Z"

    # Set correlation IDs for logging
    set_task_id(task_id)
    trace_id = str(uuid.uuid4())
    set_trace_id(trace_id)

    # Извлекаем текст из первого parts элемента
    text = ""
    for part in payload.message.parts:
        if part.type == "text":
            text = part.text
            break

    logger.info("task_received", task_id=task_id, text=text)

    # Track metrics
    active_tasks.inc()
    start_time = time.time()

    try:
        # Роутим и выполняем
        result = route_task(text)

        # Determine task type from text
        task_type = "unknown"
        if "pod health" in text.lower() or "pod status" in text.lower():
            task_type = "check_health"
        elif "logs" in text.lower():
            task_type = "get_logs"
        elif "scale" in text.lower():
            task_type = "scale"

        status = "error" if "error" in result else "success"
        task_counter.labels(status=status, task_type=task_type).inc()

        duration = time.time() - start_time
        task_duration.labels(task_type=task_type).observe(duration)

        logger.info("task_completed", task_id=task_id, status=status, duration=duration, task_type=task_type)

        task = {
            "id": task_id,
            "status": {"state": "completed"},
            "result": {
                "role": "agent",
                "parts": [{"type": "text", "text": str(result)}],
            },
            "createdAt": now,
            "updatedAt": datetime.utcnow().isoformat() + "Z",
        }
        tasks[task_id] = task
        return task
    finally:
        active_tasks.dec()
        clear_context()


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Получить статус/результат задачи по ID."""
    set_task_id(task_id)
    if task_id not in tasks:
        logger.warning("task_not_found", task_id=task_id)
        clear_context()
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    logger.info("task_retrieved", task_id=task_id)
    clear_context()
    return tasks[task_id]


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=prometheus_metrics(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
async def health():
    """Basic health check."""
    return {"status": "ok", "agent": AGENT_CARD.name}


@app.get("/health/live")
async def liveness():
    """Liveness probe - is the service running?"""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@app.get("/health/ready")
async def readiness():
    """Readiness probe - can the service handle requests?"""
    k8s_ready = check_k8s_connectivity()

    if not k8s_ready:
        logger.error("readiness_check_failed", reason="k8s_api_unreachable")
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "reason": "K8s API unreachable",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    return {
        "status": "ready",
        "k8s_api": "connected",
        "timestamp": datetime.utcnow().isoformat()
    }
