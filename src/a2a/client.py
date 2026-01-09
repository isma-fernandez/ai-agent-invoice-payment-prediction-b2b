from a2a.client import ClientFactory
from a2a.types import Message, Part, TextPart
import uuid

class A2AAgentClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self._client = None
    
    async def _get_client(self):
        if self._client is None:
            factory = ClientFactory()
            self._client = await factory.create_from_url(self.base_url)
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
        
        # Enviamos el mensaje y obtenemos la respuesta
        response = await client.send_message(message)
        
        # Extraemos el texto de la respuesta
        if response.parts and isinstance(response.parts[0].root, TextPart):
            return response.parts[0].root.text
        return ""