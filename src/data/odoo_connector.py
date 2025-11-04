from config.settings import settings
from mcp_odoo.odoo.client import OdooClient

class OdooConnection:
    def __init__(self):
        self.url = settings.ODOO_URL
        self.db = settings.ODOO_DB
        self.username = settings.ODOO_USERNAME
        self.password = settings.ODOO_PASSWORD
        self.client = None

    async def connect(self):
        self.client = OdooClient(
            url=self.url,
            database=self.db,
            username=self.username,
            password=self.password
        )
        await self.client.connect()
        return self.client

    async def search_read(self, model, domain, fields):
        return await self.client.search_read(model, domain, fields)
    
    async def execute_kw(self, model, method, args, kwargs=None):
        return await self.client.execute_kw(model, method, args, kwargs)