# SRE Kubernetes Agent - Полное руководство

## 📋 Обзор

Реализован AI-агент для Site Reliability Engineering с полной поддержкой **Google A2A Protocol**, интеграцией с **Ollama LLM** и **OpenTelemetry observability**.

## 🎯 Ключевые возможности

### 1. Google A2A Protocol
- ✅ **Agent Card** - JSON-описание возможностей агента
- ✅ **Well-Known URI** - стандартный путь `/.well-known/agent-card.json`
- ✅ **Стандартные endpoints** - `/v1/agent`, `/v1/tools/{tool_name}`
- ✅ **Streaming** - поддержка потоковых ответов
- ✅ **Async** - асинхронная обработка запросов

### 2. Ollama LLM Integration
- Локальный LLM (llama3, mistral, codellama)
- Асинхронные запросы к Ollama API
- Поддержка streaming генерации
- Настраиваемые параметры (temperature, max_tokens)

### 3. Kubernetes Tools (8 инструментов)
- `kubectl_get` - получение ресурсов
- `kubectl_describe` - детальное описание
- `kubectl_logs` - логи подов
- `kubectl_apply` - применение манифестов
- `kubectl_delete` - удаление ресурсов
- `analyze_cluster_health` - анализ здоровья кластера
- `diagnose_pod_issues` - диагностика проблем подов
- `check_resource_quotas` - проверка квот

### 4. Observability
- **OpenTelemetry** трейсинг всех операций
- **Jaeger** для визуализации трейсов
- **Trace ID** в каждом ответе агента
- **Prometheus** metrics endpoint

### 5. kagent.dev CRD
- Декларативная конфигурация агента
- API версия: `kagent.dev/v1alpha1`
- Kind: `Agent`
- Полная спецификация LLM, tools, observability

## 📁 Структура проекта

```
/home/sre21.05.2026/
│
├── 📄 README.md                    # Основная документация
├── 📄 QUICKSTART.md                # Быстрый старт (5 минут)
├── 🚀 deploy.sh                    # Скрипт развертывания
├── 🧪 test_agent.py                # Тесты A2A Protocol
│
├── 🤖 agent/                       # Код агента
│   ├── main.py                     # FastAPI + A2A Protocol + OpenTelemetry
│   ├── Dockerfile                  # Контейнер с kubectl
│   └── requirements.txt            # Python зависимости
│
├── 🔍 .well-known/                 # A2A Protocol
│   └── agent-card.json             # Agent Card (возможности агента)
│
├── ☸️  manifests/                  # Kubernetes манифесты
│   ├── deployment.yaml             # Deployment + Service + RBAC
│   ├── agent-crd.yaml              # kagent.dev/v1alpha1 Agent CRD
│   ├── ollama.yaml                 # Ollama LLM deployment
│   └── observability.yaml          # Jaeger tracing
│
├── 📚 docs/                        # Документация
│   ├── A2A_PROTOCOL.md             # Детали A2A Protocol
│   └── EXAMPLES.md                 # Примеры использования
│
└── 📦 helm/                        # Helm charts (для будущего)
    └── sre-agent/
```

## 🚀 Быстрый старт

### Шаг 1: Сборка образа

```bash
cd /home/sre21.05.2026/agent
docker build -t sre-agent:latest .

# Для kind
kind load docker-image sre-agent:latest

# Для minikube
minikube image load sre-agent:latest
```

### Шаг 2: Развертывание

```bash
cd /home/sre21.05.2026
./deploy.sh
```

Скрипт автоматически:
1. Создаст namespaces (kagent-system, observability)
2. Развернет Jaeger для трейсинга
3. Развернет Ollama LLM
4. Загрузит модель llama3
5. Развернет SRE агента
6. Применит kagent CRD

### Шаг 3: Проверка

```bash
# Статус подов
kubectl get pods -n kagent-system
kubectl get pods -n observability

# Логи агента
kubectl logs -n kagent-system -l app=sre-agent -f
```

### Шаг 4: Доступ к агенту

```bash
# Port-forward
kubectl port-forward -n kagent-system svc/sre-agent 8080:8080 &
kubectl port-forward -n observability svc/jaeger-ui 16686:16686 &
```

### Шаг 5: Получение Agent Card (Well-Known URI)

```bash
curl http://localhost:8080/.well-known/agent-card.json | jq
```

**Ответ:**
```json
{
  "$schema": "https://a2a.google/schemas/agent-card/v1",
  "name": "SRE Kubernetes Agent",
  "version": "1.0.0",
  "capabilities": {
    "streaming": true,
    "async": true,
    "observability": {
      "traces": true,
      "metrics": true,
      "logs": true
    }
  },
  "endpoints": {
    "agent": "http://sre-agent.../v1/agent",
    "health": "http://sre-agent.../health",
    "metrics": "http://sre-agent.../metrics"
  },
  "tools": [
    {"name": "kubectl_get", ...},
    {"name": "kubectl_logs", ...},
    {"name": "analyze_cluster_health", ...}
  ]
}
```

### Шаг 6: Тестирование

```bash
python3 test_agent.py
```

Тесты проверяют:
- ✅ Agent Card (Well-Known URI)
- ✅ Health endpoint
- ✅ Cluster health analysis
- ✅ Direct tool execution
- ✅ Streaming response

## 💡 Примеры использования

### Пример 1: Анализ кластера

```bash
curl -X POST http://localhost:8080/v1/agent \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Analyze cluster health"}
    ],
    "tools": ["analyze_cluster_health"]
  }' | jq
```

### Пример 2: Диагностика пода

```bash
curl -X POST http://localhost:8080/v1/agent \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Why is my pod failing?"}
    ],
    "context": {
      "pod_name": "my-app-pod",
      "namespace": "default"
    }
  }' | jq
```

### Пример 3: Получение логов

```bash
curl -X POST http://localhost:8080/v1/tools/kubectl_logs \
  -H "Content-Type: application/json" \
  -d '{
    "pod_name": "my-app-pod",
    "namespace": "default",
    "tail": 50
  }' | jq
```

### Пример 4: Streaming ответ

```bash
curl -X POST http://localhost:8080/v1/agent \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Explain Kubernetes pod lifecycle"}
    ],
    "stream": true
  }'
```

## 🔍 Observability - Просмотр трейсов

```bash
# Открыть Jaeger UI
open http://localhost:16686
```

В Jaeger вы увидите:
- **Service**: `sre-kubernetes-agent`
- **Operations**: `agent_request`, `kubectl_get`, `ollama_generate`
- **Spans**: детальная информация о каждой операции
- **Trace ID**: связь между запросом и всеми операциями

## 📊 kagent.dev CRD

```bash
# Применить CRD
kubectl apply -f manifests/agent-crd.yaml

# Проверить статус
kubectl get agent sre-kubernetes-agent -n kagent-system

# Детальная информация
kubectl describe agent sre-kubernetes-agent -n kagent-system
```

**Спецификация CRD:**
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
      endpoint: "http://jaeger-collector:4317"
```

## 🔧 Конфигурация

### Environment Variables

В `manifests/deployment.yaml`:

```yaml
env:
  - name: OLLAMA_BASE_URL
    value: "http://ollama:11434"
  - name: OLLAMA_MODEL
    value: "llama3"
  - name: OTEL_EXPORTER_OTLP_ENDPOINT
    value: "http://jaeger-collector:4317"
```

### Изменение модели LLM

```bash
# Изменить в ConfigMap
kubectl edit configmap sre-agent-config -n kagent-system

# Или использовать другие модели
OLLAMA_MODEL=mistral
OLLAMA_MODEL=codellama
```

## 🛠️ Troubleshooting

### Agent Card не доступен

```bash
kubectl exec -n kagent-system deploy/sre-agent -- ls -la /app/.well-known/
kubectl logs -n kagent-system -l app=sre-agent | grep "well-known"
```

### Ollama не отвечает

```bash
kubectl logs -n kagent-system -l app=ollama
kubectl exec -n kagent-system deploy/ollama -- ollama list
kubectl exec -n kagent-system deploy/ollama -- ollama pull llama3
```

### Трейсы не появляются

```bash
kubectl logs -n observability -l app=jaeger
kubectl exec -n kagent-system deploy/sre-agent -- \
  curl http://jaeger-collector.observability.svc.cluster.local:4317
```

## 📚 Документация

- **README.md** - основная документация с архитектурой
- **QUICKSTART.md** - быстрый старт за 5 минут
- **docs/A2A_PROTOCOL.md** - детальное описание A2A Protocol
- **docs/EXAMPLES.md** - примеры использования с Python клиентом

## 🎓 Что дальше?

1. **Добавить больше инструментов**: helm, kubectl scale, kubectl rollout
2. **Улучшить промпты**: добавить примеры, контекст
3. **Настроить Ingress**: для доступа извне кластера
4. **Добавить аутентификацию**: OAuth2, JWT
5. **Интегрировать с CI/CD**: автоматический анализ
6. **Добавить алерты**: Alertmanager integration

## 📝 Резюме команд

```bash
# Сборка и развертывание
cd /home/sre21.05.2026/agent && docker build -t sre-agent:latest .
kind load docker-image sre-agent:latest
cd .. && ./deploy.sh

# Проверка
kubectl get pods -n kagent-system
kubectl port-forward -n kagent-system svc/sre-agent 8080:8080 &

# Получение Agent Card (Well-Known URI)
curl http://localhost:8080/.well-known/agent-card.json | jq

# Тестирование
python3 test_agent.py

# Использование
curl -X POST http://localhost:8080/v1/agent \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Analyze cluster"}], "tools": ["analyze_cluster_health"]}' | jq

# Просмотр трейсов
kubectl port-forward -n observability svc/jaeger-ui 16686:16686 &
open http://localhost:16686
```

## ✅ Чек-лист реализации

- [x] Google A2A Protocol
  - [x] Agent Card JSON
  - [x] Well-Known URI endpoint
  - [x] Стандартные endpoints
  - [x] Streaming support
- [x] Ollama Integration
  - [x] Асинхронный клиент
  - [x] Поддержка разных моделей
  - [x] Streaming генерация
- [x] Kubernetes Tools
  - [x] 8 инструментов для SRE
  - [x] RBAC конфигурация
  - [x] Error handling
- [x] Observability
  - [x] OpenTelemetry трейсинг
  - [x] Jaeger экспорт
  - [x] Trace ID в ответах
  - [x] Metrics endpoint
- [x] kagent.dev CRD
  - [x] Полная спецификация
  - [x] Декларативная конфигурация
- [x] Документация
  - [x] README с архитектурой
  - [x] QUICKSTART guide
  - [x] A2A Protocol guide
  - [x] Примеры использования
- [x] Тесты
  - [x] Agent Card test
  - [x] Health check test
  - [x] Tool execution test
  - [x] Streaming test

Все готово к использованию! 🚀
