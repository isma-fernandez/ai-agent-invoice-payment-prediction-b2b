"""
Campos a extraer de los modelos de Odoo.
"""


PARTNER_FIELDS = [
    'id', 'name', 'company_type',
    'country_id',  
]

INVOICE_FIELDS = [
    'id', 'name', 'move_type', 'payment_state',     
    'company_id', 'partner_id', 'currency_id',    
    'amount_total', 'amount_residual','invoice_date',    
    'invoice_date_due',  'payment_dates',     
]

"""
Tamaño del batch para recuperar los datos (evitar timeouts).
"""
BATCH_SIZE = 500
