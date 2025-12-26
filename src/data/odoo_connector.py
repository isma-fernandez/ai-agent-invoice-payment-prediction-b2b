from config.settings import settings
import odoorpc
import asyncio


class OdooConnection:
    def __init__(self):
        self.url = settings.ODOO_URL
        self.db = settings.ODOO_DB
        self.username = settings.ODOO_USERNAME
        self.password = settings.ODOO_PASSWORD
        self.client = None


    async def connect(self):
        def _connect():
            client = odoorpc.ODOO(self.url)
            client.login(self.db, self.username, self.password)
            return client
        self.client = await asyncio.to_thread(_connect)
        return self.client


    async def is_connected(self) -> bool:
        return self.client is not None


    async def search_read(self, model, domain, fields, limit=0, offset=0):
        def _search_read():
            return self.client.env[model].search_read(domain, fields, limit=limit, offset=offset)
        return await asyncio.to_thread(_search_read)


    async def execute_kw(self, model, method, args, kwargs=None):
        def _execute():
            return self.client.execute_kw(model, method, args, kwargs or {})
        return await asyncio.to_thread(_execute)