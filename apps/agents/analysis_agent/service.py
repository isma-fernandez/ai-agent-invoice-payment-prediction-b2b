import uvicorn
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.types import AgentCard, AgentCapabilities, AgentSkill
from a2a.server.tasks import InMemoryTaskStore
from .graph import AnalysisAgent
from apps.agents.base_executor import BaseAgentExecutor
from shared.data.manager import DataManager
from apps.agents.shared import set_data_manager
from shared.config.settings import settings

_task_store = InMemoryTaskStore()

agent_card = AgentCard(
    name="analysis_agent",
    description="Agente especializado en predicciones y análisis de riesgo de pagos",
    version="1.0.0",
    url=settings.A2A_ANALYSIS_AGENT_URL,
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
            id="predict_invoice_risk",
            name="predict_invoice_risk",
            description="Predice riesgo de impago de una factura existente con modelo ML. Genera gráfico donut de probabilidades. REQUIERE invoice_id.",
            tags=["prediction", "risk", "invoice", "payment", "requires_id"]
        ),
        AgentSkill(
            id="predict_hypothetical_invoice",
            name="predict_hypothetical_invoice",
            description="Predice riesgo de una factura hipotética para escenarios futuros. REQUIERE partner_id y amount_eur.",
            tags=["prediction", "risk", "hypothetical", "invoice", "requires_id"]
        ),
        AgentSkill(
            id="get_high_risk_clients",
            name="get_high_risk_clients",
            description="Ranking de clientes con mayor riesgo de impago (risk_score 0-100). NO requiere IDs, es consulta global.",
            tags=["risk", "client", "ranking", "analysis", "global"]
        ),
        AgentSkill(
            id="compare_clients",
            name="compare_clients",
            description="Compara estadísticas de pago entre varios clientes específicos. REQUIERE lista de partner_ids (mínimo 2).",
            tags=["comparison", "client", "risk", "behavior", "requires_ids"]
        ),
        AgentSkill(
            id="get_aging_report",
            name="get_aging_report",
            description="Informe de antigüedad de deuda en buckets (0-30, 31-60, 61-90, >90 días). partner_id OPCIONAL: sin ID es global, con ID es para ese cliente.",
            tags=["aging", "debt", "report", "analysis", "optional_id"]
        ),
        AgentSkill(
            id="get_portfolio_summary",
            name="get_portfolio_summary",
            description="Resumen ejecutivo de la cartera: total pendiente, total vencido, DSO, métricas agregadas. NO requiere IDs, es consulta global.",
            tags=["portfolio", "summary", "metrics", "analysis", "global"]
        ),
        AgentSkill(
            id="get_client_trend",
            name="get_client_trend",
            description="Analiza tendencia de comportamiento de pago de un cliente (mejorando/empeorando/estable). REQUIERE partner_id.",
            tags=["trend", "client", "evolution", "analysis", "requires_id"]
        ),
        AgentSkill(
            id="get_deteriorating_clients",
            name="get_deteriorating_clients",
            description="Identifica clientes cuyo comportamiento de pago está EMPEORANDO respecto al histórico. NO requiere IDs, es consulta global.",
            tags=["deterioration", "client", "alert", "analysis", "global"]
        ),
        AgentSkill(
            id="generate_chart",
            name="generate_chart",
            description="Genera gráficos personalizados (barras, líneas, donut). Las otras herramientas ya generan sus propios gráficos automáticamente.",
            tags=["chart", "visualization", "graph", "data", "internal"]
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
    

executor = BaseAgentExecutor(lambda: AnalysisAgent())
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
    return {"status": "ok", "agent": "analysis_agent"}

if __name__ == "__main__":
    import asyncio
    asyncio.run(init_resources())
    uvicorn.run(app, host="0.0.0.0", port=8002)
