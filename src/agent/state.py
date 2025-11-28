import operator
from typing import Annotated, List, TypedDict
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    # Historial del chat
    # metadatos operator.add para indicar a langgraph no sobrescribir esta variable
    messages: Annotated[List[BaseMessage], operator.add]
    
    client_id: str | None
    # Puntual - Leve - Grave (TODO: Cambiar nombres)
    risk_category: str | None
    # Características que lo explican
    explanation: str | None