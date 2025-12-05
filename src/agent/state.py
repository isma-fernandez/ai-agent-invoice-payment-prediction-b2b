import operator
from typing import Annotated, TypedDict
from langgraph.graph import add_messages

class AgentState(TypedDict):
    # Historial del chat (inputs cliente, pensamientos y outputs (herramientas, msgs) del agente)
    # add_messages para indicar a langgraph no sobrescribir esta variable
    messages: Annotated[list, add_messages]
    
    client_id: str | None
    # Puntual - Leve - Grave (TODO: Cambiar nombres)
    risk_category: str | None
    # Características que lo explican
    explanation: str | None