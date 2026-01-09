# src/a2a/base.py
from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, TextPart
from langchain_core.messages import HumanMessage
import uuid
from typing import Callable


class BaseAgentExecutor(AgentExecutor):  
    def __init__(self, agent_factory: Callable):
        """
        Args:
            agent_factory: Función que devuelve el agente LangGraph
        """
        super().__init__()  
        self.agent_factory = agent_factory
        self.langgraph_agent = None
    
    async def initialize(self):
        """Inicializa el agente LangGraph."""
        if self.langgraph_agent is None:
            self.langgraph_agent = self.agent_factory()
    
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
            await event_queue.send_message(response)
            return
        
        # El agente ejecuta la tarea
        result = await self.langgraph_agent.run([HumanMessage(content=text_content)])
        response_text = self.langgraph_agent.extract_final_response(result) or ""
        
        # Respondemos con el resultado
        response = Message(
            message_id=str(uuid.uuid4()),
            role="agent",
            parts=[Part(root=TextPart(text=response_text))],
            kind="message"
        )
        await event_queue.send_message(response)
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass