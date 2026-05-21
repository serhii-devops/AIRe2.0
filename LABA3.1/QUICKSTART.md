# Краткое руководство по развертыванию

## Быстрый старт (5 минут)

```bash
cd /home/sre21.05.2026

# 1. Собрать образ агента
cd agent
docker build -t sre-agent:latest .

# 2. Загрузить в кластер (для kind)
kind load docker-image sre-agent:latest

# 3. Развернуть все компоненты
cd ..
./deploy.sh

# 4. Проверить статус
kubectl get pods -n kagent-system
kubectl get pods -n observability

# 5. Port-forward для доступа
kubectl port-forward -n kagent-system svc/sre-agent 8080:8080 &
kubectl port-forward -n observability svc/jaeger-ui 16686:16686 &

# 6. Получить Agent Card (Well-Known URI)
curl http://localhost:8080/.well-known/agent-card.json | jq

# 7. Протестировать агента
python3 test_agent.py
```

## Основные команды

### Получение Agent Card

```bash
# Локально
curl http://localhost:8080/.well-known/agent-card.json | jq

# Внутри кластера
curl http://sre-agent.kagent-system.svc.cluster.local:8080/.well-known/agent-card.json
```

### Использование агента

```bash
# Анализ кластера
curl -X POST http://localhost:8080/v1/agent \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Analyze cluster health"}],
    "tools": ["analyze_cluster_health"]
  }' | jq

# Диагностика пода
curl -X POST http://localhost:8080/v1/agent \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Diagnose pod issues"}],
    "context": {"pod_name": "my-pod", "namespace": "default"}
  }' | jq

# Получение логов
curl -X POST http://localhost:8080/v1/tools/kubectl_logs \
  -H "Content-Type: application/json" \
  -d '{"pod_name": "my-pod", "namespace": "default", "tail": 100}' | jq
```

### Просмотр трейсов

```bash
# Открыть Jaeger UI
open http://localhost:16686

# Выбрать сервис: sre-kubernetes-agent
# Увидите трейсы всех операций агента
```

## Структура проекта

```
/home/sre21.05.2026/
├── agent/                      # Код агента
│   ├── main.py                 # FastAPI приложение с A2A Protocol
│   ├── Dockerfile              # Образ контейнера
│   └── requirements.txt        # Python зависимости
│
├── manifests/                  # Kubernetes манифесты
│   ├── deployment.yaml         # Deployment агента + RBAC
│   ├── agent-crd.yaml          # kagent.dev CRD
│   ├── ollama.yaml             # Ollama LLM deployment
│   └── observability.yaml      # Jaeger для трейсинга
│
├── .well-known/                # A2A Protocol
│   └── agent-card.json         # Agent Card с возможностями
│
├── docs/                       # Документация
│   ├── A2A_PROTOCOL.md         # Подробное описание A2A
│   └── EXAMPLES.md             # Примеры использования
│
├── deploy.sh                   # Скрипт развертывания
├── test_agent.py               # Тесты
└── README.md                   # Основная документация
```

## Что реализовано

✅ **Google A2A Protocol**
- Agent Card с описанием возможностей
- Well-Known URI: `/.well-known/agent-card.json`
- Стандартные endpoints: `/v1/agent`, `/v1/tools/{tool_name}`
- Поддержка streaming и async

✅ **Ollama Integration**
- Локальный LLM (llama3)
- Асинхронные запросы
- Поддержка streaming ответов

✅ **Kubernetes Tools**
- kubectl_get - получение ресурсов
- kubectl_describe - детальное описание
- kubectl_logs - логи подов
- kubectl_apply - применение манифестов
- kubectl_delete - удаление ресурсов
- analyze_cluster_health - анализ кластера
- diagnose_pod_issues - диагностика проблем

✅ **Observability**
- OpenTelemetry трейсинг
- Экспорт в Jaeger
- Trace ID в каждом ответе
- Prometheus metrics endpoint

✅ **kagent.dev CRD**
- Декларативная конфигурация агента
- Спецификация инструментов
- Настройки LLM и observability
- RBAC конфигурация

## Проверка работы

```bash
# 1. Проверить поды
kubectl get pods -n kagent-system
# Должны быть: sre-agent, ollama

# 2. Проверить логи
kubectl logs -n kagent-system -l app=sre-agent

# 3. Проверить Agent Card
curl http://localhost:8080/.well-known/agent-card.json | jq '.name'
# Вывод: "SRE Kubernetes Agent"

# 4. Проверить health
curl http://localhost:8080/health
# Вывод: {"status": "healthy", ...}

# 5. Запустить тесты
python3 test_agent.py
# Должны пройти все 5 тестов
```

## Troubleshooting

**Проблема**: Agent Card не доступен
```bash
kubectl exec -n kagent-system deploy/sre-agent -- ls -la /app/.well-known/
```

**Проблема**: Ollama не отвечает
```bash
kubectl logs -n kagent-system -l app=ollama
kubectl exec -n kagent-system deploy/ollama -- ollama list
```

**Проблема**: Нет трейсов в Jaeger
```bash
kubectl logs -n observability -l app=jaeger
kubectl exec -n kagent-system deploy/sre-agent -- env | grep OTEL
```

## Дополнительная информация

- **README.md** - полная документация
- **docs/A2A_PROTOCOL.md** - детали A2A Protocol
- **docs/EXAMPLES.md** - примеры использования
- **agent/main.py** - исходный код агента
