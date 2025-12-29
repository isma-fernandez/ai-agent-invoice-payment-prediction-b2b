from langgraph.graph import StateGraph, START, END
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from src.config.settings import settings

from src.agents.state import AgentState
from src.agents.data_agent import DataAgent
from src.agents.analysis_agent import AnalysisAgent
from src.agents.memory_agent import MemoryAgent

ROUTER_PROMPT = """Decide qué agente debe responder. Responde SOLO con una palabra:

- data_agent: buscar clientes, información de clientes, ver facturas, facturas vencidas/pendientes
- analysis_agent: predicciones de riesgo, clientes de alto riesgo, tendencias, aging report, comparar clientes
- memory_agent: guardar notas, recordar algo, ver notas del cliente, alertas
- FINISH: ya tienes suficiente información para responder

Mensaje del usuario: {query}

Historial reciente:
{history}

Responde SOLO: data_agent, analysis_agent, memory_agent o FINISH"""


class Orchestrator:
    """Supervisor que coordina DataAgent, AnalysisAgent y MemoryAgent."""
    def __init__(self):
        self.llm = ChatMistralAI(
            model="mistral-large-latest",
            temperature=0,
            api_key=settings.API_MISTRAL_KEY
        )
        self.data_agent = DataAgent()
        self.analysis_agent = AnalysisAgent()
        self.memory_agent = MemoryAgent()
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self):
        """Construye el grafo del supervisor."""
        builder = StateGraph(AgentState)
        # Nodos
        builder.add_node("router", self._router)
        builder.add_node("data_agent", self._run_data_agent)
        builder.add_node("analysis_agent", self._run_analysis_agent)
        builder.add_node("memory_agent", self._run_memory_agent)

        # Grafo
        # START -> Router decide que agente usar -> Actúa el agente -> Router -> ... -> END
        builder.add_edge(START, "router")
        builder.add_conditional_edges("router", self._route, {
            "data_agent": "data_agent",
            "analysis_agent": "analysis_agent",
            "memory_agent": "memory_agent",
            "FINISH": END
        })
        builder.add_edge("data_agent", "router")
        builder.add_edge("analysis_agent", "router")
        builder.add_edge("memory_agent", "router")

        return builder.compile(checkpointer=self.checkpointer)

    def _router(self, state: AgentState) -> dict:
        """Decide a qué agente usar."""
        messages = state["messages"]
        user_msg = self._get_last_user_message(messages)
        # 6 últimos mensajes para el historial
        history = self._format_history(messages[-6:])

        prompt = ROUTER_PROMPT.format(query=user_msg, history=history)
        response = self.llm.invoke([HumanMessage(content=prompt)])
        decision = response.content.strip().lower()

        if "data_agent" in decision or "data" in decision:
            return {"next_agent": "data_agent"}
        elif "analysis_agent" in decision or "analysis" in decision:
            return {"next_agent": "analysis_agent"}
        elif "memory_agent" in decision or "memory" in decision:
            return {"next_agent": "memory_agent"}
        else:
            return {"next_agent": None}

    def _route(self, state: AgentState) -> str:
        """Función de routing basada en next_agent."""
        next_agent = state.get("next_agent")
        return next_agent if next_agent else "FINISH"

    async def _run_data_agent(self, state: AgentState) -> dict:
        """Ejecuta el DataAgent."""
        result = await self.data_agent.run(state["messages"])
        return {"messages": result["messages"]}

    async def _run_analysis_agent(self, state: AgentState) -> dict:
        """Ejecuta el AnalysisAgent."""
        result = await self.analysis_agent.run(state["messages"])
        return {"messages": result["messages"]}

    async def _run_memory_agent(self, state: AgentState) -> dict:
        """Ejecuta el MemoryAgent."""
        result = await self.memory_agent.run(state["messages"])
        return {"messages": result["messages"]}

    def _get_last_user_message(self, messages: list) -> str:
        """Obtiene el último mensaje del usuario."""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                return msg.content
            if hasattr(msg, 'type') and msg.type == 'human':
                return msg.content
        return ""

    def _format_history(self, messages: list) -> str:
        """Historial para el prompt para mejorar la precisión en el routing.
        Necesario también para que entienda el contexto de la conversación."""
        lines = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                lines.append(f"Usuario: {msg.content}\n")
            elif isinstance(msg, AIMessage):
                lines.append(f"Chatbot: {msg.content}\n")
        return "".join(lines) if lines else "sin historial"


    async def run(self, request: str, thread_id: str) -> str:
        """Procesa una solicitud y devuelve la respuesta."""
        config = {"configurable": {"thread_id": thread_id}}
        initial_state = {
            "messages": [HumanMessage(content=request)],
            "next_agent": None
        }

        final_state = await self.graph.ainvoke(initial_state, config=config)

        for msg in reversed(final_state["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                return msg.content

        return "No se ha podido procesar tu solicitud."


    async def stream(self, request: str, thread_id: str):
        """Procesa en modo streaming."""
        config = {"configurable": {"thread_id": thread_id}}
        initial_state = {
            "messages": [HumanMessage(content=request)],
            "next_agent": None
        }

        async for event in self.graph.astream_events(initial_state, config=config):
            yield event