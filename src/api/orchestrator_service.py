import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.agents.orchestrator import FinancialAgent
from src.config.settings import settings

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
    # Start
    await get_agent()
    print("Orchestrator inicializado correctamente")
    yield
    # Final
    print("Orchestrator finalizado")


app = FastAPI(
    title="Orchestrator Service",
    description="Orquestador del asistente de predicción de pagos",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health():
    """Health check del servicio."""
    return {"status": "ok", "service": "orchestrator"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
