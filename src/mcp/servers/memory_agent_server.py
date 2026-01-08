import sys
from pathlib import Path
from contextlib import asynccontextmanager

ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

from mcp.server.fastmcp import FastMCP
from langchain_core.messages import HumanMessage

from src.agents.store import MemoryStore
from src.agents.shared import set_memory_store
from src.agents.memory_agent import MemoryAgent

ms: MemoryStore = None
agent: MemoryAgent = None


@asynccontextmanager
async def lifespan(server: FastMCP):
    global ms, agent

    ms = MemoryStore(db_path="data/agent_memory.db")
    set_memory_store(ms)
    agent = MemoryAgent()
    yield


mcp = FastMCP("MemoryAgent", lifespan=lifespan)


@mcp.tool()
async def invoke(message: str) -> str:
    """Procesa una solicitud usando el agente MemoryAgent con razonamiento LLM.
    
    El agente analiza el mensaje, decide si debe guardar notas, alertas
    o recuperar información previa, y ejecuta las operaciones de memoria.
    
    Args:
        message: Solicitud en lenguaje natural. Debe incluir partner_id y 
                 partner_name si se quieren guardar notas de cliente.
        
    Returns:
        Confirmación de las operaciones realizadas o información recuperada.
        
    Ejemplos de uso:
        - "Guarda una nota: el cliente 123 (Acme) siempre paga tarde"
        - "¿Qué notas hay del cliente 456?"
        - "Registra una alerta: revisar factura crítica"
    """
    result = await agent.run([HumanMessage(content=message)])
    return agent.extract_final_response(result)


if __name__ == "__main__":
    mcp.run(transport="sse")
