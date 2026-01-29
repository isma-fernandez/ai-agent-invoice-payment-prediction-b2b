from shared.data.manager import DataManager
from apps.agents.shared import set_data_manager
from .graph import Orchestrator


class FinancialAgent:
    """Agente financiero multiagente para gestión de cobros B2B."""
    def __init__(self):
        self._initialized = False
        self._orchestrator = None


    async def initialize(self, cutoff_date: str = None):
        """Inicializa conexión a Odoo y agentes."""
        if self._initialized:
            return

        dm = DataManager(cutoff_date=cutoff_date)
        await dm.connect()
        set_data_manager(dm)

        self._orchestrator = Orchestrator()

        await self._orchestrator.initialize()
        self._initialized = True

    async def process_request(self, request: str, thread_id: str) -> str:
        """Procesa una solicitud del usuario."""
        if not self._initialized:
            raise RuntimeError("Agente no inicializado. Llama a initialize() primero.")
        return await self._orchestrator.run(request, thread_id)


    async def stream_request(self, request: str, thread_id: str):
        """Procesa en modo streaming"""
        if not self._initialized:
            raise RuntimeError("Agente no inicializado.")
        async for event in self._orchestrator.stream(request, thread_id):
            yield event
