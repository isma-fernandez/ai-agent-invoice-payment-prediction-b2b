from pydantic import BaseModel, EmailStr, field_validator
from datetime import date
from typing import List, Tuple, Any
from datetime import datetime

# TODO: None temporales para evitar errores
# TODO: Añadir gestión de excepciones en validaciones, en vez de excepción, asignar valor por defecto

# account.move
class Invoice(BaseModel):
    id: int
    name: str | None  # Nombre de la factura
    move_type: str | None  # Tipo de movimiento (out_invoice, in_invoice, etc.)
    payment_state: str | None  # Estado del pago (paid, not_paid, partial)
    company_id: Tuple[int, str] | None  # Empresa relacionada [id, nombre]
    partner_id: Tuple[int, str] | None  # Cliente o proveedor [id, nombre]
    currency_id: Tuple[int, str] | None  # Moneda utilizada [id, nombre]
    amount_total: float | None  # Monto total
    amount_residual: float | None  # Monto pendiente
    invoice_date: date | None = None  # Fecha de la factura 
    invoice_date_due: date | None  # Fecha de vencimiento
    journal_id: Tuple[int, str] | None  # Diario asociado [id, nombre]
    payment_dates: date | None |str # Fechas de pago asociadas a la factura

    # Campos adicionales fuera del modelo Odoo
    paid_late: bool | None = None # Indica si se pagó tarde
    days_overdue: int | None = -1  # Días de retraso en el pago

    @field_validator("payment_dates", mode="before")
    def empty_str_to_none(cls, v):
        """
        Convierte cadenas vacías o valores falsos en None.
        Además convierte fechas con formato DD/MM/YYYY a date.
        TODO: ya me dirás tú por qué tienen dos formatos de fecha distintos en Odoo (magic)
        """
        if not v or v is False or v == "":
            return None
        elif isinstance(v, date):
            return v
        elif isinstance(v, str):
            try:
                if "/" in v:
                    return datetime.strptime(v, "%d/%m/%Y").date()
            except ValueError:
                return None
        return v
    
    @field_validator("invoice_date", mode="before")
    def parse_invoice_date(cls, v):
        """
        Convierte cadenas vacías o valores falsos en None.
        Además convierte fechas con formato DD/MM/YYYY a date.
        """
        if not v or v is False or v == "":
            return None
        elif isinstance(v, date):
            return v
        elif isinstance(v, str):
            try:
                if "/" in v:
                    return datetime.strptime(v, "%d/%m/%Y").date()
            except ValueError:
                return None
        return v
    
    @field_validator("invoice_date_due", mode="before")
    def parse_invoice_date_due(cls, v):
        """
        Convierte cadenas vacías o valores falsos en None.
        Además convierte fechas con formato DD/MM/YYYY a date.
        """
        if not v or v is False or v == "":
            return None
        elif isinstance(v, date):
            return v
        elif isinstance(v, str):
            try:
                if "/" in v:
                    return datetime.strptime(v, "%d/%m/%Y").date()
            except ValueError:
                return None
        return v
    
    @field_validator("partner_id", mode="before")
    def validate_partner_id(cls, v):
        """
        Asegura que partner_id es una tupla (id, nombre).
        Si no se asigna un partner_id, Odoo devuelve False (qué sentido tiene eso?).
        """
        if not v or v is False:
            return None
        elif isinstance(v, list) and len(v) == 2:
            return (v[0], v[1])
        # No suele pasar, pero por si acaso
        elif isinstance(v, tuple) and len(v) == 2:
            return v
        return None

    def model_post_init(self, context):
        if self.payment_state == 'paid' and self.payment_dates and self.invoice_date_due:
            days_late = (self.payment_dates - self.invoice_date_due).days
            self.days_overdue = max(0, days_late)
            self.paid_late = days_late > 0


    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

# res.partner
class Partner(BaseModel):
    id: int
    name: str | None  # Nombre del cliente o proveedor
    email: EmailStr | None  # Correo electrónico
    phone: str | None  # Teléfono
    street: str | None  # Calle
    city: str | None  # Ciudad
    zip: str | None  # Código postal
    country_id: Tuple[int, str] | None  # País [id, nombre]
    vat: str | None  # Número de identificación fiscal
    customer_rank: int | None  # Rango de cliente (>0 si es cliente)
    supplier_rank: int | None  # Rango de proveedor (>0 si es proveedor)
    category_id: List[Tuple[int, str]] | None  # Categorías asociadas
    credit: float | None  # Dinero que debe
    credit_limit: float | None   # Límite de crédito
    invoice_ids: List[int] | None  # IDs de facturas asociadas
    total_invoiced: float | None  # Monto total facturado
    unpaid_invoices_count: int | None  # Número de facturas impagas
    unpaid_invoice_ids: List[int] | None  # IDs de facturas impagadas

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

# res.partner.category
class PartnerCategory(BaseModel):
    id: int
    name: str  # Nombre de la categoría

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()
    
# res.company
class Company(BaseModel):
    id: int
    name: str  # Nombre de la empresa
    currency_id: Tuple[int, str]  # Moneda de la empresa [id, nombre]

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

# res.currency
class Currency(BaseModel):
    id: int
    name: str  # Nombre de la moneda
    symbol: str  # Símbolo
    rate: float  # Tasa de cambio

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()