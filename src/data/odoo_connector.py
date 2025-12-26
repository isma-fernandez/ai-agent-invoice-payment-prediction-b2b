from config.settings import settings
import odoorpc


class OdooConnection:
    def __init__(self):
        self.url = settings.ODOO_URL
        self.db = settings.ODOO_DB
        self.username = settings.ODOO_USERNAME
        self.password = settings.ODOO_PASSWORD
        self.client = None
        self._connected = False

    def connect(self):
        self.client = odoorpc.ODOO(self.url)
        self.client.login(self.db, self.username, self.password)
        self._connected = True
        return self.client

    def is_connected(self) -> bool:
        return self._connected and self.client is not None

    def search_read(self, model, domain, fields, limit=0, offset=0):
        return self.client.env[model].search_read(domain, fields, limit=limit, offset=offset)

    def execute_kw(self, model, method, args, kwargs=None):
        return self.client.execute_kw(model, method, args, kwargs or {})