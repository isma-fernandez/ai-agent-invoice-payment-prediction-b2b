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

    async def is_connected(self) -> bool:
        return self.client is not None and self.client.is_connected

    async def search_read(self, model, domain, fields, limit=0, offset=0):
        return await self.client.search_read(model, domain, fields, limit, offset)
    
    async def execute_kw(self, model, method, args, kwargs=None):
        return await self.client.execute_kw(model, method, args, kwargs)