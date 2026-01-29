from shared.config.settings import settings
import odoorpc
import asyncio


class OdooConnection:
    """Gestiona la conexión con Odoo mediante JSON-RPC."""

    def __init__(self):
        # Validar que las credenciales estén en el entorno
        if not all([settings.ODOO_URL, settings.ODOO_DB, 
                    settings.ODOO_USERNAME, settings.ODOO_PASSWORD]):
            raise ValueError("Credenciales de Odoo no configuradas. "
                "Asegúrate de definir ODOO_URL, ODOO_DB, ODOO_USERNAME y ODOO_PASSWORD.")
        self.url = settings.ODOO_URL
        self.db = settings.ODOO_DB
        self.username = settings.ODOO_USERNAME
        self.password = settings.ODOO_PASSWORD
        self.client = None


    async def connect(self):
        """Establece la conexión con Odoo.

        Returns:
            Cliente ODOO conectado y autenticado.
        """
        def _connect():
            host = self.url.replace("https://", "").split(":")[0].split("/")[0]
            port = 443
            protocol = "jsonrpc+ssl"
            client = odoorpc.ODOO(host, protocol=protocol, port=port)
            client.login(self.db, self.username, self.password)
            return client
        self.client = await asyncio.to_thread(_connect)
        return self.client


    async def is_connected(self) -> bool:
        """Verifica si hay una conexión activa.

        Returns:
            True si está conectado, False en caso contrario.
        """
        return self.client is not None


    async def search_read(self, model, domain, fields, limit=0, offset=0):
        """Ejecuta search_read en Odoo.

        Args:
            model: Nombre del modelo de Odoo.
            domain: Filtros de búsqueda.
            fields: Campos a recuperar.
            limit: Número máximo de registros.
            offset: Desplazamiento inicial.

        Returns:
            Lista de registros encontrados.
        """
        def _search_read():
            return self.client.env[model].search_read(domain, fields, limit=limit, offset=offset)
        return await asyncio.to_thread(_search_read)


    async def execute_kw(self, model, method, args, kwargs=None):
        """Ejecuta un método en un modelo de Odoo.

        Args:
            model: Nombre del modelo.
            method: Nombre del método a ejecutar.
            args: Argumentos posicionales.
            kwargs: Argumentos con nombre.

        Returns:
            Resultado del método ejecutado.
        """
        def _execute():
            return self.client.execute_kw(model, method, args, kwargs or {})
        return await asyncio.to_thread(_execute)
