from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings): 
    # Configuración Odoo
    ODOO_URL: str
    ODOO_DB: str
    ODOO_USERNAME: str
    ODOO_PASSWORD: str
    API_MISTRAL_KEY: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()


