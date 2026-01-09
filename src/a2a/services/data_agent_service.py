import uvicorn
from a2a.server.apps.rest import A2ARESTFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.types import AgentCard, AgentCapabilities, AgentSkill
from src.agents.data_agent import DataAgent
from src.a2a.base import BaseAgentExecutor
from src.data.manager import DataManager
from src.agents.shared import set_data_manager

#TODO: A lo mejor mover esto a el archivo de agentes
agent_card = AgentCard(
    name="data_agent",
    description="Agente especializado en recuperación de datos del sistema Odoo ERP",
    version="1.0.0",
    capabilities=AgentCapabilities(
        streaming=False,
        state_transition_history=False,
        push_notifications=False,
        extensions=[]
    ),
    skills=[
        AgentSkill(
            id="search_client",
            name="search_client",
            description="Buscar cliente por nombre y obtener partner_id"
        ),
        AgentSkill(
            id="get_client_info",
            name="get_client_info",
            description="Obtener información y estadísticas del cliente"
        ),
        AgentSkill(
            id="get_client_invoices",
            name="get_client_invoices",
            description="Obtener facturas del cliente"
        ),
        AgentSkill(
            id="get_invoice_by_name",
            name="get_invoice_by_name",
            description="Buscar factura por nombre"
        ),
        AgentSkill(
            id="get_overdue_invoices",
            name="get_overdue_invoices",
            description="Obtener facturas vencidas"
        ),
        AgentSkill(
            id="get_upcoming_due_invoices",
            name="get_upcoming_due_invoices",
            description="Obtener facturas próximas a vencer"
        ),
        AgentSkill(
            id="get_invoices_by_period",
            name="get_invoices_by_period",
            description="Obtener facturas por período de fechas"
        ),
        AgentSkill(
            id="check_connection",
            name="check_connection",
            description="Verificar conexión con Odoo"
        ),
    ]
)

_data_manager = None

async def init_resources():
    """Inicializa los recursos necesarios para el servicio."""
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager()
        await _data_manager.connect()
        set_data_manager(_data_manager)

executor = BaseAgentExecutor(lambda: DataAgent())
request_handler = DefaultRequestHandler(agent_executor=executor)

a2a_app = A2ARESTFastAPIApplication(
    agent_card=agent_card,
    http_handler=request_handler
)

app = a2a_app.build()

@app.get("/health")
async def health():
    return {"status": "ok", "agent": "data_agent"}


if __name__ == "__main__":
    import asyncio
    # Inicializar data manager antes del servidor
    asyncio.run(init_resources())
    # TODO: poner en variable de entorno el puerto
    uvicorn.run(app, host="0.0.0.0", port=8001)