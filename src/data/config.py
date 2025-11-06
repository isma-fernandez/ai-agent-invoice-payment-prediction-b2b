"""
Campos a extraer de los modelos de Odoo.
"""
COMPANY_FIELDS = ['id', 'name', 'currency_id']

PARTNER_FIELDS = ['id', 'name', 'email', 'phone', 'street', 'city',
                  'zip', 'country_id', 'vat', 'customer_rank',
                  'supplier_rank', 'category_id', 'credit',
                  'credit_limit', 'invoice_ids',
                  'total_invoiced', 'unpaid_invoices_count',
                  'unpaid_invoice_ids']

INVOICE_FIELDS = ['id', 'name', 'move_type', 'payment_state', 'company_id',
                  'partner_id', 'currency_id', 'amount_total', 'amount_residual',
                  'invoice_date', 'invoice_date_due', 'journal_id', 'payment_dates']

CURRENCY_FIELDS = ['id', 'name']

COUNTRY_FIELDS = ['id', 'name', 'code']

PARTNER_CATEGORY_FIELDS = ['id', 'name']

PARTNER_INDUSTRY_FIELDS = ['id', 'name']

"""
Tamaño del batch para recuperar los datos (evitar timeouts).
"""
BATCH_SIZE = 500