# app/agent_card.py
from pydantic import BaseModel
from typing import List, Optional

class AgentSkill(BaseModel):
    id: str
    name: str
    description: str
    tags: List[str]
    examples: Optional[List[str]] = None

class AgentCapabilities(BaseModel):
    streaming: bool = False
    pushNotifications: bool = False
    stateTransitionHistory: bool = False

class AgentCard(BaseModel):
    name: str
    description: str
    url: str
    version: str
    capabilities: AgentCapabilities
    skills: List[AgentSkill]
    defaultInputModes: List[str] = ["text"]
    defaultOutputModes: List[str] = ["text"]

def build_agent_card(base_url: str) -> AgentCard:
    return AgentCard(
        name="SRE Kubernetes Agent",
        description=(
            "AI-агент для SRE-задач в Kubernetes: "
            "диагностика подов, просмотр логов, масштабирование деплойментов."
        ),
        url=base_url,
        version="1.0.0",
        capabilities=AgentCapabilities(
            streaming=False,
            pushNotifications=False,
            stateTransitionHistory=True,
        ),
        skills=[
            AgentSkill(
                id="check_pod_health",
                name="Check Pod Health",
                description="Проверить статус подов в неймспейсе. Возвращает список подов с их статусом, restarts и возрастом.",
                tags=["kubernetes", "pods", "health", "sre"],
                examples=[
                    "Check pods in namespace production",
                    "Are there any crashing pods in default namespace?",
                    "Show pod health for namespace monitoring",
                ],
            ),
            AgentSkill(
                id="get_logs",
                name="Get Pod Logs",
                description="Получить последние логи из конкретного пода или деплоймента.",
                tags=["kubernetes", "logs", "debug", "sre"],
                examples=[
                    "Get logs from pod nginx-abc123 in namespace default",
                    "Show last 100 lines from deployment api-server",
                ],
            ),
            AgentSkill(
                id="scale_deployment",
                name="Scale Deployment",
                description="Масштабировать деплоймент — увеличить или уменьшить количество реплик.",
                tags=["kubernetes", "scaling", "deployment", "sre"],
                examples=[
                    "Scale deployment api-server to 3 replicas in namespace production",
                    "Scale down worker to 1 replica",
                ],
            ),
        ],
    )