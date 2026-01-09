from a2a.client import ClientFactory, ClientConfig
from a2a.types import Message, Part, TextPart, TransportProtocol
import uuid
import httpx

class A2AAgentClient:
    def __init__(self, base_url: str, timeout: int = 1200):
        self.base_url = base_url
        self._client = None
        self.timeout = timeout
    
    async def _get_client(self):
        if self._client is None:
            httpx_client = httpx.AsyncClient(timeout=self.timeout)
            # Preferencias del cliente
            config = ClientConfig(
                streaming=False,
                accepted_output_modes=["text/plain"],
                httpx_client=httpx_client
            )
            self._client = await ClientFactory.connect(
                agent=self.base_url,
                client_config=config,
            )
        return self._client
    
    async def process_message(self, content: str) -> str:
        client = await self._get_client()
        
        # Mensaje en formato A2A
        message = Message(
            message_id=str(uuid.uuid4()),
            role="user",
            parts=[Part(root=TextPart(text=content))],
            kind="message"
        )
        
        # send_message devuelve un async generator
        # esto es debido a streaming
        response_text = ""
        async for response in client.send_message(message):
            # Extraemos el texto de cada respuesta parcial
            if response.parts:
                for part in response.parts:
                    if isinstance(part.root, TextPart):
                        response_text += part.root.text
        
        return response_text