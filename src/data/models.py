# src/data/models.py
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, Dict
from enum import Enum


class RiskCategory(str, Enum):
    PUNTUAL = "Puntual"
    LEVE = "Leve"
    GRAVE = "Grave"


class PaymentState(str, Enum):
    PAID = "paid"
    NOT_PAID = "not_paid"


class ClientSearchResult(BaseModel):
    """Resultado de búsqueda de clientes."""
    id: int
    name: str


class ClientInfo(BaseModel):
    """Información y estadísticas del cliente."""
    id: int
    name: str
    country_name: Optional[str] = None
    total_invoices: int
    total_invoiced_eur: float
    paid_invoices: int
    unpaid_invoices: int
    overdue_invoices: int
    total_outstanding_eur: float
    on_time_ratio: float 
    avg_delay_days: float  


class InvoiceSummary(BaseModel):
    """Resumen de factura para el agente."""
    id: int
    name: str
    amount_eur: float
    invoice_date: date
    due_date: date
    payment_state: PaymentState
    payment_date: Optional[date] = None
    paid_late: Optional[bool] = None
    delay_days: Optional[int] = None 
    days_overdue: Optional[int] = None  


class PredictionResult(BaseModel):
    """Resultado de predicción de riesgo de impago."""
    partner_id: int
    partner_name: str
    is_hypothetical: bool = False
    invoice_id: Optional[int] = None  # None si hipotética
    invoice_name: Optional[str] = None
    amount_eur: float
    due_date: date
    prediction: RiskCategory
    probabilities: Dict[str, float] 


class SearchClientInput(BaseModel):
    """Input para buscar clientes por nombre."""
    name: str = Field(description="Nombre o parte del nombre del cliente a buscar")
    limit: int = Field(default=5, description="Máximo de resultados")


class GetClientInfoInput(BaseModel):
    """Input para obtener información de un cliente."""
    partner_id: int = Field(description="ID del cliente en el sistema")

class GetClientInvoicesInfoInput(BaseModel):
    """Input para obtener información de facturas de un cliente."""
    partner_id: int = Field(description="ID del cliente en el sistema")
    limit: int = Field(default=5, description="Máximo de facturas a devolver")
    only_unpaid: bool = Field(default=False, description="Solo facturas pendientes de pago")
    paid_only: bool = Field(default=False, description="Solo facturas pagadas")

class PredictInvoiceInput(BaseModel):
    """Input para predecir riesgo de una factura existente."""
    invoice_id: int = Field(description="ID de la factura")

class GetInvoiceByName(BaseModel):
    """Input para obtener una factura por su nombre."""
    invoice_name: str = Field(description="Nombre de la factura")

class PredictHypotheticalInput(BaseModel):
    """Input para predecir riesgo de una factura hipotética."""
    partner_id: int = Field(description="ID del cliente")
    amount_eur: float = Field(description="Importe de la factura en EUR", gt=0)
    payment_term_days: int = Field(default=30, description="Días de plazo de pago")