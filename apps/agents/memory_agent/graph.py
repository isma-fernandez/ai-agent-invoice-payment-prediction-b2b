from apps.agents.base import BaseAgent
from .tools import MEMORY_TOOLS
from .prompts import PROMPT


class MemoryAgent(BaseAgent):
    """Agente especializado en gestión de memoria persistente."""
    def __init__(self):
        super().__init__(
            prompt=PROMPT,
            tools=MEMORY_TOOLS,
            model="mistral-small-latest"
        )
