# TODO: Necesario para evitar imports circulares desde main
from src.agents.orchestrator import FinancialAgent

_agent: FinancialAgent | None = None


async def get_agent() -> FinancialAgent:
    """Obtiene la instancia del agente."""
    global _agent
    if _agent is None:
        _agent = FinancialAgent()
        await _agent.initialize(
            # TODO: Eliminar cutoff_date en producción
            cutoff_date="2025-01-01"
        )
    return _agent
