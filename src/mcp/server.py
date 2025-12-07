import asyncio
import sys
from pathlib import Path

# Añadir raíz del proyecto al path
# TODO: temporal, ya lo arreglaré más adelante
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from mcp.server.fastmcp import FastMCP
from src.data.manager import DataManager
from src.data.models import *
from typing import List

mcp = FastMCP('Invoice Risk  Prediction Agent')
data_manager = None
financial_agent = None

async def startup_event():
    """Inicializar el DataManager."""
    global data_manager
    data_manager = DataManager()
    await data_manager.connect()
    data_manager.load_model('models/late_invoice_payment_classification.pkl')

@mcp.tool()
async def ask_agent(user_input: str) -> str:
    """Procesa una solicitud del usuario a través del agente financiero."""
    # TODO: Completar una vez que el agente esté implementado
    ...

@mcp.tool()
async def search_clients(name: str, limit: int) -> List[dict]:
    """Busca clientes por nombre para conseguir el ID."""
    records = await data_manager.search_clients(name=name, limit=limit)
    return [result.model_dump() for result in records]

@mcp.tool()
async def get_client_info(partner_id: int) -> dict | None:
    """Recupera información y estadísticas de un cliente a partir de su ID."""
    result = await data_manager.get_client_info(partner_id=partner_id)
    return result.model_dump() if result else None

@mcp.tool()
async def get_client_invoices(partner_id: int, limit: int, only_unpaid: bool) -> List[dict]:
    """Recupera un resumen de las facturas de un cliente a partir de su ID."""
    records = await data_manager.get_client_invoices(partner_id=partner_id, limit=limit, only_unpaid=only_unpaid)
    return [result.model_dump() for result in records]

@mcp.tool()
async def get_invoice_by_name(invoice_name: str) -> dict | None:
    """Recupera una factura por su nombre."""
    result = await data_manager.get_invoice_by_name(invoice_name=invoice_name)
    return result.model_dump() if result else None

@mcp.tool()
async def predict_invoice_risk(invoice_id: int) -> dict | None:
    """Predice el riesgo de impago de una factura existente a partir de su ID."""
    result = await data_manager.predict(invoice_id=invoice_id)
    return result.model_dump() if result else None

@mcp.tool()
async def predict_hypothetical_invoice(partner_id: int, amount_eur: float, payment_term_days: int) -> dict | None:
    """Predice el riesgo de impago de una factura hipotética."""
    result = await data_manager.predict_hypothetical(
        partner_id=partner_id,
        amount_eur=amount_eur,
        payment_term_days=payment_term_days
    )
    return result.model_dump() if result else None

if __name__ == "__main__":
    # Uso fastmcp run src/mcp/server.py
    # Probar npx @modelcontextprotocol/inspector python src/mcp/server.py
    # TODO: Para producción
    #asyncio.run(startup_event())
    mcp.run()