import uvicorn
from a2a.server.apps.rest import A2ARESTFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.types import AgentCard, AgentCapabilities
from src.agents.analysis_agent import AnalysisAgent
from src.a2a.base import BaseAgentExecutor
from src.data.manager import DataManager
from src.agents.shared import set_data_manager

#TODO: A lo mejor mover esto a el archivo de agentes
agent_card = AgentCard(
    name="analysis_agent",
    description="Agente especializado en predicciones y análisis de riesgo de pagos",
    version="1.0.0",
    capabilities=AgentCapabilities(
        streaming=False,
        state_transition_history=False,
        push_notifications=False,
        extensions=[]
    )
)

_data_manager = None

async def init_resources():
    """Inicializa los recursos necesarios para el servicio."""
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager()
        await _data_manager.connect()
        set_data_manager(_data_manager)

executor = BaseAgentExecutor(lambda: AnalysisAgent())
request_handler = DefaultRequestHandler(agent_executor=executor)

a2a_app = A2ARESTFastAPIApplication(
    agent_card=agent_card,
    http_handler=request_handler
)

app = a2a_app.build()

@app.get("/health")
async def health():
    return {"status": "ok", "agent": "analysis_agent"}

if __name__ == "__main__":
    import asyncio
    # Inicializar data manager antes del servidor
    asyncio.run(init_resources())
    # TODO: poner en variable de entorno el puerto
    uvicorn.run(app, host="0.0.0.0", port=8002)