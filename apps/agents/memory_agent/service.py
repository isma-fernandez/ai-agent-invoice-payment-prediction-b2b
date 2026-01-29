import uvicorn
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.types import AgentCard, AgentCapabilities, AgentSkill
from a2a.server.tasks import InMemoryTaskStore
from .graph import MemoryAgent
from apps.agents.base_executor import BaseAgentExecutor
from shared.config.settings import settings

_task_store = InMemoryTaskStore()

agent_card = AgentCard(
    name="memory_agent",
    description="Agente especializado en gestión de memoria persistente (notas y alertas)",
    version="1.0.0",
    url=settings.A2A_MEMORY_AGENT_URL,
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    capabilities=AgentCapabilities(
        streaming=False,
        state_transition_history=False,
        push_notifications=False,
        extensions=[]
    ),
    skills=[
        AgentSkill(
            id="save_client_note",
            name="save_client_note",
            description="Guardar nota permanente sobre un cliente. Usar cuando el usuario dice 'recuerda que...', 'anota que...'. REQUIERE partner_id.",
            tags=["memory", "note", "client", "persistence", "requires_id"]
        ),
        AgentSkill(
            id="get_client_notes",
            name="get_client_notes",
            description="Recuperar notas guardadas de un cliente específico. REQUIERE partner_id.",
            tags=["memory", "note", "client", "retrieval", "requires_id"]
        ),
        AgentSkill(
            id="save_alert",
            name="save_alert",
            description="Guardar alerta importante que requiere atención. partner_id OPCIONAL si la alerta es sobre un cliente específico.",
            tags=["memory", "alert", "persistence", "notification", "optional_id"]
        ),
        AgentSkill(
            id="get_active_alerts",
            name="get_active_alerts",
            description="Recuperar alertas activas del sistema. NO requiere IDs, es consulta global.",
            tags=["memory", "alert", "active", "retrieval", "global"]
        ),
    ]
)

executor = BaseAgentExecutor(lambda: MemoryAgent())
request_handler = DefaultRequestHandler(
    agent_executor=executor, 
    task_store=_task_store
)

a2a_app = A2AFastAPIApplication(
    agent_card=agent_card,
    http_handler=request_handler
)

app = a2a_app.build()

@app.get("/health")
async def health():
    return {"status": "ok", "agent": "memory_agent"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
