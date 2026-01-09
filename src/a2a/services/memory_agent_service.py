# src/a2a/services/memory_agent_service.py
import uvicorn
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.types import AgentCard, AgentCapabilities, AgentSkill
from a2a.server.tasks import InMemoryTaskStore
from src.agents.memory_agent import MemoryAgent
from src.a2a.base import BaseAgentExecutor
from src.agents.store import MemoryStore
from src.agents.shared import set_memory_store
from src.config.settings import settings

_task_store = InMemoryTaskStore()

#TODO: A lo mejor mover esto a el archivo de agentes
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
            description="Guarda una nota permanente sobre un cliente",
            tags=["memory", "note", "client", "persistence"]
        ),
        AgentSkill(
            id="get_client_notes",
            name="get_client_notes",
            description="Recupera las notas guardadas de un cliente",
            tags=["memory", "note", "client", "retrieval"]
        ),
        AgentSkill(
            id="save_alert",
            name="save_alert",
            description="Guarda una alerta importante que requiere atención",
            tags=["memory", "alert", "persistence", "notification"]
        ),
        AgentSkill(
            id="get_active_alerts",
            name="get_active_alerts",
            description="Recupera las alertas activas del sistema",
            tags=["memory", "alert", "active", "retrieval"]
        ),
    ]
)

_memory_store = None

# TODO: Hay que tocar las rutas del memory store
async def init_resources():
    """Inicializa los recursos necesarios para el servicio."""
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore()
        set_memory_store(_memory_store)

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
    import asyncio
    # Inicializar memory store antes del servidor
    asyncio.run(init_resources())
    # TODO: poner en variable de entorno el puerto
    uvicorn.run(app, host="0.0.0.0", port=8003)