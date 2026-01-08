import sys
from pathlib import Path
from contextlib import asynccontextmanager
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
from mcp.server.fastmcp import FastMCP
from langchain_core.messages import HumanMessage
from src.data.manager import DataManager
from src.agents.shared import set_data_manager
from src.agents.analysis_agent import AnalysisAgent

dm: DataManager = None
agent: AnalysisAgent = None


@asynccontextmanager
async def lifespan(server: FastMCP):
    global dm, agent
    print("[AnalysisAgent Server] Iniciando...")
    
    # Inicializar DataManager con modelo
    dm = DataManager(cutoff_date="2025-01-01")
    await dm.connect()
    
    try:
        dm.load_model("models/late_invoice_payment_classification.pkl")
    except Exception as e:
        print(f"AnalysisAgent: Modelo no disponible: {e}")
    
    set_data_manager(dm)
    agent = AnalysisAgent()
    yield


mcp = FastMCP("AnalysisAgent", lifespan=lifespan)


@mcp.tool()
async def invoke(message: str) -> str:
    """Procesa una solicitud usando el agente AnalysisAgent con razonamiento LLM.
    
    El agente analiza el mensaje, decide qué análisis o predicciones realizar,
    ejecuta las herramientas necesarias y genera una respuesta con datos y gráficos.
    
    Args:
        message: Solicitud en lenguaje natural. Debe incluir IDs si se necesitan
                 para predicciones o análisis de clientes específicos.
        
    Returns:
        Respuesta del agente con análisis, predicciones y/o gráficos (CHART:id).
        
    Ejemplos de uso:
        - "Dame el aging report"
        - "Predice el riesgo de la factura ID 456"
        - "¿Cuáles son los clientes de mayor riesgo?"
        - "Compara los clientes 123 y 456"
    """
    result = await agent.run([HumanMessage(content=message)])
    return agent.extract_final_response(result)


if __name__ == "__main__":
    mcp.run(transport="sse")
