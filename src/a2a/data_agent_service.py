# src/a2a/services/data_agent_service.py
import uvicorn
from a2a.server.agent_execution import AgentExecutor
from a2a.server.apps.rest import A2ARESTFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler, RequestContext
from a2a.server.events import EventQueue
from a2a.types import AgentCard, AgentCapabilities, Message, Part, TextPart
from langchain_core.messages import HumanMessage
from src.agents.data_agent import DataAgent
import uuid

agent_card = AgentCard(
    name="data_agent",
    description="Agente especializado en recuperación de datos del sistema Odoo ERP",
    version="1.0.0",
    # TODO: Añadir capabilities
    capabilities=AgentCapabilities(
        streaming=False,
        state_transition_history=False,
        push_notifications=False,
        extensions=[]
    )
)

class DataAgentExecutor(AgentExecutor):
    def __init__(self):
        super().__init__()
        self.langchain_agent = None
    
    async def initialize(self):
        """Inicializa el agente de datos."""
        if self.langchain_agent is None:
            self.langchain_agent = DataAgent()
    

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        await self.initialize()
        
        # Extraemos el mensaje de A2A
        message = context.message

        # Nos quedamos con el texto
        text_content = ""
        if message.parts:
            for part in message.parts:
                if isinstance(part.root, TextPart):
                    text_content = part.root.text
                    break

        # Si no hay texto, enviamos un mensaje de error
        if not text_content:
            response = Message(
                message_id=str(uuid.uuid4()),
                role="agent",
                parts=[Part(root=TextPart(text="Error: No hay contenido de texto en el mensaje"))],
                kind="message"
            )

            # Respondemos con el mensaje de error
            await event_queue.send_message(response)
            return
        
        # El agente de datos ejecuta la tarea
        result = await self.langchain_agent.run([HumanMessage(content=text_content)])
        response_text = self.langchain_agent.extract_final_response(result) or ""
        
        # Respondemos con el resultado
        response = Message(
            message_id=str(uuid.uuid4()),
            role="agent",
            parts=[Part(root=TextPart(text=response_text))],
            kind="message"
        )
        await event_queue.send_message(response)

executor = DataAgentExecutor()
request_handler = DefaultRequestHandler(agent_executor=executor)

a2a_app = A2ARESTFastAPIApplication(
    agent_card=agent_card,
    http_handler=request_handler
)

app = a2a_app.build()

@app.get("/health")
async def health():
    return {"status": "ok", "agent": "data_agent"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)