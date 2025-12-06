from .odoo_connector import OdooConnection
from .config import INVOICE_FIELDS, PARTNER_FIELDS, BATCH_SIZE

class DataRetriever:
    def __init__(self, odoo_connection: OdooConnection):
        self.odoo_connection = odoo_connection
    
    """  MÉTODOS PARA RECUPERAR TODOS LOS REGISTROS DE UN MODELO """
    async def get_all_outbound_invoices(self):
        """
        Recupera todas las facturas de salida (outbound) de todas las empresas.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        all_records = []
        offset = 0
        while True:
            records = await self.odoo_connection.search_read('account.move', [('move_type', '=', 'out_invoice')], INVOICE_FIELDS, BATCH_SIZE, offset)
            if not records:
                break
            all_records.extend(records)
            if (offset // BATCH_SIZE) % 5 == 0:
                print(f"Recuperadas {len(records)} facturas, total: {len(all_records)}")
            offset += BATCH_SIZE
        return all_records

    async def search_client_by_name(self, name: str, limit: int = 5):
        """
        Busca clientes por nombre.

        Args:
            name (str): Nombre o parte del nombre del cliente a buscar.
            limit (int): Máximo número de resultados a devolver.
        Returns:
            list: Lista de registros de clientes que coinciden con el nombre dado.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        
        domain = [('name', 'ilike', name), ('customer_rank', '>', '0')]
        records = await self.odoo_connection.search_read(
            model='res.partner', 
            domain=domain, 
            fields=PARTNER_FIELDS, 
            limit=limit
        )
        return records

    async def get_all_outbound_invoices_by_company(self, company_id: int):
        """
        Recupera todas las facturas de salida para una empresa dada.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        domain = [('company_id', '=', company_id),
                  ('move_type', '=', 'out_invoice')]
        all_records = []
        offset = 0
        while True:
            records = await self.odoo_connection.search_read('account.move', domain, INVOICE_FIELDS, BATCH_SIZE, offset)
            if not records:
                break
            all_records.extend(records)
            if (offset // BATCH_SIZE) % 5 == 0:
                print(f"Recuperadas {len(records)} facturas, total: {len(all_records)}")
            offset += BATCH_SIZE
        return all_records

    async def get_all_customer_partners(self):
        """
        Recupera todos los partners (clientes/proveedores).
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        all_records = []
        offset = 0
        while True:
            records = await self.odoo_connection.search_read('res.partner', [('customer_rank', '>', '0')], PARTNER_FIELDS, BATCH_SIZE, offset)
            if not records:
                break
            all_records.extend(records)
            if (offset // BATCH_SIZE) % 5 == 0:
                print(f"Recuperadas {len(records)} facturas, total: {len(all_records)}")
            offset += BATCH_SIZE
        return all_records
    

    """ MÉTODOS PARA RECUPERAR REGISTROS ESPECÍFICOS POR ID """

    async def get_invoice_by_id(self, invoice_id: int):
        """
        Recupera una factura por su ID.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        domain = [('id', '=', invoice_id)]
        invoice = await self.odoo_connection.search_read('account.move', domain, INVOICE_FIELDS)
        if invoice:
            return invoice[0]
        return None

    async def get_partner_by_id(self, partner_id: int):
        """
        Recupera un partner por su ID.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        domain = [('id', '=', partner_id)]
        partner = await self.odoo_connection.search_read('res.partner', domain, PARTNER_FIELDS)
        if partner:
            return partner[0]
        return None
    
    
    """ MÉTODOS ADICIONALES SEGÚN NECESIDAD """

    async def get_invoices_by_partner(self, partner_id: int):
        """
        Recupera todas las facturas asociadas a un partner (cliente/proveedor).
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        domain = [('partner_id', '=', partner_id)]
        records = await self.odoo_connection.search_read('account.move', domain, INVOICE_FIELDS, 0)
        return records
    
    async def get_invoices_by_date(self, start_date: str, end_date: str, company_id: int):
        """
        Recupera todas las facturas de una empresa dentro de un rango de fechas.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        domain = [('invoice_date', '>=', start_date), ('invoice_date', '<=', end_date),
                  ('company_id', '=', company_id)]
        records = await self.odoo_connection.search_read('account.move', domain, INVOICE_FIELDS, 0)
        return records