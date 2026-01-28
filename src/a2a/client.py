from a2a.client import ClientFactory, ClientConfig
from a2a.types import Message, Part, TextPart
import uuid
import httpx


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
    
    async def process_message(self, content: str) -> str:
        """Envía un mensaje al agente y devuelve la respuesta.
        
        Crea un cliente nuevo por cada mensaje para evitar problemas
        de conexión en entornos containerizados.
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