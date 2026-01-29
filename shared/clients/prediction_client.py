import json
from fastmcp import Client
from shared.config.settings import settings

def _parse_result(result):
    """Extrae el contenido de un CallToolResult de fastmcp."""
    if result.is_error:
        raise Exception(f"Error MCP: {result.content}")
    text = result.content[0].text
    if text.startswith('[') or text.startswith('{'):
        return json.loads(text)
    return text

class PredictionMCPClient:
    """Cliente MCP para conectarse al servidor de predicción."""

    def __init__(self):
        self.server_url = settings.MCP_PREDICTION_URL
        self._client = None

    async def _get_client(self) -> Client:
        """Obtiene o crea el cliente MCP."""
        if self._client is None:
            self._client = Client(self.server_url)
        return self._client

    async def predict(self, invoice: dict, client_history: list) -> dict:
        """Predice el riesgo de impago de una factura.

        Args:
            invoice: Datos de la factura a predecir.
            client_history: Historial de facturas del cliente.

        Returns:
            dict con prediction y probabilities
        """
        client = await self._get_client()
        async with client:
            result = await client.call_tool(
                "predict_invoice",
                {"invoice": invoice, "client_history": client_history}
            )
            return _parse_result(result)

_prediction_client: PredictionMCPClient | None = None

def get_prediction_client() -> PredictionMCPClient:
    """Obtiene el cliente MCP de predicción.
    
    Returns:
        Instancia del cliente de predicción.
    """
    global _prediction_client
    if _prediction_client is None:
        _prediction_client = PredictionMCPClient()
    return _prediction_client
