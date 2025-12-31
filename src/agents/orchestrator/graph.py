from langgraph.graph import StateGraph, START, END
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from src.config.settings import settings

from src.agents.state import AgentState
from src.agents.data_agent import DataAgent
from src.agents.analysis_agent import AnalysisAgent
from src.agents.memory_agent import MemoryAgent
from .prompts import ROUTER_PROMPT, FINAL_ANSWER_PROMPT


class Orchestrator:
    """Orquestador que coordina agentes y sintetiza respuestas."""
    # TODO: Mencionado en el estado también pero habría que buscar otra solución para los bucles infinitos
    MAX_ITERATIONS = 5
    MAX_HISTORY_MESSAGES = 10

    def __init__(self):
        self.llm = ChatMistralAI(
            model="mistral-large-latest",
            temperature=0,
            api_key=settings.API_MISTRAL_KEY
        )
        # TODO: Esto en vez de crearse aquí, se tendrían que comunicar a través de MCP
        self.data_agent = DataAgent()
        self.analysis_agent = AnalysisAgent()
        # TODO: No funciona ...
        self.memory_agent = MemoryAgent()
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(AgentState)

        # Nodos
        builder.add_node("router", self._router)
        builder.add_node("data_agent", self._run_data_agent)
        builder.add_node("analysis_agent", self._run_analysis_agent)
        builder.add_node("memory_agent", self._run_memory_agent)
        builder.add_node("final_answer", self._generate_final_answer)

        # Grafo
        # Petición -> Router -> Agente -> Router -> ... -> Sintentizador -> Respuesta final
        builder.add_edge(START, "router")
        builder.add_conditional_edges("router", self._route, {
            "data_agent": "data_agent",
            "analysis_agent": "analysis_agent",
            "memory_agent": "memory_agent",
            "final_answer": "final_answer"
        })
        builder.add_edge("data_agent", "router")
        builder.add_edge("analysis_agent", "router")
        builder.add_edge("memory_agent", "router")
        builder.add_edge("final_answer", END)

        return builder.compile(checkpointer=self.checkpointer)

    def _extract_conversation_history(self, messages: list) -> str:
        """Extrae el historial de conversación de los mensajes."""
        if not messages:
            return "Sin historial previo."

        # Tomamos los últimos N mensajes (excluyendo el mensaje actual)
        recent = messages[:-1] if len(messages) > 1 else []
        recent = recent[-self.MAX_HISTORY_MESSAGES:]
        if not recent:
            return "Sin historial previo."

        # Construimos el historial
        lines = []
        for msg in recent:
            if isinstance(msg, HumanMessage):
                lines.append(f"Usuario: {msg.content}")
            elif isinstance(msg, AIMessage) and msg.content:
                content = msg.content
                lines.append(f"Asistente: {content}")

        return "\n".join(lines) if lines else "Sin historial previo."

    def _router(self, state: AgentState) -> dict:
        """Decide qué agente usar en base a la información recopilada."""
        curr_info = state.get("collected_data", [])
        user_query = state.get("user_query", "")
        iterations = state.get("iterations", 0)
        messages = state.get("messages", [])

        # Evitar bucles infinitos
        # TODO: Mencionado en varios sitios, se debe buscar otra solución
        if iterations >= self.MAX_ITERATIONS:
            return {"next_agent": None, "iterations": iterations + 1}

        # Formateamos los datos existentes
        collected_str = "\n".join(curr_info) if curr_info else "Ninguna información recopilada aún."
        history_str = self._extract_conversation_history(messages)

        prompt = ROUTER_PROMPT.format(
            conversation_history=history_str,
            collected_data=collected_str,
            user_query=user_query
        )

        # TODO: SystemMessage redundante con el prompt, sacado de la antigua arquitectura
        response = self.llm.invoke([
            SystemMessage(
                content="Eres un router que decide qué agente usar. "
                        "Responde solo con el nombre del agente o FINISH."),
            HumanMessage(content=prompt)
        ])

        decision = response.content.strip().lower()

        if "data_agent" in decision or "data" in decision:
            next_agent = "data_agent"
        elif "analysis_agent" in decision or "analysis" in decision:
            next_agent = "analysis_agent"
        elif "memory_agent" in decision or "memory" in decision:
            next_agent = "memory_agent"
        else:
            next_agent = None

        return {"next_agent": next_agent, "iterations": iterations + 1}

    def _route(self, state: AgentState) -> str:
        next_agent = state.get("next_agent")
        if next_agent:
            return next_agent
        return "final_answer"

    # TODO: Código redundante
    async def _run_data_agent(self, state: AgentState) -> dict:
        user_query = state.get("user_query", "")
        collected = state.get("collected_data", []).copy()
        messages = state.get("messages", [])
        context = self._build_context_for_subagent(user_query, collected, messages)

        result = await self.data_agent.run([HumanMessage(content=context)])
        response = self.data_agent.extract_final_response(result)
        if response:
            collected.append(f"[DataAgent]: {response}")

        return {"collected_data": collected}

    async def _run_analysis_agent(self, state: AgentState) -> dict:
        user_query = state.get("user_query", "")
        collected = state.get("collected_data", []).copy()
        messages = state.get("messages", [])
        context = self._build_context_for_subagent(user_query, collected, messages)

        result = await self.analysis_agent.run([HumanMessage(content=context)])
        response = self.analysis_agent.extract_final_response(result)
        if response:
            collected.append(f"[AnalysisAgent]: {response}")

        return {"collected_data": collected}

    async def _run_memory_agent(self, state: AgentState) -> dict:
        user_query = state.get("user_query", "")
        collected = state.get("collected_data", []).copy()
        messages = state.get("messages", [])
        context = self._build_context_for_subagent(user_query, collected, messages)

        result = await self.memory_agent.run([HumanMessage(content=context)])
        response = self.memory_agent.extract_final_response(result)
        if response:
            collected.append(f"[MemoryAgent]: {response}")

        return {"collected_data": collected}

    # TODO: Valorar simplificar método con el del orquestador
    def _build_context_for_subagent(self, user_query: str, collected: list, messages: list) -> str:
        context_parts = []
        history = self._extract_conversation_history(messages)
        if history != "Sin historial previo.":
            context_parts.append(f"HISTORIAL DE CONVERSACIÓN:\n{history}\n")
        context_parts.append(f"SOLICITUD ACTUAL: {user_query}")

        if collected:
            context_parts.append("\nINFORMACIÓN YA RECOPILADA:")
            for item in collected:
                context_parts.append(item)
            context_parts.append(
                "\nIMPORTANTE: Usa los IDs (partner_id, invoice_id) de la información recopilada. NO inventes IDs.")
        context_parts.append(
            "\nIMPORTANTE: Si la solicitud hace referencia a algo del historial (ej: 'sus facturas', 'de ese cliente'), usa ese contexto para identificar el cliente/factura correcta.")

        return "\n".join(context_parts)

    def _generate_final_answer(self, state: AgentState) -> dict:
        collected = state.get("collected_data", [])
        user_query = state.get("user_query", "")
        messages = state.get("messages", [])
        history_str = self._extract_conversation_history(messages)

        system_instruction = (
            "Eres un asistente financiero profesional. "
            "Responde en español, sin emojis, de forma directa. "
            "Adapta la extensión a la complejidad de la pregunta. "
            "NO resumas datos numéricos. NO inventes datos."
        )

        if not collected:
            response = self.llm.invoke([
                SystemMessage(content=system_instruction),
                HumanMessage(content=f"Historial: {history_str}\n\nPregunta: {user_query}")
            ])
            final_response = response.content
        else:
            collected_str = "\n".join(collected)
            prompt = FINAL_ANSWER_PROMPT.format(
                conversation_history=history_str,
                user_query=user_query,
                collected_data=collected_str
            )

            response = self.llm.invoke([
                SystemMessage(
                    content="Genera una respuesta clara y útil basada SOLO en la información proporcionada. NO inventes datos."),
                HumanMessage(content=prompt)
            ])
            final_response = response.content

        return {"messages": [AIMessage(content=final_response)]}

    async def run(self, request: str, thread_id: str) -> str:
        config = {"configurable": {"thread_id": thread_id}}
        initial_state = {
            "messages": [HumanMessage(content=request)],
            "user_query": request,
            "next_agent": None,
            "collected_data": [],
            "iterations": 0
        }
        final_state = await self.graph.ainvoke(initial_state, config=config)

        for msg in reversed(final_state.get("messages", [])):
            if isinstance(msg, AIMessage) and msg.content:
                return msg.content

        return "No se pudo procesar tu solicitud."

    async def stream(self, request: str, thread_id: str):
        config = {"configurable": {"thread_id": thread_id}}
        initial_state = {
            "messages": [HumanMessage(content=request)],
            "user_query": request,
            "next_agent": None,
            "collected_data": [],
            "iterations": 0
        }

        async for event in self.graph.astream_events(initial_state, config=config):
            yield event