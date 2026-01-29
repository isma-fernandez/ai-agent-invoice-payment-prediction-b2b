from a2a.client import ClientFactory, ClientConfig
from a2a.types import Message, Part, TextPart
from a2a.client.errors import A2AClientJSONRPCError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
import uuid
import httpx


def is_rate_limit_error(exception):
    """Verifica si es un error de rate limit."""
    if isinstance(exception, A2AClientJSONRPCError):
        return "429" in str(exception) or "rate_limit" in str(exception).lower()
    return False


class A2AAgentClient:
    def __init__(self, base_url: str, timeout: int = 900):  # 15 minutos
        self.base_url = base_url
        self.timeout = timeout
        self._agent_card: dict | None = None
    
    async def get_agent_card(self) -> dict | None:
        """Obtiene la AgentCard del agente via /.well-known/agent.json.
        
        La AgentCard contiene información sobre las capacidades y skills
        del agente, útil para que el orchestrator sepa qué puede hacer.
        
        Returns:
            dict: AgentCard con name, description, skills, etc.
            None: Si no se pudo obtener la card.
        """
        if self._agent_card is not None:
            return self._agent_card
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(f"{self.base_url}/.well-known/agent.json")
                if response.status_code == 200:
                    self._agent_card = response.json()
                    return self._agent_card
        except Exception as e:
            print(f"Error obteniendo AgentCard de {self.base_url}: {e}")
        
        return None
    
    @retry(
        retry=retry_if_exception(is_rate_limit_error),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
        before_sleep=lambda rs: print(
            f"[A2A Retry] Rate limit del sub-agente. Reintentando en {rs.next_action.sleep:.1f}s... "
            f"(intento {rs.attempt_number}/5)"
        )
    )
    async def process_message(self, content: str) -> str:
        """Envía un mensaje al agente y devuelve la respuesta.
        
        Incluye retry con backoff exponencial para rate limits.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as httpx_client:
            config = ClientConfig(
                streaming=False,
                accepted_output_modes=["text/plain"],
                httpx_client=httpx_client
            )
            client = await ClientFactory.connect(
                agent=self.base_url,
                client_config=config,
            )
            
            message = Message(
                message_id=str(uuid.uuid4()),
                role="user",
                parts=[Part(root=TextPart(text=content))],
                kind="message"
            )
            
            response_text = ""
            async for response in client.send_message(message):
                if response.parts:
                    for part in response.parts:
                        if isinstance(part.root, TextPart):
                            response_text += part.root.text
            
            return response_text
