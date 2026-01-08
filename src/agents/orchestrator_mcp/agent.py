from .graph import Orchestrator


class FinancialAgent:

    def __init__(self):
        self._initialized = False
        self._orchestrator: Orchestrator = None

    async def initialize(self):
        """Inicializa el Orchestrator y conecta con sub-agentes MCP.
        Los sub-agentes MCP deben estar on antes de este método."""
        if self._initialized:
            return

        self._orchestrator = Orchestrator()
        await self._orchestrator.initialize()
        self._initialized = True

    async def shutdown(self):
        """Cierra conexiones con sub-agentes."""
        if self._orchestrator:
            await self._orchestrator.shutdown()
        self._initialized = False

    async def process_request(self, request: str, thread_id: str) -> str:
        """Procesa una solicitud del usuario."""
        if not self._initialized:
            raise RuntimeError("Agente no inicializado.")
        return await self._orchestrator.run(request, thread_id)

    async def stream_request(self, request: str, thread_id: str):
        """Procesa en modo streaming."""
        if not self._initialized:
            raise RuntimeError("Agente no inicializado.")
        async for event in self._orchestrator.stream(request, thread_id):
            yield event
