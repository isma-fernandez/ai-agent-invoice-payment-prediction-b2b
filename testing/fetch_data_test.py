from config import URL, USERNAME, DB, PASSWORD
import asyncio
from mcp_odoo.odoo.client import OdooClient

INVOICE_FIELDS = ['id', 'name', 'move_type', 'state', 'invoice_date', 'invoice_date_due', 
                    'amount_total', 'amount_residual', 'currency_id', 'partner_id', 
                    'commercial_partner_id', 'invoice_payment_term_id', 'payment_state', 
                    'journal_id', 'company_id', 'invoice_user_id', 'user_id', 'country_code', 
                    'payment_mode_id', 'preferred_payment_method_id', 'invoice_origin', 
                    'fiscal_position_id', 'partner_bank_id']

async def get_companies(client, fields=None):
    companies = await client.search_read(
        'res.company',
        [('active', '=', True)],
        fields or ['id', 'name', 'currency_id'],
        0
    )
    return companies

async def get_invoices(client, company_id, fields=None):
    invoices = await client.search_read(
        'account.move',
        [('company_id', '=', company_id),
         ('move_type', 'in', ['out_invoice', 'out_refund'])],
        fields or ['id', 'name', 'amount_total', 'invoice_date'],
        0
    )
    return invoices


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
    
    # Obtener compañías
    companies = await get_companies(client)
    for company in companies:
        print(f"Compañía: {company['name']} (ID: {company['id']})")
        invoices = await get_invoices(client, company_id=company['id'], fields=['id'])
        print(f"Facturas encontradas: {len(invoices)}")
    



    # Desconectar
    await client.disconnect()
 
asyncio.run(main())