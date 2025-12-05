from .state import AgentState
from langgraph.graph import StateGraph, START, END
from langchain_mistralai import ChatMistralAI
from config.settings import settings

LLM = ChatMistralAI(
    model="mistral-small-latest",
    temperature=0,
    max_retries=2,
    api_key=settings.API_MISTRAL_KEY,
)

class Graph:
    def __init__(self):
        self.graph_builder = StateGraph(AgentState)
        self.graph_builder.add_edge(START, "chatbot")
        self.graph_builder.add_node("chatbot", self.chatbot)
        self.graph_builder.add_edge("chatbot", END)
        self.graph = self.graph_builder.compile()
    
    def chatbot(self, state: AgentState):
        return {"messages": [LLM.invoke(state["messages"])]}
    
    def run(self, user_input: str) -> AgentState:
        initial_state: AgentState = {
            "messages": [{"role": "human", "content": user_input}],
            "client_id": None,
            "risk_category": None,
            "explanation": None,
        }
        final_state = self.graph.invoke(initial_state)
        return final_state