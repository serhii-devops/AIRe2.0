#!/usr/bin/env python3
"""
SRE Kubernetes Agent with Google A2A Protocol support
Integrates with Ollama LLM and provides observability via OpenTelemetry
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
import httpx
from kubernetes import client, config
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenTelemetry
resource = Resource.create({"service.name": "sre-kubernetes-agent"})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

# Configure OTLP exporter (fallback to console if not available)
otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
if otlp_endpoint:
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))
else:
    console_exporter = ConsoleSpanExporter()
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(console_exporter))

# Initialize FastAPI
app = FastAPI(title="SRE Kubernetes Agent", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)

# Ollama configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://0.0.0.0:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Initialize Kubernetes client
try:
    config.load_incluster_config()
except:
    try:
        config.load_kube_config()
    except:
        logger.warning("Could not load Kubernetes config")

k8s_v1 = client.CoreV1Api()
k8s_apps = client.AppsV1Api()


# Pydantic models for A2A Protocol
class ToolParameter(BaseModel):
    type: str
    description: str
    default: Optional[Any] = None


class Tool(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]


class Message(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None


class AgentRequest(BaseModel):
    messages: List[Message]
    tools: Optional[List[str]] = None
    stream: bool = False
    context: Optional[Dict[str, Any]] = None


class AgentResponse(BaseModel):
    message: Message
    tool_calls: Optional[List[Dict[str, Any]]] = None
    trace_id: Optional[str] = None


# Tool implementations
class KubernetesTools:
    @staticmethod
    @tracer.start_as_current_span("kubectl_get")
    def kubectl_get(resource_type: str, namespace: str = "default", name: Optional[str] = None) -> Dict[str, Any]:
        """Get Kubernetes resources"""
        try:
            if resource_type == "pod":
                if name:
                    pod = k8s_v1.read_namespaced_pod(name, namespace)
                    return {"status": "success", "data": pod.to_dict()}
                else:
                    pods = k8s_v1.list_namespaced_pod(namespace)
                    return {"status": "success", "data": [p.to_dict() for p in pods.items]}
            elif resource_type == "deployment":
                if name:
                    dep = k8s_apps.read_namespaced_deployment(name, namespace)
                    return {"status": "success", "data": dep.to_dict()}
                else:
                    deps = k8s_apps.list_namespaced_deployment(namespace)
                    return {"status": "success", "data": [d.to_dict() for d in deps.items]}
            elif resource_type == "service":
                if name:
                    svc = k8s_v1.read_namespaced_service(name, namespace)
                    return {"status": "success", "data": svc.to_dict()}
                else:
                    svcs = k8s_v1.list_namespaced_service(namespace)
                    return {"status": "success", "data": [s.to_dict() for s in svcs.items]}
            else:
                return {"status": "error", "message": f"Unsupported resource type: {resource_type}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    @tracer.start_as_current_span("kubectl_logs")
    def kubectl_logs(pod_name: str, namespace: str = "default", container: Optional[str] = None, tail: int = 100) -> Dict[str, Any]:
        """Get pod logs"""
        try:
            logs = k8s_v1.read_namespaced_pod_log(
                pod_name, namespace, container=container, tail_lines=tail
            )
            return {"status": "success", "data": logs}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    @tracer.start_as_current_span("kubectl_describe")
    def kubectl_describe(resource_type: str, name: str, namespace: str = "default") -> Dict[str, Any]:
        """Describe Kubernetes resource"""
        try:
            if resource_type == "pod":
                pod = k8s_v1.read_namespaced_pod(name, namespace)
                return {"status": "success", "data": pod.to_dict()}
            elif resource_type == "deployment":
                dep = k8s_apps.read_namespaced_deployment(name, namespace)
                return {"status": "success", "data": dep.to_dict()}
            else:
                return {"status": "error", "message": f"Unsupported resource type: {resource_type}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    @tracer.start_as_current_span("analyze_cluster_health")
    def analyze_cluster_health(include_metrics: bool = True) -> Dict[str, Any]:
        """Analyze cluster health"""
        try:
            nodes = k8s_v1.list_node()
            pods = k8s_v1.list_pod_for_all_namespaces()

            health_data = {
                "nodes": {
                    "total": len(nodes.items),
                    "ready": sum(1 for n in nodes.items if any(c.type == "Ready" and c.status == "True" for c in n.status.conditions))
                },
                "pods": {
                    "total": len(pods.items),
                    "running": sum(1 for p in pods.items if p.status.phase == "Running"),
                    "pending": sum(1 for p in pods.items if p.status.phase == "Pending"),
                    "failed": sum(1 for p in pods.items if p.status.phase == "Failed")
                }
            }

            return {"status": "success", "data": health_data}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    @tracer.start_as_current_span("diagnose_pod_issues")
    def diagnose_pod_issues(pod_name: str, namespace: str = "default") -> Dict[str, Any]:
        """Diagnose pod issues"""
        try:
            pod = k8s_v1.read_namespaced_pod(pod_name, namespace)
            issues = []

            # Check pod status
            if pod.status.phase != "Running":
                issues.append(f"Pod is in {pod.status.phase} state")

            # Check container statuses
            if pod.status.container_statuses:
                for cs in pod.status.container_statuses:
                    if cs.state.waiting:
                        issues.append(f"Container {cs.name}: {cs.state.waiting.reason} - {cs.state.waiting.message}")
                    if cs.state.terminated:
                        issues.append(f"Container {cs.name}: Terminated with exit code {cs.state.terminated.exit_code}")
                    if cs.restart_count > 0:
                        issues.append(f"Container {cs.name}: Restarted {cs.restart_count} times")

            # Check events
            events = k8s_v1.list_namespaced_event(namespace, field_selector=f"involvedObject.name={pod_name}")
            warning_events = [e for e in events.items if e.type == "Warning"]

            return {
                "status": "success",
                "data": {
                    "pod_name": pod_name,
                    "namespace": namespace,
                    "phase": pod.status.phase,
                    "issues": issues,
                    "warning_events": [{"reason": e.reason, "message": e.message} for e in warning_events[-5:]]
                }
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Ollama integration
class OllamaClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model
        self.client = httpx.AsyncClient(timeout=120.0)

    @tracer.start_as_current_span("ollama_generate")
    async def generate(self, prompt: str, system: Optional[str] = None, stream: bool = False):
        """Generate response from Ollama"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream
        }
        if system:
            payload["system"] = system

        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()

            if stream:
                return response
            else:
                return response.json()
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise


ollama_client = OllamaClient(OLLAMA_BASE_URL, OLLAMA_MODEL)


# A2A Protocol endpoints
@app.get("/.well-known/agent-card.json")
async def get_agent_card():
    """Serve Agent Card via Well-Known URI"""
    with open("/app/.well-known/agent-card.json", "r") as f:
        agent_card = json.load(f)
    return JSONResponse(content=agent_card)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return {"message": "Metrics endpoint - integrate with prometheus_client"}


@app.post("/v1/agent")
@tracer.start_as_current_span("agent_request")
async def agent_endpoint(request: AgentRequest):
    """Main agent endpoint following A2A Protocol"""
    span = trace.get_current_span()
    trace_id = format(span.get_span_context().trace_id, '032x')

    # Build context for LLM
    system_prompt = """You are an SRE (Site Reliability Engineering) agent for Kubernetes clusters.
You have access to kubectl commands and cluster analysis tools.
When users ask about cluster issues, use the available tools to diagnose and provide solutions.
Always explain your reasoning and provide actionable recommendations."""

    # Extract last user message
    user_message = request.messages[-1].content if request.messages else ""

    # Check if tools should be used
    tool_results = []
    if request.tools:
        for tool_name in request.tools:
            # Simple tool routing (in production, use LLM to decide)
            if tool_name == "analyze_cluster_health":
                result = KubernetesTools.analyze_cluster_health()
                tool_results.append({"tool": tool_name, "result": result})

    # Build prompt with tool results
    prompt = f"User query: {user_message}\n\n"
    if tool_results:
        prompt += "Tool results:\n"
        for tr in tool_results:
            prompt += f"- {tr['tool']}: {json.dumps(tr['result'], indent=2)}\n"
    prompt += "\nProvide a helpful response based on the information above."

    # Generate response from Ollama
    try:
        if request.stream:
            # Streaming response
            async def generate_stream():
                response = await ollama_client.generate(prompt, system=system_prompt, stream=True)
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "response" in data:
                            yield f"data: {json.dumps({'content': data['response']})}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(generate_stream(), media_type="text/event-stream")
        else:
            # Non-streaming response
            response = await ollama_client.generate(prompt, system=system_prompt)

            return AgentResponse(
                message=Message(
                    role="assistant",
                    content=response.get("response", ""),
                    timestamp=datetime.utcnow().isoformat()
                ),
                tool_calls=tool_results if tool_results else None,
                trace_id=trace_id
            )
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/tools/{tool_name}")
@tracer.start_as_current_span("tool_execution")
async def execute_tool(tool_name: str, params: Dict[str, Any]):
    """Execute a specific tool"""
    tools_map = {
        "kubectl_get": KubernetesTools.kubectl_get,
        "kubectl_logs": KubernetesTools.kubectl_logs,
        "kubectl_describe": KubernetesTools.kubectl_describe,
        "analyze_cluster_health": KubernetesTools.analyze_cluster_health,
        "diagnose_pod_issues": KubernetesTools.diagnose_pod_issues,
    }

    if tool_name not in tools_map:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")

    try:
        result = tools_map[tool_name](**params)
        return result
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
