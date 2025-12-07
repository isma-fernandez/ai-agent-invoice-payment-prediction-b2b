from config.settings import settings
from .graph import Graph
from src.agent.tools import tools

class FinancialAgent:
    def __init__(self):
        self.api_key = settings.API_MISTRAL_KEY
        self.graph = Graph()

    def process_request(self, request: str) -> str:
        responses = self.graph.run(request)
        return responses      