import uvicorn
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.types import AgentCard, AgentCapabilities, AgentSkill
from a2a.server.tasks import InMemoryTaskStore
from .graph import DataAgent
from apps.agents.base_executor import BaseAgentExecutor
from shared.data.manager import DataManager
from apps.agents.shared import set_data_manager
from shared.config.settings import settings

_task_store = InMemoryTaskStore()

agent_card = AgentCard(
    name="data_agent",
    description="Agente especializado en recuperación de datos del sistema Odoo ERP",
    version="1.0.0",
    url=settings.A2A_DATA_AGENT_URL,
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
            id="search_client",
            name="search_client",
            description="Buscar cliente por NOMBRE para obtener partner_id. USAR PRIMERO cuando el usuario menciona un cliente por nombre y necesitas su ID para otras operaciones.",
            tags=["client", "search", "odoo", "requires_name"]
        ),
        AgentSkill(
            id="get_client_info",
            name="get_client_info",
            description="Información completa y estadísticas de un cliente: facturas, montos, ratios de pago, riesgo. REQUIERE partner_id.",
            tags=["client", "information", "statistics", "odoo", "requires_id"]
        ),
        AgentSkill(
            id="get_client_invoices",
            name="get_client_invoices",
            description="Listado de facturas de un cliente específico con filtros (pagadas, pendientes, límite). REQUIERE partner_id.",
            tags=["client", "invoice", "odoo", "requires_id"]
        ),
        AgentSkill(
            id="get_invoice_by_name",
            name="get_invoice_by_name",
            description="Buscar factura por nombre (ej: 'INV-001'). Usar cuando el usuario menciona una factura específica por su código.",
            tags=["invoice", "search", "odoo", "requires_name"]
        ),
        AgentSkill(
            id="get_overdue_invoices",
            name="get_overdue_invoices",
            description="Facturas vencidas de TODOS los clientes ordenadas por urgencia. NO requiere IDs, es consulta global.",
            tags=["invoice", "overdue", "odoo", "global"]
        ),
        AgentSkill(
            id="get_upcoming_due_invoices",
            name="get_upcoming_due_invoices",
            description="Facturas próximas a vencer para gestión preventiva. NO requiere IDs, es consulta global.",
            tags=["invoice", "upcoming", "due", "odoo", "global"]
        ),
        AgentSkill(
            id="get_invoices_by_period",
            name="get_invoices_by_period",
            description="Facturas emitidas en un período específico (fechas). partner_id OPCIONAL para filtrar por cliente.",
            tags=["invoice", "period", "dates", "odoo", "optional_id"]
        ),
        AgentSkill(
            id="check_connection",
            name="check_connection",
            description="Verificar conexión con Odoo. Usar solo si hay problemas de conectividad.",
            tags=["connection", "odoo", "verification", "diagnostic"]
        ),
    ]
)

_data_manager = None

async def init_resources():
    """Inicializa los recursos necesarios para el servicio."""
    global _data_manager
    if _data_manager is None:
        # TODO: Eliminar cutoff_date en producción
        _data_manager = DataManager(cutoff_date="2025-01-01")
        await _data_manager.connect()
        set_data_manager(_data_manager)

executor = BaseAgentExecutor(lambda: DataAgent())
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
    return {"status": "ok", "agent": "data_agent"}


if __name__ == "__main__":
    import asyncio
    asyncio.run(init_resources())
    uvicorn.run(app, host="0.0.0.0", port=8001)
