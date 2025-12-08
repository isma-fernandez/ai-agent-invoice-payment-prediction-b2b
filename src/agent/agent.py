import asyncio
from config.settings import settings
from .graph import Graph
from src.agent.tools import initialize_data_manager, tools

class FinancialAgent:
    def __init__(self):
        self.api_key = settings.API_MISTRAL_KEY
        asyncio.run(initialize_data_manager("models/late_invoice_payment_classification.pkl"))
        self.graph = Graph()

    async def process_request(self, request: str, thread_id: str) -> str:
        responses = await self.graph.run(request=request, thread_id=thread_id)
        return responses      