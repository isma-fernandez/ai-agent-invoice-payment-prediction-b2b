import asyncio
from config.settings import settings
from .graph import Graph
from langchain_mistralai import ChatMistralAI
from src.data.manager import DataManager
from src.agent.tools import initialize_data_manager


class FinancialAgent:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self._initialized = False

        # LLM
        self.llm = ChatMistralAI(
            model="mistral-large-latest",
            temperature=0,
            max_retries=2,
            api_key=settings.API_MISTRAL_KEY,
        )

        # Componentes (se inicializan en _initialize)
        self.data_manager: DataManager = None
        self.memory_store: MemoryStore = None
        self.graph: Graph()

    async def process_request(self, request: str, thread_id: str) -> str:
        responses = await self.graph.run(request=request, thread_id=thread_id)
        return responses

    async def stream_request(self, request: str, thread_id: str):
        async for event in self.graph.stream(request=request, thread_id=thread_id):
            yield event