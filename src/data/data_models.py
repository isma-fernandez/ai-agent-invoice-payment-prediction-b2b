from pydantic import BaseModel, EmailStr
from datetime import date

# account.move
class Invoice(BaseModel):
    id: int
    name: str # Nombre de la factura
    move_type: str # Tipo de movimiento de la factura (out_invoice, in_invoice, out_refund, in_refund)
    payment_state: str # Estado del pago de la factura (paid, not_paid, partial)
    company_id: list # Empresa relacionada con la factura [id, nombre]
    partner_id: list # Cliente o proveedor relacionado con la factura [id, nombre]
    currency_id: list # Moneda utilizada en la factura [id, nombre]
    amount_total: float # Monto total de la factura
    amount_residual: float # Monto pendiente de pago
    invoice_date: date # Fecha de la factura
    invoice_date_due: date # Fecha de vencimiento de la factura
    journal_id: list # Diario asociado a la factura [id, nombre]
    payment_dates: date # Fechas de pago asociadas a la factura

    # Campos adicionales fuera del modelo Odoo
    paid_late: bool # Indica si la factura se pagó tarde
    days_overdue: int # Días de retraso en el pago de la factura
    
# res.partner
class Partner(BaseModel):
    id: int
    name: str # Nombre del cliente o proveedor
    email: EmailStr # Correo electrónico del cliente o proveedor
    phone: str # Teléfono del cliente o proveedor
    street: str # Calle del cliente o proveedor
    city: str # Ciudad del cliente o proveedor
    zip: str # Código postal del cliente o proveedor
    country_id: list # País del cliente o proveedor [id, nombre]
    vat: str # Número de identificación fiscal del cliente o proveedor
    customer_rank: int # Rango de cliente (>0 si es cliente)
    supplier_rank: int # Rango de proveedor (>0 si es proveedor)
    category_id: list # Categorías asociadas al cliente o proveedor
    credit: float # Dinero que debe
    credit_limit: float # Límite de crédito establecido
    invoice_ids: list # Lista de IDs de facturas asociadas al cliente o proveedor
    total_invoiced: float # Monto total facturado al cliente o proveedor
    unpaid_invoices_count: int # Número de facturas impagas asociadas al cliente o proveedor
    unpaid_invoice_ids: list # Lista de IDs de facturas impagadas

# res.partner.category
class PartnerCategory(BaseModel):
    id: int
    name: str # Nombre de la categoría

# res.company
class Company(BaseModel):
    id: int
    name: str # Nombre de la empresa
    currency_id: list # Moneda de la empresa [id, nombre]

# res.currency
class Currency(BaseModel):
    id: int
    name: str # Nombre de la moneda
    symbol: str # Símbolo de la moneda
    rate: float # Tasa de cambio de la moneda