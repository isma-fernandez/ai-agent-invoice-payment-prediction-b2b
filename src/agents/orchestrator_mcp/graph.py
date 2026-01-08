"""
Orchestrator con comunicación MCP a sub-agentes.

En lugar de instanciar los agentes localmente, se comunica con ellos
vía MCP como servicios remotos.
"""
import json
import re

from langgraph.graph import StateGraph, START, END
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver

from src.config.settings import settings
from src.agents.state import AgentState
# Cliente MCP
# TODO: implementar
from .prompts import ROUTER_PROMPT, FINAL_ANSWER_PROMPT


class Orchestrator:
    """Orchestrator que coordina sub-agentes vía MCP."""

    MAX_AGENTS_PER_PLAN = 8
    MAX_HISTORY_MESSAGES = 10

    def __init__(self):
        self.llm = ChatMistralAI(
            model="mistral-large-latest",
            temperature=0,
            api_key=settings.API_MISTRAL_KEY
        )

        # Cliente MCP
        # TODO: implementar

        self.checkpointer = MemorySaver()
        self.graph = None  # Se construye después de conectar

    async def initialize(self):
        """Conecta con los sub-agentes MCP."""
        # Cliente MCP
        # TODO: implementar
        await self.subagents.connect_all()
        self.graph = self._build_graph()

    async def shutdown(self):
        """Desconecta de los sub-agentes."""
        if self.subagents:
            await self.subagents.disconnect_all()

    def _build_graph(self):
        builder = StateGraph(AgentState)

        builder.add_node("router", self._router)
        builder.add_node("executor", self._executor)
        builder.add_node("final_answer", self._generate_final_answer)

        builder.add_edge(START, "router")
        builder.add_conditional_edges("router", self._should_execute, {
            "execute": "executor",
            "finish": "final_answer"
        })
        builder.add_conditional_edges("executor", self._next_step, {
            "continue": "executor",
            "done": "final_answer"
        })
        builder.add_edge("final_answer", END)

        return builder.compile(checkpointer=self.checkpointer)

    def _extract_context_ids(self, messages: list) -> dict:
        """Extrae partner_ids mencionados en el historial."""
        ids_found = {}
        for msg in messages:
            if hasattr(msg, 'content') and msg.content:
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                matches = re.findall(r'([A-Za-zÀ-ÿ\s\.,&]+?)\s*\(ID:\s*(\d+)\)', content)
                for name, pid in matches:
                    ids_found[name.strip()] = int(pid)
        return ids_found

    def _router(self, state: AgentState) -> dict:
        """Planifica qué agentes ejecutar."""
        user_query = state.get("user_query", "")
        messages = state.get("messages", [])

        history_str = self._extract_conversation_history(messages)
        context_ids = self._extract_context_ids(messages)

        context_ids_str = "\n".join([f"- {name}: partner_id = {pid}" for name, pid in context_ids.items()])
        if not context_ids_str:
            context_ids_str = "Ninguno disponible"

        prompt = ROUTER_PROMPT.format(
            conversation_history=history_str,
            context_ids=context_ids_str,
            user_query=user_query
        )

        response = self.llm.invoke([
            SystemMessage(content="Responde solo con JSON válido."),
            HumanMessage(content=prompt)
        ])

        try:
            content = response.content.strip()
            content = re.sub(r'^```json\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
            agent_plan = json.loads(content)
            if not isinstance(agent_plan, list):
                agent_plan = []
        except (json.JSONDecodeError, Exception):
            agent_plan = []

        agent_plan = agent_plan[:self.MAX_AGENTS_PER_PLAN]

        return {
            "agent_plan": agent_plan,
            "current_step": 0,
            "collected_data": []
        }

    def _should_execute(self, state: AgentState) -> str:
        """Decide si hay agentes que ejecutar."""
        plan = state.get("agent_plan", [])
        return "execute" if plan else "finish"

    async def _executor(self, state: AgentState) -> dict:
        """Ejecuta el agente actual del plan VÍA MCP."""
        plan = state.get("agent_plan", [])
        step = state.get("current_step", 0)
        collected = state.get("collected_data", []).copy()

        if step >= len(plan):
            return {"current_step": step}

        agent_name = plan[step]
        user_query = state.get("user_query", "")
        messages = state.get("messages", [])

        context = self._build_context_for_subagent(user_query, collected, messages)

        try:
            response = await self.subagents.invoke(agent_name, context)

            if response:
                # Formatear igual que antes para mantener compatibilidad
                agent_label = {
                    "data_agent": "DataAgent",
                    "analysis_agent": "AnalysisAgent",
                    "memory_agent": "MemoryAgent"
                }.get(agent_name, agent_name)

                collected.append(f"[{agent_label}]: {response}")

        except Exception as e:
            print(f"Error invocando {agent_name}: {e}")
            collected.append(f"[{agent_name}]: Error - {str(e)}")

        return {
            "collected_data": collected,
            "current_step": step + 1
        }

    def _next_step(self, state: AgentState) -> str:
        """Decide si continuar con el siguiente agente o terminar."""
        plan = state.get("agent_plan", [])
        step = state.get("current_step", 0)
        return "continue" if step < len(plan) else "done"

    def _build_context_for_subagent(self, user_query: str, collected: list, messages: list) -> str:
        """Contexto mínimo y limpio para el subagente."""
        context_parts = []

        context_ids = self._extract_context_ids(messages)
        collected_ids = self._extract_ids_from_collected(collected)
        all_ids = {**context_ids, **collected_ids}

        if all_ids:
            context_parts.append("IDs DISPONIBLES (usar estos):")
            for name, pid in all_ids.items():
                clean_name = name.replace('"', '').replace("'", "").strip()
                context_parts.append(f"- {clean_name}: partner_id = {pid}")
            context_parts.append("")

        context_parts.append(f"SOLICITUD: {user_query}")
        context_parts.append("\nNO inventes IDs. Usa solo los proporcionados arriba.")

        return "\n".join(context_parts)

    def _extract_ids_from_collected(self, collected: list) -> dict:
        """Extrae IDs de los datos recopilados en pasos anteriores."""
        ids_found = {}

        for item in collected:
            matches = re.findall(r'([A-Za-zÀ-ÿ\s\.,&\-]+?)\s*\(ID:\s*(\d+)\)', item)
            for name, pid in matches:
                clean_name = name.strip().rstrip(':').strip()
                if clean_name and len(clean_name) > 2 and clean_name.lower() not in ['id', 'partner', 'cliente']:
                    ids_found[clean_name] = int(pid)

            pattern_markdown = r'\*\*Cliente:\s*(.+?)\s*\(ID:\s*(\d+)\)\*\*'
            matches_md = re.findall(pattern_markdown, item)
            for name, pid in matches_md:
                clean_name = name.strip()
                if clean_name:
                    ids_found[clean_name] = int(pid)

            pattern_multiline = r'\*\*(?:Cliente \d+:\s*)?([A-Za-zÀ-ÿ\s\.,&\-]+?)\*\*\s*\n-\s*ID:\s*(\d+)'
            matches_ml = re.findall(pattern_multiline, item)
            for name, pid in matches_ml:
                clean_name = name.strip()
                if clean_name:
                    ids_found[clean_name] = int(pid)

        return ids_found

    def _extract_conversation_history(self, messages: list) -> str:
        """Extrae el historial de conversación de los mensajes."""
        if not messages:
            return "Sin historial previo."

        recent = messages[:-1] if len(messages) > 1 else []
        recent = recent[-self.MAX_HISTORY_MESSAGES:]
        if not recent:
            return "Sin historial previo."

        lines = []
        for msg in recent:
            if isinstance(msg, HumanMessage):
                lines.append(f"Usuario: {msg.content}")
            elif isinstance(msg, AIMessage) and msg.content:
                content = msg.content
                lines.append(f"Asistente: {content}")

        return "\n".join(lines) if lines else "Sin historial previo."

    def _generate_final_answer(self, state: AgentState) -> dict:
        collected = state.get("collected_data", [])
        user_query = state.get("user_query", "")
        messages = state.get("messages", [])
        history_str = self._extract_conversation_history(messages)

        chart_markers = []
        for item in collected:
            charts = re.findall(r'CHART:[a-f0-9]+', item)
            chart_markers.extend(charts)

        charts_instruction = ""
        if chart_markers:
            charts_instruction = f"\n\nINCLUYE OBLIGATORIAMENTE estos marcadores de gráfico AL FINAL de tu respuesta (en una línea separada, tal cual): {' '.join(chart_markers)}"

        system_instruction = (
                "Eres un asistente financiero profesional. "
                "Responde en español, sin emojis, de forma directa. "
                "Adapta la extensión a la complejidad de la pregunta. "
                "NO resumas datos numéricos. NO inventes datos."
                + charts_instruction
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
                SystemMessage(content=system_instruction),
                HumanMessage(content=prompt)
            ])
            final_response = response.content

        return {"messages": [AIMessage(content=final_response)]}

    async def run(self, request: str, thread_id: str) -> str:
        config = {"configurable": {"thread_id": thread_id}}
        initial_state = {
            "messages": [HumanMessage(content=request)],
            "user_query": request,
            "agent_plan": [],
            "current_step": 0,
            "collected_data": []
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
            "agent_plan": [],
            "current_step": 0,
            "collected_data": []
        }

        async for event in self.graph.astream_events(initial_state, config=config):
            yield event
