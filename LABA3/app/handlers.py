# app/handlers.py
import json
import re
from app.k8s_client import check_pod_health, get_pod_logs, scale_deployment

def route_task(text: str) -> dict:
    """
    Простой роутер на основе ключевых слов.
    В продакшне здесь был бы LLM для intent detection.
    """
    text_lower = text.lower()

    # --- check pod health ---
    if any(kw in text_lower for kw in ["pod health", "pods in", "pod status", "crashing pods"]):
        namespace = _extract_namespace(text) or "default"
        return check_pod_health(namespace)

    # --- get logs ---
    if any(kw in text_lower for kw in ["logs", "log from"]):
        namespace = _extract_namespace(text) or "default"
        pod = _extract_pod(text)
        lines = _extract_lines(text) or 50
        if not pod:
            return {"error": "Pod name not found in request. Example: 'get logs from pod nginx-abc in namespace default'"}
        return get_pod_logs(namespace, pod, lines)

    # --- scale ---
    if any(kw in text_lower for kw in ["scale", "replicas"]):
        namespace = _extract_namespace(text) or "default"
        deployment = _extract_deployment(text)
        replicas = _extract_replicas(text)
        if not deployment or replicas is None:
            return {"error": "Need deployment name and replica count. Example: 'scale deployment api to 3 replicas in namespace production'"}
        return scale_deployment(namespace, deployment, replicas)

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
