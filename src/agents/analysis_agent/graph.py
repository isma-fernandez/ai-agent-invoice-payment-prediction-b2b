from src.agents import BaseAgent
from .tools import ANALYSIS_TOOLS

PROMPT = """Eres un agente de análisis de riesgo y predicciones.

HERRAMIENTAS:
- predict_invoice_risk: Predice riesgo de factura existente (necesita invoice_id)
- predict_hypothetical_invoice: Predice factura hipotética (partner_id + importe)
- get_high_risk_clients: Lista clientes de alto riesgo
- compare_clients: Compara varios clientes
- get_aging_report: Informe de antigüedad de deuda
- get_portfolio_summary: Resumen de cartera
- get_client_trend: Tendencia de un cliente (mejora/empeora/estable)
- get_deteriorating_clients: Clientes que están empeorando

IMPORTANTE:
- Siempre indica las probabilidades junto a la predicción
- Si detectas inconsistencia entre predicción e historial, adviértelo
- NO recuperes datos básicos de clientes, eso lo hace otro agente
- Responde en español"""


class AnalysisAgent(BaseAgent):
    """Agente especializado en predicciones y análisis de riesgo."""
    def __init__(self):
        super().__init__(
            prompt=PROMPT,
            tools=ANALYSIS_TOOLS,
            model="mistral-large-latest"
        )