import json
import re

from langgraph.graph import StateGraph, START, END
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

from apps.agents.state import AgentState
from shared.config.settings import settings
from shared.clients.a2a_client import A2AAgentClient
from .prompts import ROUTER_PROMPT, FINAL_ANSWER_PROMPT


def llm_retry():
    """Decorador para retry con backoff exponencial en llamadas al LLM."""
    return retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError,)),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
        before_sleep=lambda retry_state: print(
            f"[LLM Retry] Rate limit. Reintentando en {retry_state.next_action.sleep}s... "
            f"(intento {retry_state.attempt_number}/5)"
        )
    )


class Orchestrator:
    MAX_AGENTS_PER_PLAN = 8
    MAX_HISTORY_MESSAGES = 10

    def __init__(self):
        self.llm = ChatMistralAI(
            model="mistral-large-latest",
            temperature=0,
            api_key=settings.API_MISTRAL_KEY
        )
        self._llm_invoke = llm_retry()(self.llm.invoke)
        # Clientes A2A
        self._agent_clients = {
            "data_agent": A2AAgentClient(settings.A2A_DATA_AGENT_URL),
            "analysis_agent": A2AAgentClient(settings.A2A_ANALYSIS_AGENT_URL),
            "memory_agent": A2AAgentClient(settings.A2A_MEMORY_AGENT_URL),
        }
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()
        self._agent_cards: dict[str, dict] = {}
        self._router_prompt: str | None = None
    
    async def initialize(self):
        """Inicializa el orchestrator obteniendo las AgentCards de los subagentes.
        
        Debe llamarse antes de usar el orchestrator para que el router
        tenga información actualizada de las capacidades de cada agente.
        """
        await self._fetch_agent_cards()
    
    async def _fetch_agent_cards(self):
        """Obtiene las AgentCards de todos los subagentes via A2A."""
        for name, client in self._agent_clients.items():
            card = await client.get_agent_card()
            if card:
                self._agent_cards[name] = card
                print(f"[Orchestrator] AgentCard obtenida: {name} ({len(card.get('skills', []))} skills)")
            else:
                print(f"[Orchestrator] No se pudo obtener AgentCard de {name}")
        
        # Generar el prompt
        if self._agent_cards:
            from .prompts import generate_router_prompt
            self._router_prompt = generate_router_prompt(self._agent_cards)
    
    def get_router_prompt(self) -> str:
        """Devuelve el router prompt."""
        if self._router_prompt:
            return self._router_prompt
        return ROUTER_PROMPT

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
                # Patrón: "Nombre (ID: 123)"
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

        router_prompt_template = self.get_router_prompt()
        prompt = router_prompt_template.format(
            conversation_history=history_str,
            context_ids=context_ids_str,
            user_query=user_query
        )

        response = self._llm_invoke([
            SystemMessage(content="Responde solo con JSON válido."),
            HumanMessage(content=prompt)
        ])

        #formato [{"agent": "...", "task": "..."}]
        try:
            content = response.content.strip()
            content = re.sub(r'^```json\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
            raw_plan = json.loads(content)
            
            agent_plan = [
                {"agent": item["agent"], "task": item.get("task", "")}
                for item in raw_plan[:self.MAX_AGENTS_PER_PLAN]
                if isinstance(item, dict) and "agent" in item
            ]
        except (json.JSONDecodeError, Exception):
            agent_plan = []

        # DEBUG
        print(f"\n{'=' * 50}")
        print(f"ROUTER - Plan:")
        for step in agent_plan:
            print(f"  → {step['agent']}: {step['task'][:60]}...")
        print(f"Query: {user_query}")
        print(f"Context IDs: {context_ids}")
        print(f"{'=' * 50}\n")

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
        """Ejecuta el agente actual del plan con su tarea específica."""
        plan = state.get("agent_plan", [])
        step = state.get("current_step", 0)
        collected = state.get("collected_data", []).copy()

        if step >= len(plan):
            return {"current_step": step}

        current_step = plan[step]
        agent_name = current_step["agent"]
        task = current_step["task"]  # Tarea específica del router
        messages = state.get("messages", [])

        context = self._build_context_for_subagent(agent_name, task, collected, messages)

        client = self._agent_clients.get(agent_name)
        if client:
            response = await client.process_message(context)
            if response:
                display_name = agent_name.replace("_", " ").title().replace(" ", "")
                collected.append(f"[{display_name}]: {response}")

        return {
            "collected_data": collected,
            "current_step": step + 1
        }

    def _next_step(self, state: AgentState) -> str:
        """Decide si continuar con el siguiente agente o terminar."""
        plan = state.get("agent_plan", [])
        step = state.get("current_step", 0)
        return "continue" if step < len(plan) else "done"

    def _build_context_for_subagent(self, agent_name: str, task: str, collected: list, messages: list) -> str:
        """Construye contexto con la tarea específica del router."""
        context_parts = []

        # Combinar IDs del historial Y del collected_data actual
        context_ids = self._extract_context_ids(messages)
        collected_ids = self._extract_ids_from_collected(collected)
        all_ids = {**context_ids, **collected_ids}

        if all_ids:
            context_parts.append("IDs DISPONIBLES:")
            for name, pid in all_ids.items():
                clean_name = name.replace('"', '').replace("'", "").strip()
                context_parts.append(f"- {clean_name}: partner_id = {pid}")
            context_parts.append("")

        context_parts.append(f"TAREA: {task}")
        context_parts.append("\nEjecuta la tarea usando tus herramientas. NO inventes IDs.")

        return "\n".join(context_parts)

    def _extract_ids_from_collected(self, collected: list) -> dict:
        """Extrae IDs de los datos recopilados en pasos anteriores."""
        ids_found = {}

        for item in collected:
            # Patrón 1: "**Nombre** (ID: **123**)" formato markdown
            pattern_bold = r'\*\*([^*]+)\*\*\s*\(ID:\s*\*\*(\d+)\*\*\)'
            matches_bold = re.findall(pattern_bold, item)
            for name, pid in matches_bold:
                clean_name = name.strip()
                if clean_name and len(clean_name) > 2:
                    ids_found[clean_name] = int(pid)
            
            # Patrón 2: "Nombre (ID: 123)" formato general sin markdown
            matches = re.findall(r'([A-Za-zÀ-ÿ\s\.,&\-]+?)\s*\(ID:\s*(\d+)\)', item)
            for name, pid in matches:
                clean_name = name.strip().rstrip(':').strip()
                if clean_name and len(clean_name) > 2 and clean_name.lower() not in ['id', 'partner', 'cliente']:
                    ids_found[clean_name] = int(pid)

            # Patrón 3: "**Cliente: Nombre (ID: 123)**" - otro formato markdown
            pattern_markdown = r'\*\*Cliente:\s*(.+?)\s*\(ID:\s*(\d+)\)\*\*'
            matches_md = re.findall(pattern_markdown, item)
            for name, pid in matches_md:
                clean_name = name.strip()
                if clean_name:
                    ids_found[clean_name] = int(pid)

            # Patrón 4: "**Cliente N: Nombre**\n- ID: 123" - formato con ID en línea separada
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

    def _generate_final_answer(self, state: AgentState) -> dict:
        collected = state.get("collected_data", [])
        user_query = state.get("user_query", "")
        messages = state.get("messages", [])
        history_str = self._extract_conversation_history(messages)

        # DEBUG
        print(f"\n{'=' * 50}")
        print(f"FINAL ANSWER")
        print(f"Collected data: {collected}")
        print(f"{'=' * 50}\n")

        # Extraer gráficos JSON de los collected_data
        # se añaden al final de la respuesta del orquestador
        chart_jsons = []
        cleaned_collected = []
        for item in collected:
            temp = item.replace("CHART:CHART_JSON:", "CHART_JSON:")
            while "CHART_JSON:" in temp:
                idx = temp.find("CHART_JSON:")
                json_start = idx + len("CHART_JSON:")
                try:
                    chart_obj, end = json.JSONDecoder().raw_decode(temp[json_start:])
                    chart_jsons.append(json.dumps(chart_obj))
                    temp = temp[:idx] + temp[json_start + end:]
                except:
                    break
            cleaned_collected.append(temp.strip())

        # Prompt SIN gráfico
        system_instruction = (
            "Eres un asistente financiero profesional. "
            "Responde en español, sin emojis, de forma directa. "
            "Adapta la extensión a la complejidad de la pregunta. "
            "NO resumas datos numéricos. NO inventes datos."
        )

        if not collected:
            response = self._llm_invoke([
                SystemMessage(content=system_instruction),
                HumanMessage(content=f"Historial: {history_str}\n\nPregunta: {user_query}")
            ])
            final_response = response.content
        else:
            collected_str = "\n".join(cleaned_collected)
            prompt = FINAL_ANSWER_PROMPT.format(
                conversation_history=history_str,
                user_query=user_query,
                collected_data=collected_str
            )

            response = self._llm_invoke([
                SystemMessage(content=system_instruction),
                HumanMessage(content=prompt)
            ])
            final_response = response.content

        # Añadir gráficos directamente al final
        if chart_jsons:
            charts_str = " ".join([f"CHART_JSON:{cj}" for cj in chart_jsons])
            final_response = f"{final_response}\n\n{charts_str}"

        return {"messages": [AIMessage(content=final_response)]}

    async def _stream_final_answer(self, state: AgentState):
        """Genera la respuesta final en streaming."""
        collected = state.get("collected_data", [])
        user_query = state.get("user_query", "")
        messages = state.get("messages", [])
        history_str = self._extract_conversation_history(messages)

        # Extraer gráficos JSON
        chart_jsons = []
        cleaned_collected = []
        for item in collected:
            temp = item.replace("CHART:CHART_JSON:", "CHART_JSON:")
            while "CHART_JSON:" in temp:
                idx = temp.find("CHART_JSON:")
                json_start = idx + len("CHART_JSON:")
                try:
                    chart_obj, end = json.JSONDecoder().raw_decode(temp[json_start:])
                    chart_jsons.append(json.dumps(chart_obj))
                    temp = temp[:idx] + temp[json_start + end:]
                except:
                    break
            cleaned_collected.append(temp.strip())

        system_instruction = (
            "Eres un asistente financiero profesional. "
            "Responde en español, sin emojis, de forma directa. "
            "Adapta la extensión a la complejidad de la pregunta. "
            "NO resumas datos numéricos. NO inventes datos."
        )

        if not collected:
            msgs = [
                SystemMessage(content=system_instruction),
                HumanMessage(content=f"Historial: {history_str}\n\nPregunta: {user_query}")
            ]
        else:
            collected_str = "\n".join(cleaned_collected)
            prompt = FINAL_ANSWER_PROMPT.format(
                conversation_history=history_str,
                user_query=user_query,
                collected_data=collected_str
            )
            msgs = [
                SystemMessage(content=system_instruction),
                HumanMessage(content=prompt)
            ]

        async for chunk in self.llm.astream(msgs):
            if chunk.content:
                yield {"type": "token", "content": chunk.content}

        if chart_jsons:
            charts_str = " ".join([f"CHART_JSON:{cj}" for cj in chart_jsons])
            yield {"type": "charts", "content": charts_str}

    async def run(self, request: str, thread_id: str) -> str:
        config = {"configurable": {"thread_id": thread_id}}
        
        # Recuperar historial existente
        existing_state = self.graph.get_state(config)
        existing_messages = []
        if existing_state and existing_state.values:
            existing_messages = existing_state.values.get("messages", [])
        initial_state = {
            "messages": existing_messages + [HumanMessage(content=request)],
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
        """Procesa la solicitud emitiendo eventos de progreso."""
        config = {"configurable": {"thread_id": thread_id}}
        
        existing_state = self.graph.get_state(config)
        existing_messages = []
        if existing_state and existing_state.values:
            existing_messages = existing_state.values.get("messages", [])
        
        state = {
            "messages": existing_messages + [HumanMessage(content=request)],
            "user_query": request,
            "agent_plan": [],
            "current_step": 0,
            "collected_data": []
        }
        
        # Generar plan
        yield {"type": "status", "message": "Analizando consulta..."}
        router_result = self._router(state)
        state.update(router_result)
        plan = state.get("agent_plan", [])
        if plan:
            yield {"type": "plan", "tasks": [step["task"] for step in plan]}
        
        # Ejecutar plan y anunciar progreso
        for i, step in enumerate(plan):
            yield {
                "type": "progress",
                "step": i + 1,
                "total": len(plan),
                "agent": step["agent"],
                "task": step["task"]
            }
            state["current_step"] = i
            executor_result = await self._executor(state)
            state.update(executor_result)
        
        # Generación de respuesta final con streaming
        yield {"type": "status", "message": "Generando respuesta..."}
        
        full_response = ""
        async for event in self._stream_final_answer(state):
            if event["type"] == "token":
                full_response += event["content"]
                yield event
            elif event["type"] == "charts":
                # gráficos al final
                full_response += "\n\n" + event["content"]
        
        # Checkpointer
        state["messages"] = state["messages"] + [AIMessage(content=full_response)]
        self.graph.update_state(config, state)
        yield {"type": "complete", "response": full_response}
