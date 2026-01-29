import json
from fastmcp import Client
from shared.config.settings import settings


def _parse_result(result):
    """Extrae el texto de un CallToolResult de fastmcp."""
    if result.is_error:
        raise Exception(f"Error MCP: {result.content}")

    text = result.content[0].text
    
    # Si es json
    if text.startswith('[') or text.startswith('{'):
        return json.loads(text)
    
    return text


class MemoryMCPClient:
    """Cliente MCP para conectarse al servidor de memoria."""

    def __init__(self):
        self.server_url = settings.MCP_MEMORY_URL
        self._client = None

    async def _get_client(self) -> Client:
        """Obtiene o crea el cliente MCP."""
        if self._client is None:
            self._client = Client(self.server_url)
        return self._client

    async def save_client_note(self, partner_id: int, partner_name: str, note: str) -> str:
        """Guarda una nota sobre un cliente."""
        client = await self._get_client()
        async with client:
            result = await client.call_tool(
                "save_client_note",
                {"partner_id": partner_id, "partner_name": partner_name, "note": note}
            )
            return _parse_result(result)

    async def get_client_notes(self, partner_id: int) -> list[dict]:
        """Recupera las notas de un cliente."""
        client = await self._get_client()
        async with client:
            result = await client.call_tool(
                "get_client_notes",
                {"partner_id": partner_id}
            )
            return _parse_result(result) or []

    async def save_alert(self, content: str, partner_id: int = None, partner_name: str = None) -> str:
        """Guarda una alerta."""
        client = await self._get_client()
        async with client:
            args = {"content": content}
            if partner_id is not None:
                args["partner_id"] = partner_id
            if partner_name is not None:
                args["partner_name"] = partner_name
            result = await client.call_tool("save_alert", args)
            return _parse_result(result)

    async def get_active_alerts(self, limit: int = 10) -> list[dict]:
        """Recupera las alertas activas."""
        client = await self._get_client()
        async with client:
            result = await client.call_tool(
                "get_active_alerts",
                {"limit": limit}
            )
            return _parse_result(result) or []


_memory_client: MemoryMCPClient | None = None


def get_memory_client() -> MemoryMCPClient:
    """Obtiene el cliente MCP de memoria (singleton)."""
    global _memory_client
    if _memory_client is None:
        _memory_client = MemoryMCPClient()
    return _memory_client
