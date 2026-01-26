from pydantic_settings import BaseSettings, SettingsConfigDict

class PredictionMCPSettings(BaseSettings):
    """Configuración del servidor MCP de predicción."""
    MODEL_PATH: str = "models/late_invoice_payment_classification.pkl"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

prediction_mcp_settings = PredictionMCPSettings()
