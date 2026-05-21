# SRE Kubernetes Agent with Google A2A Protocol

AI-powered Site Reliability Engineering agent for Kubernetes with Ollama LLM integration and OpenTelemetry observability.

## Architecture

```
┌─────────────────┐
│   User/Client   │
└────────┬────────┘
         │ HTTP/A2A Protocol
         ▼
┌─────────────────────────────────┐
│   SRE Agent (FastAPI)           │
│   - A2A Protocol endpoints      │
│   - Agent Card (Well-Known URI) │
│   - OpenTelemetry tracing       │
└────┬──────────────────┬─────────┘
     │                  │
     │ Ollama API       │ Kubernetes API
     ▼                  ▼
┌──────────┐      ┌──────────────┐
│  Ollama  │      │  Kubernetes  │
│  (LLM)   │      │   Cluster    │
└──────────┘      └──────────────┘
     │
     │ OTLP traces
     ▼
┌──────────────┐
│   Jaeger     │
│ (Tracing UI) │
└──────────────┘
```

## Features

- **Google A2A Protocol**: Full implementation with Agent Card discovery
- **Ollama Integration**: Local LLM inference (llama3, mistral, codellama)
- **Kubernetes Tools**: kubectl operations, cluster health analysis, pod diagnostics
- **Observability**: OpenTelemetry traces exported to Jaeger
- **kagent.dev CRD**: Declarative agent configuration

## Quick Start

### 1. Build the Agent Image

```bash
cd /home/sre21.05.2026/agent
docker build -t sre-agent:latest .
```

### 2. Deploy to Kubernetes

```bash
# Create namespace and deploy observability stack
kubectl apply -f /home/sre21.05.2026/manifests/observability.yaml

# Deploy Ollama LLM
kubectl apply -f /home/sre21.05.2026/manifests/ollama.yaml

# Wait for Ollama to be ready
kubectl wait --for=condition=ready pod -l app=ollama -n kagent-system --timeout=300s

# Pull the LLM model (this may take a few minutes)
kubectl apply -f /home/sre21.05.2026/manifests/ollama.yaml

# Deploy the SRE agent
kubectl apply -f /home/sre21.05.2026/manifests/deployment.yaml

# Apply kagent CRD (if kagent operator is installed)
kubectl apply -f /home/sre21.05.2026/manifests/agent-crd.yaml
```

### 3. Verify Deployment

```bash
# Check agent status
kubectl get pods -n kagent-system

# Check agent logs
kubectl logs -n kagent-system -l app=sre-agent -f

# Port-forward to access the agent
kubectl port-forward -n kagent-system svc/sre-agent 8080:8080
```

## Agent Card Discovery (Well-Known URI)

The agent exposes its capabilities via the A2A Protocol Agent Card at:

```bash
# Get Agent Card
curl http://localhost:8080/.well-known/agent-card.json | jq
```

**Agent Card includes:**
- Agent name, description, version
- Available tools and their parameters
- Endpoints (agent, health, metrics)
- Capabilities (streaming, async, observability)
- Authentication requirements
- LLM backend information

## Using the Agent

### Example 1: Analyze Cluster Health

```bash
curl -X POST http://localhost:8080/v1/agent \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Analyze the cluster health"
      }
    ],
    "tools": ["analyze_cluster_health"],
    "stream": false
  }' | jq
```

### Example 2: Diagnose Pod Issues

```bash
curl -X POST http://localhost:8080/v1/agent \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Why is my pod failing?"
      }
    ],
    "context": {
      "pod_name": "my-app-pod",
      "namespace": "default"
    }
  }' | jq
```

### Example 3: Get Pod Logs

```bash
curl -X POST http://localhost:8080/v1/tools/kubectl_logs \
  -H "Content-Type: application/json" \
  -d '{
    "pod_name": "my-app-pod",
    "namespace": "default",
    "tail": 50
  }' | jq
```

### Example 4: Streaming Response

```bash
curl -X POST http://localhost:8080/v1/agent \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Explain the current cluster state"
      }
    ],
    "stream": true
  }'
```

## Observability

### View Traces in Jaeger

```bash
# Port-forward Jaeger UI
kubectl port-forward -n observability svc/jaeger-ui 16686:16686

# Open in browser
open http://localhost:16686
```

**Trace information includes:**
- Agent request processing
- Tool execution (kubectl commands)
- Ollama LLM generation
- Kubernetes API calls

### Prometheus Metrics

```bash
# Get metrics
curl http://localhost:8080/metrics
```

## Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `kubectl_get` | Get Kubernetes resources | resource_type, namespace, name |
| `kubectl_describe` | Describe resource in detail | resource_type, name, namespace |
| `kubectl_logs` | Get pod logs | pod_name, namespace, container, tail |
| `kubectl_apply` | Apply manifest | manifest, namespace |
| `kubectl_delete` | Delete resource | resource_type, name, namespace |
| `analyze_cluster_health` | Analyze cluster health | include_metrics |
| `diagnose_pod_issues` | Diagnose pod issues | pod_name, namespace |
| `check_resource_quotas` | Check resource quotas | namespace |

## Configuration

### Environment Variables

Set in `manifests/deployment.yaml` ConfigMap:

- `OLLAMA_BASE_URL`: Ollama service URL (default: `http://ollama.kagent-system.svc.cluster.local:11434`)
- `OLLAMA_MODEL`: LLM model to use (default: `llama3`)
- `OTEL_EXPORTER_OTLP_ENDPOINT`: OpenTelemetry collector endpoint
- `OTEL_SERVICE_NAME`: Service name for traces

### kagent CRD Configuration

The `manifests/agent-crd.yaml` defines the agent using kagent.dev API:

```yaml
apiVersion: kagent.dev/v1alpha1
kind: Agent
metadata:
  name: sre-kubernetes-agent
spec:
  llm:
    provider: ollama
    model: llama3
  protocol:
    type: a2a
    agentCard:
      wellKnownUri: "/.well-known/agent-card.json"
  tools:
    - name: kubectl_get
      enabled: true
  observability:
    traces:
      enabled: true
      endpoint: "http://jaeger-collector.observability.svc.cluster.local:4317"
```

## Development

### Local Testing

```bash
# Install dependencies
cd /home/sre21.05.2026/agent
pip install -r requirements.txt

# Set environment variables
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=llama3
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Run locally
python main.py
```

### Testing with Ollama Locally

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model
ollama pull llama3

# Run Ollama
ollama serve
```

## Troubleshooting

### Agent not starting

```bash
# Check logs
kubectl logs -n kagent-system -l app=sre-agent

# Check Ollama connectivity
kubectl exec -n kagent-system deploy/sre-agent -- curl http://ollama:11434/api/tags
```

### Ollama model not loaded

```bash
# Check Ollama logs
kubectl logs -n kagent-system -l app=ollama

# Manually pull model
kubectl exec -n kagent-system deploy/ollama -- ollama pull llama3
```

### Traces not appearing in Jaeger

```bash
# Check Jaeger collector
kubectl logs -n observability -l app=jaeger

# Verify OTLP endpoint
kubectl exec -n kagent-system deploy/sre-agent -- \
  curl http://jaeger-collector.observability.svc.cluster.local:4317
```

## API Reference

### GET /.well-known/agent-card.json

Returns the Agent Card with capabilities and metadata.

**Response:**
```json
{
  "name": "SRE Kubernetes Agent",
  "version": "1.0.0",
  "capabilities": {...},
  "tools": [...],
  "endpoints": {...}
}
```

### POST /v1/agent

Main agent endpoint for conversational interaction.

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "query"}
  ],
  "tools": ["tool_name"],
  "stream": false
}
```

**Response:**
```json
{
  "message": {
    "role": "assistant",
    "content": "response",
    "timestamp": "2026-05-21T10:00:00Z"
  },
  "tool_calls": [...],
  "trace_id": "abc123..."
}
```

### POST /v1/tools/{tool_name}

Execute a specific tool directly.

**Request:**
```json
{
  "param1": "value1",
  "param2": "value2"
}
```

### GET /health

Health check endpoint.

### GET /metrics

Prometheus metrics endpoint.

## Security

- **RBAC**: Agent runs with limited ServiceAccount permissions
- **Authentication**: Bearer token authentication via Kubernetes ServiceAccount
- **Network Policies**: Recommended to restrict agent network access
- **Tool Approval**: Destructive operations (apply, delete) can require approval in kagent CRD

## License

Apache-2.0

## Support

For issues and questions, refer to the kagent.dev documentation or Kubernetes cluster administrator.
