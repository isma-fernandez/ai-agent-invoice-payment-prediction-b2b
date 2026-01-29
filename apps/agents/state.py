from typing import Annotated, Literal, Optional, TypedDict
from langgraph.graph import add_messages


class AgentState(TypedDict):
    """Estado del orquestador principal."""
    messages: Annotated[list, add_messages]
    user_query: str
    agent_plan: list[str]
    collected_data: list[str]
    current_step: int

class SubAgentState(TypedDict):
    """Estado interno de cada subagente."""
    messages: Annotated[list, add_messages]
