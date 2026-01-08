import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Necesario temporalmente
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from mcp.server.fastmcp import FastMCP
from src.data.manager import DataManager
from src.data.models import (
    PredictionResult, ClientInfo, AgingReport,
    PortfolioSummary, ClientTrend, DeterioratingClient
)

dm: DataManager = None


@asynccontextmanager
async def lifespan(server: FastMCP):
    global dm
    # TODO: el cutoff_date no sirve para producción
    dm = DataManager(cutoff_date="2025-01-01")
    await dm.connect()

    try:
        dm.load_model("models/late_invoice_payment_classification.pkl")
    except Exception as e:
        print(f"[AnalysisAgent] WARN: Modelo no disponible: {e}")

    yield


mcp = FastMCP("AnalysisAgent", lifespan=lifespan)

@mcp.tool()
async def predict_invoice_risk(invoice_id: int) -> PredictionResult | dict:
    """Predice el riesgo de impago de una factura existente."""
    if not dm.is_model_loaded():
        return {"error": "Modelo no disponible"}
    try:
        return await dm.predict(invoice_id=invoice_id)
    except ValueError as e:
        return {"error": str(e)}


@mcp.tool()
async def predict_hypothetical_invoice(
        partner_id: int,
        amount_eur: float,
        payment_term_days: int = 30
) -> PredictionResult | dict:
    """Predice el riesgo de una factura hipotética."""
    if not dm.is_model_loaded():
        return {"error": "Modelo no disponible"}
    try:
        return await dm.predict_hypothetical(
            partner_id=partner_id,
            amount_eur=amount_eur,
            payment_term_days=payment_term_days
        )
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def get_high_risk_clients(limit: int = 10) -> list[ClientInfo]:
    """Obtiene clientes con mayor riesgo de impago."""
    return await dm.get_high_risk_clients(limit=limit)


@mcp.tool()
async def compare_clients(partner_ids: list[int]) -> list[ClientInfo] | dict:
    """Compara estadísticas de pago entre varios clientes."""
    return await dm.compare_clients(partner_ids=partner_ids)


@mcp.tool()
async def get_client_trend(partner_id: int, recent_months: int = 6) -> ClientTrend | None:
    """Analiza tendencia de pago de un cliente (mejorando/empeorando/estable)."""
    return await dm.get_client_trend(partner_id=partner_id, recent_months=recent_months)


@mcp.tool()
async def get_deteriorating_clients(limit: int = 10, min_invoices: int = 5) -> list[DeterioratingClient]:
    """Identifica clientes cuyo comportamiento está empeorando."""
    return await dm.get_deteriorating_clients(limit=limit, min_invoices=min_invoices)


@mcp.tool()
async def get_aging_report(partner_id: int = None) -> AgingReport:
    """Genera aging report (global o de un cliente)."""
    return await dm.get_aging_report(partner_id=partner_id)


@mcp.tool()
async def get_portfolio_summary() -> PortfolioSummary:
    """Genera resumen ejecutivo de la cartera."""
    return await dm.get_portfolio_summary()


if __name__ == "__main__":
    mcp.run(transport="sse")
