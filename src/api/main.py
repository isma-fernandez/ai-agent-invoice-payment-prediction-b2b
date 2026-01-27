import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.agents.orchestrator import FinancialAgent
from src.api.routes import chat, health
from src.a2a.services.orchestrator_a2a import create_a2a_app

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de la aplicación."""
    await get_agent()
    print("Orchestrator inicializado correctamente")
    yield
    print("Orchestrator finalizado")


app = FastAPI(
    title="Orchestrator Service",
    description="Orquestador del asistente de predicción de pagos",
    version="1.0.0",
    lifespan=lifespan
)

#endpoints
app.include_router(health.router)
app.include_router(chat.router)

# A2A para agentes externos
a2a_app = create_a2a_app(get_agent)
app.mount("/a2a", a2a_app)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
