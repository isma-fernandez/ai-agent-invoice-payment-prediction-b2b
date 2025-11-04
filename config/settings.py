from pydantic_settings import BaseSettings

class Settings(BaseSettings): 
    # Configuración Odoo
    ODOO_URL: str
    ODOO_DB: str
    ODOO_USERNAME: str
    ODOO_PASSWORD: str

settings = Settings()


