from a2a.client import ClientFactory, ClientConfig
from a2a.types import Message, Part, TextPart
import uuid
import httpx


class A2AAgentClient:
    def __init__(self, base_url: str, timeout: int = 900):  # 15 minutos
        self.base_url = base_url
        self.timeout = timeout
    
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