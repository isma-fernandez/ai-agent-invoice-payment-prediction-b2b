from .odoo_connector import OdooConnection
from .config import INVOICE_FIELDS, PARTNER_FIELDS, BATCH_SIZE

#TODO: clase demasiado grande, dividir en varios ficheros?
#TODO: modificada para devolver diccionarios en lugar de modelos Pydantic, simplifica el preprocesado

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

    async def get_all_lines_of_all_outbound_invoices(self):
        """
        Recupera todas las líneas de todas las facturas de salida (outbound).
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        all_records = []
        offset = 0
        while True:
            records = await self.odoo_connection.search_read('account.move.line', [('move_id.move_type', '=', 'out_invoice')], 
                                                             ['id', 'move_id', 'product_id', 'quantity', 
             'price_unit', 'tax_ids', 'reconciled', 'blocked', 
             'date_maturity', 'debit', 'credit', 'balance',
             'amount_residual', 'currency_id', 'company_id',
             'discount', 'discount_percentage', 'full_reconcile_id',
             'is_downpayment', 'reconcile_model_id'], BATCH_SIZE, offset)
            if not records:
                break
            all_records.extend(records)
            if (offset // BATCH_SIZE) % 5 == 0:
                print(f"Recuperadas {len(records)} facturas, total: {len(all_records)}")
            offset += BATCH_SIZE
        return all_records

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
    
    async def get_all_companies(self):
        """
        Recupera todas las empresas.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        records = await self.odoo_connection.search_read('res.company', [], ['id', 'name', 'currency_id'], 0)

        return records
        
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

    async def get_all_currencies(self):
        """
        Recupera todas las monedas.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        records = await self.odoo_connection.search_read('res.currency', [], ['id', 'name'], 0)
        return records
    
    async def get_all_partner_categories(self):
        """
        Recupera todas las categorías de partners.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        records = await self.odoo_connection.search_read('res.partner.category', [], ['id', 'name'], 0)
        return records

    async def get_all_industries(self):
        """
        Recupera todas las industrias.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        records = await self.odoo_connection.search_read('res.partner.industry', [], ['id', 'name'], 0)
        return records
    

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

    async def get_invoice_line_by_invoice_id(self, invoice_id: int):
        """
        Recupera las líneas de una factura por su ID.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        domain = [('move_id', '=', invoice_id)]
        invoice_lines = await self.odoo_connection.search_read(
            'account.move.line', domain, 
            ['id', 'move_id', 'product_id', 'quantity', 
             'price_unit', 'tax_ids', 'reconciled', 'blocked', 
             'date_maturity', 'debit', 'credit', 'balance',
             'amount_residual', 'currency_id', 'company_id',
             'discount', 'discount_percentage', 'full_reconcile_id',
             'is_downpayment', 'reconcile_model_id'])
        return invoice_lines


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
    
    async def get_company_by_id(self, company_id: int):
        """
        Recupera una empresa por su ID.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        domain = [('id', '=', company_id)]
        company = await self.odoo_connection.search_read('res.company', domain, ['id', 'name', 'currency_id'])

    async def get_currency_by_id(self, currency_id: int):
        """
        Recupera una moneda por su ID.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        domain = [('id', '=', currency_id)]
        currency = await self.odoo_connection.search_read('res.currency', domain, ['id', 'name'])
        if currency:
            return currency[0]
        return None
    
    async def get_partner_category_by_id(self, category_id: int):
        """
        Recupera una categoría de partner por su ID.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        domain = [('id', '=', category_id)]
        category = await self.odoo_connection.search_read('res.partner.category', domain, ['id', 'name'])
        if category:
            return category[0]
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
    
    async def get_partners_by_company(self, company_id: int):
        """
        Recupera todos los partners asociados a una empresa.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        domain = [('company_id', '=', company_id)]
        records = await self.odoo_connection.search_read('res.partner', domain, PARTNER_FIELDS, 0)
        return records
    
    async def get_partners_by_category(self, category_id: int):
        """
        Recupera todos los partners asociados a una categoría específica.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        domain = [('category_id', 'in', [category_id])]
        records = await self.odoo_connection.search_read('res.partner', domain, PARTNER_FIELDS, 0)
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