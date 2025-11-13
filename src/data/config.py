"""
Campos a extraer de los modelos de Odoo.
"""
COMPANY_FIELDS = ['id', 'name', 'currency_id']

PARTNER_FIELDS = [
    'id', 'name', 'email', 'phone', 'street', 'city', 'zip',
    'country_id', 'customer_rank', 'supplier_rank', 'category_id',
    'is_company', 'company_type', 'company_id', 'credit',
    'credit_limit',  'industry_id', 'vat',
    'invoice_ids', 'total_due', 'total_invoiced', 'total_overdue',
    'trust', 'unpaid_invoice_ids', 'unpaid_invoices_count', 'company_type', 
    
]

INVOICE_FIELDS = [
    'id', 'name', 'move_type', 'payment_state', 'company_id',
    'partner_id', 'currency_id', 'amount_total', 'amount_paid',
    'amount_residual', 'invoice_date', 'invoice_date_due',
    'payment_dates', 'date', 'create_date', 'payment_id', 'payment_ids'
]

CURRENCY_FIELDS = ['id', 'name', 'symbol', 'rate']

COUNTRY_FIELDS = ['id', 'name', 'code']

PARTNER_CATEGORY_FIELDS = ['id', 'name']

PARTNER_INDUSTRY_FIELDS = ['id', 'name']

"""
Tamaño del batch para recuperar los datos (evitar timeouts).
"""
BATCH_SIZE = 500