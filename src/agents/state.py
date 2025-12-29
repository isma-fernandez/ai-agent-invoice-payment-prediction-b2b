import operator
from typing import Annotated, Literal, Optional, TypedDict
from langgraph.graph import add_messages

class AgentState(TypedDict):
    """Estado compartido entre agentes"""
    messages: Annotated[list, add_messages]
    next_agent: Optional[Literal["data_agent", "analysis_agent", "memory_agent"]]