from .state import AgentState
from langgraph.graph import StateGraph, START, END
from langchain_mistralai import ChatMistralAI
from config.settings import settings
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode
from .tools import tools
from langgraph.checkpoint.memory import MemorySaver

SYSTEM_PROMPT = """Eres un asistente financiero especializado en análisis de riesgo de impago de facturas B2B.

Tu objetivo es ayudar a los usuarios a:
- Buscar información sobre clientes
- Consultar estadísticas de pago de clientes
- Ver facturas de clientes (pagadas, pendientes, vencidas)
- Predecir el riesgo de impago de facturas existentes o hipotéticas

FLUJO DE TRABAJO:
1. Antes de nada debes comprovar que la conexión con el sistema Odoo está activa usando la herramienta `check_connection`. Si no está activa, informa al usuario.
2. Si la conexión está activa, procede a ayudar al usuario:
2.1 Cuando el usuario mencione un cliente por nombre, usa `search_client` para obtener su ID.
2.2 Con el ID, puedes usar `get_client_info` para estadísticas o `get_client_invoices` para ver facturas.
2.3 Para predicciones, usa `predict_invoice_risk` (factura existente) o `predict_hypothetical_invoice` (factura nueva).

FORMATO DE RESPUESTA:
- Sé conciso y directo.
- Presenta los datos de forma clara.
- Si hay riesgo alto (Grave), destácalo.
- Siempre indica el nivel de confianza de las predicciones usando las probabilidades.

REGLAS:
- Nunca inventes información. Si no tienes datos suficientes, informa al usuario.
- Siempre verifica que el cliente o factura exista antes de proceder.
- No utilices información de tu conocimiento previo; basa tus respuestas únicamente en los datos proporcionados por las herramientas.
- Usa únicamente las herramientas disponibles para obtener información.
- Si alguna información o herramienta no está disponible, informa al usuario de manera clara.

GESTIÓN DE MEMORIA:
- Cuando consultes información de un cliente, usa primero `get_client_notes` para ver si hay notas previas.
- Si el usuario te pide recordar algo o detectas información importante sobre un cliente, usa `save_client_note`.
- Usa `save_alert` para situaciones críticas que requieran seguimiento.
- Usa `get_active_alerts` cuando el usuario pregunte por pendientes o alertas.

Responde en español."""

class Graph:
    def __init__(self):
        self.tools = ToolNode(tools)
        self.llm = ChatMistralAI(
            model="mistral-large-latest",
            temperature=0,
            max_retries=2,
            api_key=settings.API_MISTRAL_KEY,
        ).bind_tools(tools)

        self.memory = MemorySaver()
        self.graph = self._build_graph()
        
    
    def _build_graph(self):
        """Construye el grafo de estados del agente financiero."""
        # Arquitectura ReAct
        #   1. Comienza en START y va a "chatbot"
        #   2. Desde "chatbot", decide si usar una herramienta o terminar (END)
        #   3. Si usa una herramienta, va a "tools" y luego regresa a "chatbot"
        #   4. Repite hasta decidir terminar
        self.graph_builder = StateGraph(AgentState)
        self.graph_builder.add_edge(START, "chatbot")
        self.graph_builder.add_node("chatbot", self._chatbot)
        self.graph_builder.add_node("tools", self.tools)
        self.graph_builder.add_conditional_edges(
            "chatbot",
            self._condition_tools_or_end,
            {"tools": "tools", END: END},
        )
        self.graph_builder.add_edge("tools", "chatbot")
        return self.graph_builder.compile(checkpointer=self.memory)


    def _condition_tools_or_end(self, state: AgentState) -> str:
        """Decide si usar una herramienta o terminar la conversación."""
        last_message = state["messages"][-1]

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END


    def _chatbot(self, state: AgentState):
        messages = state["messages"]

        # Inyecto el prompt del sistema en cada llamada, necesario para
        # evitar que el prompt se pierda en llamadas sucesivas
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        
        result = self.llm.invoke(messages)
        return {"messages": [result]}


    async def stream(self, request: str, thread_id: str):
        config = {"configurable": {"thread_id": thread_id}}
        initial_state: AgentState = {
            "messages": [{"role": "human", "content": request}],
            "client_id": None,
            "risk_category": None,
            "explanation": None,
        }
        async for event in self.graph.astream_events(initial_state, config=config):
            yield event


    async def run(self, request: str, thread_id: str) -> AgentState:
        config = {"configurable": {"thread_id": thread_id}}
        initial_state: AgentState = {
            "messages": [{"role": "human", "content": request}],
            "client_id": None,
            "risk_category": None,
            "explanation": None,
        }
        final_state = await self.graph.ainvoke(initial_state, config=config)
        return final_state