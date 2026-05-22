# app/handlers.py
import json
import re
from app.k8s_client import check_pod_health, get_pod_logs, scale_deployment
from app.logging_config import get_logger
from app.observability import get_tracer

logger = get_logger(__name__)
tracer = get_tracer()

def route_task(text: str) -> dict:
    """
    Роутер задач на основе ключевых слов.
    В продакшне здесь был бы LLM для intent detection.
    """
    text_lower = text.lower()

    with tracer.start_as_current_span("route_task") as span:
        span.set_attribute("task.text", text)

        logger.info("routing_task", text=text)

        # --- check pod health ---
        if any(kw in text_lower for kw in ["pod health", "pods in", "pod status", "crashing pods"]):
            namespace = _extract_namespace(text) or "default"
            span.set_attribute("task.type", "check_health")
            span.set_attribute("task.namespace", namespace)
            logger.info("task_routed", task_type="check_health", namespace=namespace)
            return check_pod_health(namespace)

        # --- get logs ---
        if any(kw in text_lower for kw in ["logs", "log from"]):
            namespace = _extract_namespace(text) or "default"
            pod = _extract_pod(text)
            lines = _extract_lines(text) or 50

            span.set_attribute("task.type", "get_logs")
            span.set_attribute("task.namespace", namespace)
            span.set_attribute("task.pod", pod or "unknown")

            if not pod:
                logger.warning("task_routing_failed", reason="pod_name_missing", text=text)
                return {"error": "Pod name not found in request. Example: 'get logs from pod nginx-abc in namespace default'"}

            logger.info("task_routed", task_type="get_logs", namespace=namespace, pod=pod, lines=lines)
            return get_pod_logs(namespace, pod, lines)

        # --- scale ---
        if any(kw in text_lower for kw in ["scale", "replicas"]):
            namespace = _extract_namespace(text) or "default"
            deployment = _extract_deployment(text)
            replicas = _extract_replicas(text)

            span.set_attribute("task.type", "scale")
            span.set_attribute("task.namespace", namespace)
            span.set_attribute("task.deployment", deployment or "unknown")

            if not deployment or replicas is None:
                logger.warning("task_routing_failed", reason="missing_params", text=text)
                return {"error": "Need deployment name and replica count. Example: 'scale deployment api to 3 replicas in namespace production'"}

            logger.info("task_routed", task_type="scale", namespace=namespace, deployment=deployment, replicas=replicas)
            return scale_deployment(namespace, deployment, replicas)

        logger.warning("task_routing_failed", reason="unknown_task", text=text)
        span.set_attribute("task.type", "unknown")
        return {
            "error": "Unknown task. Supported: check pod health, get logs, scale deployment.",
            "hint": "Example: 'Check pods in namespace production'",
        }


# --- helpers ---
def _extract_namespace(text: str) -> str | None:
    m = re.search(r'namespace\s+(\S+)', text, re.IGNORECASE)
    return m.group(1) if m else None

def _extract_pod(text: str) -> str | None:
    m = re.search(r'pod[s]?\s+(\S+)', text, re.IGNORECASE)
    return m.group(1) if m else None

def _extract_deployment(text: str) -> str | None:
    m = re.search(r'deployment\s+(\S+)', text, re.IGNORECASE)
    return m.group(1) if m else None

def _extract_lines(text: str) -> int | None:
    m = re.search(r'(\d+)\s+lines?', text, re.IGNORECASE)
    return int(m.group(1)) if m else None

def _extract_replicas(text: str) -> int | None:
    m = re.search(r'(\d+)\s+replica', text, re.IGNORECASE)
    return int(m.group(1)) if m else None
