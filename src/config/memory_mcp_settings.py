from pydantic_settings import BaseSettings, SettingsConfigDict


class MemoryMCPSettings(BaseSettings):
    """Configuración para el servidor MCP de memoria."""
    
    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "ismael"
    POSTGRES_PASSWORD: str = "ismael"
    POSTGRES_DB: str = "memory"

    model_config = SettingsConfigDict(env_file=".env",env_file_encoding="utf-8")


memory_settings = MemoryMCPSettings()
