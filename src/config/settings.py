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
    LANGCHAIN_PROJECT: str = "tfg-financial-agent"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()


