"""Mensajes de estado para la interfaz de usuario."""

from src.agents.data_agent.tools import TOOL_MESSAGES as DATA_TOOL_MESSAGES
from src.agents.analysis_agent.tools import TOOL_MESSAGES as ANALYSIS_TOOL_MESSAGES
from src.agents.memory_agent.tools import TOOL_MESSAGES as MEMORY_TOOL_MESSAGES

AGENT_MESSAGES = {
    "data_agent": "Consultando datos en Odoo...",
    "analysis_agent": "Realizando análisis...",
    "memory_agent": "Gestionando memoria...",
    "final_answer": "Generando respuesta...",
    "router": "Delegando tareas...",
}

TOOL_MESSAGES = {
    **DATA_TOOL_MESSAGES,
    **ANALYSIS_TOOL_MESSAGES,
    **MEMORY_TOOL_MESSAGES,
}


def get_agent_message(agent_name: str) -> str | None:
    """Obtiene el mensaje de estado para un agente."""
    agent_name_lower = agent_name.lower()
    for key, message in AGENT_MESSAGES.items():
        if key in agent_name_lower:
            return message
    return None


def get_tool_message(tool_name: str) -> str:
    """Obtiene el mensaje de estado para una herramienta."""
    return TOOL_MESSAGES.get(tool_name, "Procesando...")