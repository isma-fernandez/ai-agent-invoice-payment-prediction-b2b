from .data_models import Company, Currency, Partner, Invoice, PartnerCategory
from .odoo_connector import OdooConnection

INVOICE_FIELDS = ['id', 'name', 'move_type', 'payment_state', 'company_id',
            'partner_id', 'currency_id', 'amount_total', 'amount_residual',
            'invoice_date', 'invoice_date_due', 'journal_id', 'payment_dates']
PARTNER_FIELDS = ['id', 'name', 'email', 'phone', 'street', 'city',
                'zip', 'country_id', 'vat', 'customer_rank',
                'supplier_rank', 'category_id', 'credit',
                'credit_limit', 'invoice_ids',
                'total_invoiced', 'unpaid_invoices_count',
            'unpaid_invoice_ids']

#TODO: clase demasiado grande, dividir en varios ficheros?

class DataRetriever:
    def __init__(self, odoo_connection: OdooConnection):
        self.odoo_connection = odoo_connection
    
    """  MÉTODOS PARA RECUPERAR TODOS LOS REGISTROS DE UN MODELO """

    # Por empresa y únicamente facturas a clientes (outbound)
    # TODO: en caso de ser necesario, generalizar
    async def get_all_outbound_invoices(self, company_id: int):
        """
        Recupera todas las facturas de salida para una empresa dada.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        domain = [('company_id', '=', company_id),
                  ('move_type', '=', 'out_invoice')]
        records = await self.odoo_connection.search_read('account.move', domain, INVOICE_FIELDS)
        return [Invoice.model_validate(record) for record in records]
    
    async def get_all_companies(self):
        """
        Recupera todas las empresas.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        records = await self.odoo_connection.search_read('res.company', [], ['id', 'name', 'currency_id'])
        return [Company.model_validate(record) for record in records]
        
    async def get_all_partners(self):
        """
        Recupera todos los partners (clientes/proveedores).
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        records = await self.odoo_connection.search_read('res.partner', [], PARTNER_FIELDS)
        return [Partner.model_validate(record) for record in records]

    async def get_all_currencies(self):
        """
        Recupera todas las monedas.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        records = await self.odoo_connection.search_read('res.currency', [], ['id', 'name'])
        return [Currency.model_validate(record) for record in records]
    
    async def get_all_partner_categories(self):
        """
        Recupera todas las categorías de partners.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        records = await self.odoo_connection.search_read('res.partner.category', [], ['id', 'name'])
        return [PartnerCategory.model_validate(record) for record in records]
    

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
            return Invoice.model_validate(invoice[0])
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
            return Partner.model_validate(partner[0])
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
            return Currency.model_validate(currency[0])
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
            return PartnerCategory.model_validate(category[0])
        return None
    
    """ MÉTODOS ADICIONALES SEGÚN NECESIDAD """

    async def get_invoices_by_partner(self, partner_id: int):
        """
        Recupera todas las facturas asociadas a un partner (cliente/proveedor).
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        domain = [('partner_id', '=', partner_id)]
        records = await self.odoo_connection.search_read('account.move', domain, INVOICE_FIELDS)
        return [Invoice.model_validate(record) for record in records]
    
    async def get_partners_by_company(self, company_id: int):
        """
        Recupera todos los partners asociados a una empresa.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        domain = [('company_id', '=', company_id)]
        records = await self.odoo_connection.search_read('res.partner', domain, PARTNER_FIELDS)
        return [Partner.model_validate(record) for record in records]
    
    async def get_partners_by_category(self, category_id: int):
        """
        Recupera todos los partners asociados a una categoría específica.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        domain = [('category_id', 'in', [category_id])]
        records = await self.odoo_connection.search_read('res.partner', domain, PARTNER_FIELDS)
        return [Partner.model_validate(record) for record in records]
    
    async def get_invoices_by_date(self, start_date: str, end_date: str, company_id: int):
        """
        Recupera todas las facturas de una empresa dentro de un rango de fechas.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        domain = [('invoice_date', '>=', start_date), ('invoice_date', '<=', end_date),
                  ('company_id', '=', company_id)]
        records = await self.odoo_connection.search_read('account.move', domain, INVOICE_FIELDS)
        return [Invoice.model_validate(record) for record in records]