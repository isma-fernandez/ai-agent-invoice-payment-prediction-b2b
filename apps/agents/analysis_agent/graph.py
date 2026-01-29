from apps.agents.base import BaseAgent
from .tools import ANALYSIS_TOOLS
from .prompts import PROMPT

class AnalysisAgent(BaseAgent):
    """Agente especializado en predicciones y análisis de riesgo."""
    def __init__(self):
        super().__init__(
            prompt=PROMPT,
            tools=ANALYSIS_TOOLS,
            model="mistral-large-latest"
        )
