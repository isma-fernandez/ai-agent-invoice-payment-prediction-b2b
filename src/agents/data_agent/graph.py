from src.agents import BaseAgent
from .tools import DATA_TOOLS
from .prompts import PROMPT


class DataAgent(BaseAgent):
    """Agente especializado en recuperación de datos de Odoo."""
    def __init__(self):
        super().__init__(
            prompt=PROMPT,
            tools=DATA_TOOLS,
            model="mistral-large-latest"
        )
