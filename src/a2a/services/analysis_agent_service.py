import uvicorn
from a2a.server.apps.rest import A2ARESTFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.types import AgentCard, AgentCapabilities, AgentSkill
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
    ),
    skills=[
        AgentSkill(
            id="predict_invoice_risk",
            name="predict_invoice_risk",
            description="Predice el riesgo de impago de una factura existente",
            tags=["prediction", "risk", "invoice", "payment"]
        ),
        AgentSkill(
            id="predict_hypothetical_invoice",
            name="predict_hypothetical_invoice",
            description="Predice el riesgo de una factura hipotética para un cliente",
            tags=["prediction", "risk", "hypothetical", "invoice"]
        ),
        AgentSkill(
            id="get_high_risk_clients",
            name="get_high_risk_clients",
            description="Obtiene los clientes con mayor riesgo de impago",
            tags=["risk", "client", "ranking", "analysis"]
        ),
        AgentSkill(
            id="compare_clients",
            name="compare_clients",
            description="Compara varios clientes en términos de riesgo y comportamiento de pago",
            tags=["comparison", "client", "risk", "behavior"]
        ),
        AgentSkill(
            id="get_aging_report",
            name="get_aging_report",
            description="Genera un informe de antigüedad de deuda (global o por cliente)",
            tags=["aging", "debt", "report", "analysis"]
        ),
        AgentSkill(
            id="get_portfolio_summary",
            name="get_portfolio_summary",
            description="Obtiene un resumen de la cartera completa con métricas agregadas",
            tags=["portfolio", "summary", "metrics", "analysis"]
        ),
        AgentSkill(
            id="get_client_trend",
            name="get_client_trend",
            description="Analiza la tendencia de pago de un cliente a lo largo del tiempo",
            tags=["trend", "client", "evolution", "analysis"]
        ),
        AgentSkill(
            id="get_deteriorating_clients",
            name="get_deteriorating_clients",
            description="Identifica clientes cuyo comportamiento de pago está empeorando",
            tags=["deterioration", "client", "alert", "analysis"]
        ),
        AgentSkill(
            id="generate_chart",
            name="generate_chart",
            description="Genera gráficos visuales para mostrar datos (barras, líneas, donut, etc.)",
            tags=["chart", "visualization", "graph", "data"]
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