# app/main.py
import os
import uuid
import logging
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Any

from app.agent_card import build_agent_card
from app.handlers import route_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SRE Kubernetes Agent", version="1.0.0")

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

    # Извлекаем текст из первого parts элемента
    text = ""
    for part in payload.message.parts:
        if part.type == "text":
            text = part.text
            break

    logger.info(f"Task {task_id}: {text!r}")

    # Роутим и выполняем
    result = route_task(text)

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


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Получить статус/результат задачи по ID."""
    if task_id not in tasks:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return tasks[task_id]


@app.get("/health")
async def health():
    return {"status": "ok", "agent": AGENT_CARD.name}
