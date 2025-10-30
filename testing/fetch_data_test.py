from config import URL, USERNAME, DB, PASSWORD
import asyncio
from mcp_odoo.odoo.client import OdooClient

async def main():
    # Crear cliente
    client = OdooClient(
        url=URL,
        database=DB,
        username=USERNAME,
        password=PASSWORD
    )

    # Conectar
    await client.connect()
    print(f"Conectado: {await client.get_server_version()}")
    
        # Buscar facturas de marzo 2025
    invoices = await client.search_read(
        'account.move',
        [],
        []
    )
    
    for inv in invoices:
        print(f"{inv['name']}: {inv['amount_total']}")
    # No tengo permisos :/
    """
    # Obtener modelos
    models = await client.search_read(
        'ir.model',
        [],  # sin filtro para que devuelva todos
        ['model', 'name', 'state']
    )
    for m in models:
        print(m['model'], m['name'], m['state'])
    """
    """
    # Buscar empresas
    companies = await client.search_read(
        'res.company',
        [('active', '=', True)],
        ['name', 'currency_id']
    )
    
    for company in companies:
        print(f"- {company['name']}")
    """
    # Desconectar
    await client.disconnect()

asyncio.run(main())