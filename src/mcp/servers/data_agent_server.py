import sys
from pathlib import Path
from contextlib import asynccontextmanager

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

from mcp.server.fastmcp import FastMCP
from langchain_core.messages import HumanMessage

from src.data.manager import DataManager
from src.agents.shared import set_data_manager
from src.agents.data_agent import DataAgent

# Instancias globales
dm: DataManager = None
agent: DataAgent = None


@asynccontextmanager
async def lifespan(server: FastMCP):
    global dm, agent

    dm = DataManager(cutoff_date="2025-01-01")
    await dm.connect()
    set_data_manager(dm)
    agent = DataAgent()
    yield


mcp = FastMCP("DataAgent", lifespan=lifespan)


@mcp.tool()
async def invoke(message: str) -> str:
    """Procesa una solicitud usando el agente DataAgent con razonamiento LLM.
    
    El agente analiza el mensaje, decide qué herramientas de Odoo usar,
    las ejecuta y genera una respuesta estructurada.
    
    Args:
        message: Solicitud en lenguaje natural. Puede incluir contexto
                 con IDs de clientes disponibles.
        
    Returns:
        Respuesta del agente con los datos solicitados.
        
    Ejemplos de uso:
        - "Busca al cliente Acme"
        - "Dame las facturas pendientes del cliente ID 123"
        - "¿Qué facturas vencen esta semana?"
    """
    result = await agent.run([HumanMessage(content=message)])
    return agent.extract_final_response(result)


if __name__ == "__main__":
    mcp.run(transport="sse")
