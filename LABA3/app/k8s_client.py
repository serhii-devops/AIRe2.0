# app/k8s_client.py
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import logging
import os

logger = logging.getLogger(__name__)

def get_k8s_clients():
    """Автоопределение: внутри кластера или локально (kubeconfig)."""
    try:
        config.load_incluster_config()
        logger.info("Running inside Kubernetes cluster")
    except config.ConfigException:
        config.load_kube_config()
        logger.info("Running with local kubeconfig")

    return client.CoreV1Api(), client.AppsV1Api()

core_v1, apps_v1 = get_k8s_clients()


def check_pod_health(namespace: str = "default") -> dict:
    """Возвращает статус всех подов в неймспейсе."""
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
        return {"namespace": namespace, "pods": result, "total": len(result)}
    except ApiException as e:
        return {"error": f"K8s API error: {e.status} {e.reason}"}


def get_pod_logs(namespace: str, pod_name: str, lines: int = 50) -> dict:
    """Возвращает последние N строк логов из пода."""
    try:
        logs = core_v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=lines,
            timestamps=True,
        )
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
    try:
        # Patch только поле replicas
        body = {"spec": {"replicas": replicas}}
        apps_v1.patch_namespaced_deployment_scale(
            name=deployment_name,
            namespace=namespace,
            body=body,
        )
        return {
            "deployment": deployment_name,
            "namespace": namespace,
            "replicas": replicas,
            "status": "scaled",
        }
    except ApiException as e:
        return {"error": f"K8s API error: {e.status} {e.reason}"}
