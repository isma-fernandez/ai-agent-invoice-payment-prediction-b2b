import uuid
from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events import EventQueue
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentCapabilities, AgentSkill, Message, Part, TextPart
from shared.config.settings import settings


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


class OrchestratorExecutor(AgentExecutor):
    """Executor A2A para el orquestador."""

    def __init__(self, get_agent_func):
        super().__init__()
        self.get_agent = get_agent_func

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Procesa un mensaje A2A y envía la respuesta."""
        text_content = extract_text_from_message(context.message)

        if not text_content:
            response = create_a2a_response("Error: No hay contenido de texto")
            await event_queue.enqueue_event(response)
            return

        thread_id = context.context_id or str(uuid.uuid4())

        agent = await self.get_agent()
        response_text = await agent.process_request(text_content, thread_id)

        response = create_a2a_response(response_text)
        await event_queue.enqueue_event(response)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancela la ejecución del orquestador."""
        pass


def create_a2a_app(get_agent_func):
    """Crea la aplicación A2A para el orquestador."""
    agent_card = AgentCard(
        name="orchestrator",
        description="Orquestador del asistente de predicción de pagos B2B",
        version="1.0.0",
        url=settings.A2A_ORCHESTRATOR_URL,
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(
            streaming=False,
            state_transition_history=False,
            push_notifications=False,
            extensions=[]
        ),
        skills=[
            AgentSkill(
                id="process_query",
                name="process_query",
                description="Procesa consultas sobre facturación, clientes y predicciones de pago",
                tags=["invoices", "clients", "predictions", "payments"]
            ),
        ]
    )

    task_store = InMemoryTaskStore()
    executor = OrchestratorExecutor(get_agent_func)
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store
    )

    a2a_app = A2AFastAPIApplication(
        agent_card=agent_card,
        http_handler=request_handler
    )

    return a2a_app.build()
