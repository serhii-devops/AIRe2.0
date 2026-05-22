# app/k8s_client.py
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import time
from contextlib import contextmanager

from app.logging_config import get_logger
from app.observability import k8s_api_calls, k8s_api_duration, k8s_api_errors, get_tracer

logger = get_logger(__name__)
tracer = get_tracer()

def get_k8s_clients():
    """Автоопределение: внутри кластера или локально (kubeconfig)."""
    try:
        config.load_incluster_config()
        logger.info("k8s_config_loaded", mode="incluster")
    except config.ConfigException:
        config.load_kube_config()
        logger.info("k8s_config_loaded", mode="kubeconfig")

    return client.CoreV1Api(), client.AppsV1Api()

core_v1, apps_v1 = get_k8s_clients()


@contextmanager
def track_k8s_operation(operation: str):
    """Context manager to track K8s API calls with metrics and tracing."""
    start_time = time.time()
    with tracer.start_as_current_span(f"k8s.{operation}") as span:
        span.set_attribute("k8s.operation", operation)
        try:
            yield
            duration = time.time() - start_time
            k8s_api_calls.labels(operation=operation, status="success").inc()
            k8s_api_duration.labels(operation=operation).observe(duration)
            logger.info("k8s_api_call", operation=operation, duration=duration, status="success")
        except ApiException as e:
            duration = time.time() - start_time
            k8s_api_calls.labels(operation=operation, status="error").inc()
            k8s_api_errors.labels(operation=operation, error_code=str(e.status)).inc()
            k8s_api_duration.labels(operation=operation).observe(duration)
            span.set_attribute("error", True)
            span.set_attribute("error.code", e.status)
            logger.error("k8s_api_error", operation=operation, duration=duration, error_code=e.status, reason=e.reason)
            raise


def check_pod_health(namespace: str = "default") -> dict:
    """Возвращает статус всех подов в неймспейсе."""
    with track_k8s_operation("list_pods"):
        try:
            pods = core_v1.list_namespaced_pod(namespace=namespace)
            result = []
            for pod in pods.items:
                containers = pod.status.container_statuses or []
                restarts = sum(c.restart_count for c in containers)
                result.append({
                    "name": pod.metadata.name,
                    "phase": pod.status.phase,
                    "restarts": restarts,
                    "ready": all(c.ready for c in containers) if containers else False,
                    "node": pod.spec.node_name,
                })
            logger.info("pod_health_check", namespace=namespace, pod_count=len(result))
            return {"namespace": namespace, "pods": result, "total": len(result)}
        except ApiException as e:
            return {"error": f"K8s API error: {e.status} {e.reason}"}


def get_pod_logs(namespace: str, pod_name: str, lines: int = 50) -> dict:
    """Возвращает последние N строк логов из пода."""
    with track_k8s_operation("get_pod_logs"):
        try:
            logs = core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                tail_lines=lines,
                timestamps=True,
            )
            logger.info("pod_logs_retrieved", pod=pod_name, namespace=namespace, lines=lines)
            return {
                "pod": pod_name,
                "namespace": namespace,
                "lines": lines,
                "logs": logs,
            }
        except ApiException as e:
            return {"error": f"K8s API error: {e.status} {e.reason}"}


def scale_deployment(namespace: str, deployment_name: str, replicas: int) -> dict:
    """Масштабирует деплоймент до указанного числа реплик."""
    with track_k8s_operation("scale_deployment"):
        try:
            # Patch только поле replicas
            body = {"spec": {"replicas": replicas}}
            apps_v1.patch_namespaced_deployment_scale(
                name=deployment_name,
                namespace=namespace,
                body=body,
            )
            logger.info("deployment_scaled", deployment=deployment_name, namespace=namespace, replicas=replicas)
            return {
                "deployment": deployment_name,
                "namespace": namespace,
                "replicas": replicas,
                "status": "scaled",
            }
        except ApiException as e:
            return {"error": f"K8s API error: {e.status} {e.reason}"}


def check_k8s_connectivity() -> bool:
    """Check if K8s API is accessible."""
    try:
        core_v1.get_api_resources()
        return True
    except Exception as e:
        logger.error("k8s_connectivity_check_failed", error=str(e))
        return False
