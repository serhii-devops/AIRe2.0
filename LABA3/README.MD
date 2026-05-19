# Laba3 Quick Start
Minimal setup for running Kagent with Ollama and `qwen2.5:7b` model inside Abox.

---

## Requirements

- Linux server / VM
- Docker
- kubectl
- 16+ GB RAM recommended

---

# 1. Install dependencies

```bash

echo "fs.inotify.max_user_instances=8192" | sudo tee -a /etc/sysctl.conf
echo "fs.inotify.max_user_watches=524288" | sudo tee -a /etc/sysctl.conf

kubectl apply -f mcp_and_agent.yaml

```

## Запуск декларативного агента.
![Успішна відповідь від AgentGateway](assets/kagent-1.png)

## Робота декларативного агента.
![Успішна відповідь від AgentGateway](assets/kagent-2.png)


