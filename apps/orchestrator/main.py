import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .dependencies import get_agent
from .routes import chat, health
from .a2a_service import create_a2a_app


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

app.include_router(health.router)
app.include_router(chat.router)

# A2A para agentes externos
a2a_app = create_a2a_app(get_agent)
app.mount("/a2a", a2a_app)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
