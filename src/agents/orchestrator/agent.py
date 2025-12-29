from src.data.manager import DataManager
from src.agents.store import MemoryStore
from src.agents.shared import set_data_manager, set_memory_store
from src.agents.orchestrator import Orchestrator


class FinancialAgent:
    """Agente financiero multiagente para gestión de cobros B2B."""
    def __init__(self):
        self._initialized = False
        self._orchestrator = None


    async def initialize(self, cutoff_date: str = None, model_path: str = None):
        """Inicializa conexión a Odoo, modelo de predicción y agentes."""
        if self._initialized:
            return

        dm = DataManager(cutoff_date=cutoff_date)
        await dm.connect()
        if model_path:
            dm.load_model(model_path)
        set_data_manager(dm)

        ms = MemoryStore()
        set_memory_store(ms)

        self._orchestrator = Orchestrator()
        self._initialized = True


    async def stream_request(self, request: str, thread_id: str):
        """Procesa en modo streaming"""
        if not self._initialized:
            raise RuntimeError("Agente no inicializado.")
        async for event in self._orchestrator.stream(request, thread_id):
            yield event