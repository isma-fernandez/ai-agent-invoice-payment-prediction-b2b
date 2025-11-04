from .data_models import Company, Currency, Partner, Invoice, PartnerCategory
from .odoo_connector import OdooConnection


class DataRetriever:
    def __init__(self, odoo_connection: OdooConnection):
        self.odoo_connection = odoo_connection
    
    async def get_all_outbound_invoices(self, company_id: int):
        """
        Recupera todas las facturas de salida para una empresa dada.
        """
        if self.odoo_connection.client is None:
            raise Exception("Odoo client is not connected.")
        domain = [('company_id', '=', company_id),
                  ('move_type', '=', 'out_invoice')]
        fields = ['id', 'name', 'move_type', 'payment_state', 'company_id',
            'partner_id', 'currency_id', 'amount_total', 'amount_residual',
            'invoice_date', 'invoice_date_due', 'journal_id', 'payment_dates']
        records = await self.odoo_connection.search_read('account.move', domain, fields)
        return [Invoice.model_validate(record) for record in records]
        
    