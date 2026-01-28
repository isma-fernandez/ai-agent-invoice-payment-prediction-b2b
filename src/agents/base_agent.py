import json
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from src.config.settings import settings
from .state import SubAgentState


class BaseAgent:
    """Clase base para todos los sub-agentes"""
    def __init__(self, prompt: str, tools: list, model: str = "mistral-large-latest"):
        self.MAX_MESSAGES = 20
        self.prompt = prompt
        self.tools = tools
        self.tool_node = ToolNode(tools)
        # Limito a mistral pero se podría modificar
        self.llm = ChatMistralAI(
            model=model,
            temperature=0,
            api_key=settings.API_MISTRAL_KEY,
        ).bind_tools(tools)
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(SubAgentState)
        builder.add_node("agent", self._chatbot)
        builder.add_node("tools", self._run_tools)
        builder.add_edge(START, "agent")
        builder.add_conditional_edges(
            "agent",
            self._should_use_tools,
            {"tools": "tools", "end": END}
        )
        builder.add_edge("tools", "agent")
        return builder.compile()

    def _prepare_messages_for_mistral(self, messages: list) -> list:
        """
        Reordena los mensajes de forma que el primero después del SystemMessage
        sea Human, en caso contrario la LLM pensaría que ya ha respondido.
        """
        # Primer mensaje
        if not messages:
            return [SystemMessage(content=self.prompt)]

        # Limitar mensajes para evitar pasarse de la ventana de contexto
        if len(messages) > self.MAX_MESSAGES:
            messages = messages[-self.MAX_MESSAGES:]

        msgs = [SystemMessage(content=self.prompt)]
        for msg in messages:
            msgs.append(msg)

        # TODO: Revisar esto
        if len(msgs) > 1 and not isinstance(msgs[1], HumanMessage):
            idx = None
            for i, msg in enumerate(msgs[1:], start=1):
                if isinstance(msg, HumanMessage):
                    idx = i
                    break
            if idx:
                human_msg = msgs.pop(idx)
                msgs.insert(1, human_msg)

        return msgs

    async def _chatbot(self, state: SubAgentState):
        rearranged_msgs = self._prepare_messages_for_mistral(state["messages"])
        result = await self.llm.ainvoke(rearranged_msgs)
        return {"messages": [result]}

    async def _run_tools(self, state: SubAgentState):
        return await self.tool_node.ainvoke(state)

    def _should_use_tools(self, state: SubAgentState) -> str:
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "end"

    async def run(self, messages: list) -> SubAgentState:
        return await self.graph.ainvoke({"messages": messages})

    def extract_final_response(self, result: SubAgentState) -> str:
        """Método para extraer la última respuesta del agente y los gráficos de las tools."""
        # Extraer gráficos de ToolMessages
        chart_jsons = []
        for msg in result["messages"]:
            if isinstance(msg, ToolMessage) and msg.content:
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                temp = content
                while "CHART_JSON:" in temp:
                    idx = temp.find("CHART_JSON:")
                    json_start = idx + len("CHART_JSON:")
                    try:
                        chart_obj, end = json.JSONDecoder().raw_decode(temp[json_start:])
                        chart_jsons.append(json.dumps(chart_obj))
                        temp = temp[json_start + end:]
                    except json.JSONDecodeError:
                        break
        # Extraer respuesta del AIMessage
        text_response = ""
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                content = msg.content
                if isinstance(content, list):
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif isinstance(block, str):
                            text_parts.append(block)
                    content = " ".join(text_parts)

                if content and content.strip():
                    if not getattr(msg, 'tool_calls', None):
                        text_response = content.strip()
                        break
        # Combinar respuesta con gráficos
        if chart_jsons:
            charts_str = " ".join([f"CHART_JSON:{cj}" for cj in chart_jsons])
            return f"{text_response} {charts_str}"
        
        return text_response