from .state import AgentState
from langgraph.graph import StateGraph, START, END
from langchain_mistralai import ChatMistralAI
from config.settings import settings
from langchain_core.messages import SystemMessage

SYSTEM_PROMPT = """Eres un asistente financiero especializado en análisis de riesgo de impago de facturas B2B.

Tu objetivo es ayudar a los usuarios a:
- Buscar información sobre clientes
- Consultar estadísticas de pago de clientes
- Ver facturas de clientes (pagadas, pendientes, vencidas)
- Predecir el riesgo de impago de facturas existentes o hipotéticas

FLUJO DE TRABAJO:
1. Cuando el usuario mencione un cliente por nombre, usa `search_client` para obtener su ID.
2. Con el ID, puedes usar `get_client_info` para estadísticas o `get_client_invoices` para ver facturas.
3. Para predicciones, usa `predict_invoice_risk` (factura existente) o `predict_hypothetical_invoice` (factura nueva).

FORMATO DE RESPUESTA:
- Sé conciso y directo.
- Presenta los datos de forma clara.
- Si hay riesgo alto (Grave), destácalo.
- Siempre indica el nivel de confianza de las predicciones usando las probabilidades.

Responde en español."""

class Graph:
    def __init__(self):
        self.graph = self._build_graph()

        self.llm = ChatMistralAI(
            model="mistral-small-latest",
            temperature=0,
            max_retries=2,
            api_key=settings.API_MISTRAL_KEY,
        )

        #TODO: añadir tools
    
    def _build_graph(self):
        """Construye el grafo de estados del agente financiero."""
        self.graph_builder = StateGraph(AgentState)
        self.graph_builder.add_edge(START, "chatbot")
        self.graph_builder.add_node("chatbot", self._chatbot)
        self.graph_builder.add_edge("chatbot", END)
        return self.graph_builder.compile()


    def _chatbot(self, state: AgentState):
        messages = state["messages"]

        if len(messages) == 1:
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        
        result = self.llm.invoke(messages)
        return {"messages": [result]}
    
    def run(self, user_input: str) -> AgentState:
        initial_state: AgentState = {
            "messages": [{"role": "human", "content": user_input}],
            "client_id": None,
            "risk_category": None,
            "explanation": None,
        }
        final_state = self.graph.invoke(initial_state)
        return final_state