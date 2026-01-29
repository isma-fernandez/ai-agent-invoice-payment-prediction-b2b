from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from shared.config.settings import settings
from apps.agents.state import SubAgentState
from .tools import MEMORY_TOOLS
from .prompts import PROMPT


class MemoryAgent:
    """Agente de memoria."""
    
    def __init__(self):
        self.prompt = PROMPT
        self.tools = MEMORY_TOOLS
        self.tool_node = ToolNode(MEMORY_TOOLS)
        self.llm = ChatMistralAI(
            model="mistral-large-latest",
            temperature=0,
            api_key=settings.API_MISTRAL_KEY,
        ).bind_tools(MEMORY_TOOLS, tool_choice="any")
        self.graph = self._build_graph()

    def _build_graph(self):
        """Construye el grafo de LangGraph para el agente."""
        builder = StateGraph(SubAgentState)
        builder.add_node("agent", self._call_tools)
        builder.add_node("tools", self._run_tools)
        builder.add_node("format", self._format_result)
        builder.add_edge(START, "agent")
        builder.add_edge("agent", "tools")
        builder.add_edge("tools", "format")
        builder.add_edge("format", END)
        return builder.compile()

    async def _call_tools(self, state: SubAgentState):
        """Invoca al LLM para decidir qué herramientas usar."""
        msgs = [SystemMessage(content=self.prompt)] + state["messages"]
        result = await self.llm.ainvoke(msgs)
        return {"messages": [result]}

    async def _run_tools(self, state: SubAgentState):
        """Ejecuta las herramientas seleccionadas."""
        return await self.tool_node.ainvoke(state)

    async def _format_result(self, state: SubAgentState):
        """Devuelve resultados de herramientas."""
        results = []
        for msg in state["messages"]:
            if isinstance(msg, ToolMessage):
                content = str(msg.content) if msg.content else ""
                tool_name = msg.name if hasattr(msg, 'name') else ""
                
                if "Error" in content:
                    results.append(f"Error: {content}")
                elif content in ["[]", "", "null", "None"]:
                    results.append("No hay notas guardadas para este cliente.")
                elif tool_name == "save_client_note" and content.isdigit():
                    results.append(f"Nota guardada correctamente (ID: {content})")
                elif tool_name == "delete_note":
                    results.append("Nota eliminada correctamente." if content == "True" else "No se pudo eliminar la nota.")
                else:
                    results.append(content)
        
        response = "\n".join(results) if results else "No hay notas guardadas."
        return {"messages": [AIMessage(content=response)]}

    async def run(self, messages: list) -> SubAgentState:
        """Ejecuta el agente con los mensajes proporcionados.
        
        Args:
            messages: Lista de mensajes de entrada.
            
        Returns:
            Estado final del agente.
        """
        return await self.graph.ainvoke({"messages": messages})

    def extract_final_response(self, result: SubAgentState) -> str:
        """Extrae la respuesta final del agente.
        
        Args:
            result: Estado final del agente.
            
        Returns:
            Texto de la respuesta.
        """
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                if not getattr(msg, 'tool_calls', None):
                    return msg.content.strip()
        return "Sin respuesta"
