from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import SystemMessage
from config.settings import settings
from .state import AgentState


class BaseAgent:
    def __init__(self, prompt: str, tools: list, model: str = "mistral-small-latest"):
        self.MAX_MESSAGES = 20
        self.prompt = prompt
        self.tools = tools
        self.tool_node = ToolNode(tools)
        # Lo limito a Mistral pero podria expandirse a otros proveedores
        self.llm = ChatMistralAI(
            model=model,
            temperature=0,
            api_key=settings.API_MISTRAL_KEY,
        ).bind_tools(tools)
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("agent", self._chatbot)
        builder.add_node("tools", self.tool_node)
        builder.add_edge(START, "agent")
        builder.add_conditional_edges(
            "agent",
            self._condition_tools_or_end,
            {"tools": "tools", "end": END}
        )
        builder.add_edge("tools", "agent")
        return builder.compile()

    def _chatbot(self, state: AgentState):
        messages = state["messages"]
        # Inyecto el prompt del sistema en cada llamada, necesario para
        # evitar que el prompt se pierda en llamadas sucesivas
        if len(messages) > self.MAX_MESSAGES:
            messages = messages[-self.MAX_MESSAGES:]
        messages = [SystemMessage(content=self.prompt)] + messages
        result = self.llm.invoke(messages)
        return {"messages": [result]}

    def _condition_tools_or_end(self, state: AgentState) -> str:
        """Decide si usar una herramienta o terminar la conversación."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "end"

    async def run(self, messages: list) -> AgentState:
        return await self.graph.ainvoke({"messages": messages})
