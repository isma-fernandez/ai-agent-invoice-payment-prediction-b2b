from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events import EventQueue
from a2a.types import Message, Part, TextPart
from langchain_core.messages import HumanMessage
import uuid
from typing import Callable


def extract_text_from_message(message: Message) -> str:
    """Extrae el texto de un mensaje A2A."""
    if message.parts:
        for part in message.parts:
            if isinstance(part.root, TextPart):
                return part.root.text
    return ""


def create_a2a_response(text: str) -> Message:
    """Crea un mensaje de respuesta A2A."""
    return Message(
        message_id=str(uuid.uuid4()),
        role="agent",
        parts=[Part(root=TextPart(text=text))],
        kind="message"
    )


class BaseAgentExecutor(AgentExecutor):
    """Executor base para subagentes LangGraph."""

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

        text_content = extract_text_from_message(context.message)
        agent_name = self.langgraph_agent.__class__.__name__

        print(f"\n{'=' * 50}")
        print(f"[{agent_name}] REQUEST")
        print(f"Query: {text_content[:200]}{'...' if len(text_content) > 200 else ''}")
        print(f"{'=' * 50}\n")

        if not text_content:
            response = create_a2a_response("Error: No hay contenido de texto en el mensaje")
            await event_queue.enqueue_event(response)
            return

        result = await self.langgraph_agent.run([HumanMessage(content=text_content)])
        response_text = self.langgraph_agent.extract_final_response(result) or ""

        print(f"\n{'=' * 50}")
        print(f"[{agent_name}] RESPONSE")
        print(f"Response: {response_text[:500]}{'...' if len(response_text) > 500 else ''}")
        print(f"{'=' * 50}\n")

        response = create_a2a_response(response_text)
        await event_queue.enqueue_event(response)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass
