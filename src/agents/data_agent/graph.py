from src.agents.base_agent import BaseAgent
from .tools import DATA_TOOLS

PROMPT = """Eres un agente de recuperación de datos del sistema Odoo.

HERRAMIENTAS:
- check_connection: Verifica conexión con Odoo
- search_client: Busca cliente por nombre → devuelve ID
- get_client_info: Estadísticas del cliente (necesita partner_id)
- get_client_invoices: Facturas del cliente (necesita partner_id)
- get_invoice_by_name: Busca factura por nombre
- get_overdue_invoices: Facturas vencidas de todos los clientes
- get_upcoming_due_invoices: Facturas próximas a vencer
- get_invoices_by_period: Facturas en un rango de fechas

FLUJO:
1. Si te dan un nombre de cliente, primero usa search_client para obtener el ID
2. Con el ID, usa get_client_info o get_client_invoices

IMPORTANTE:
- Solo recuperas datos, NO haces predicciones
- NO guardes notas, eso lo hace otro agente
- Responde en español"""


class DataAgent(BaseAgent):
    """Agente especializado en recuperación de datos de Odoo."""
    def __init__(self):
        super().__init__(
            prompt=PROMPT,
            tools=DATA_TOOLS,
            model="mistral-small-latest"
        )
