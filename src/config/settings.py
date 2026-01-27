import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings): 
    # Configuración Odoo
    ODOO_URL: str
    ODOO_DB: str
    ODOO_USERNAME: str
    ODOO_PASSWORD: str

    # Mistral
    API_MISTRAL_KEY: str

    # LangSmith
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str | None = None
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com" # Default usa ...

    # A2A
    A2A_DATA_AGENT_URL: str = "http://localhost:8001"
    A2A_ANALYSIS_AGENT_URL: str = "http://localhost:8002"
    A2A_MEMORY_AGENT_URL: str = "http://localhost:8003"

    # Servidores MCP
    MCP_MEMORY_URL: str = "http://localhost:8100/mcp"
    MCP_PREDICTION_URL: str = "http://localhost:8200/mcp"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

if settings.LANGCHAIN_TRACING_V2 and settings.LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT