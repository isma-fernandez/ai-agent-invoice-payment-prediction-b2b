from typing import Annotated, Literal, Optional, TypedDict
from langgraph.graph import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    next_agent: Optional[Literal["data_agent", "analysis_agent", "memory_agent"]]
    collected_data: list[str]
    user_query: str
    # TODO: tiene bucles infinitos cuando no encuentra datos, habría que solucionarlo sin esta variable...
    iterations: int

class SubAgentState(TypedDict):
    """Estado interno de cada subagente."""
    messages: Annotated[list, add_messages]