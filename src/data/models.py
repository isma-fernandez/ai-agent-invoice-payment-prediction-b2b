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
    risk_score: Optional[float] = None


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
    partner_id: Optional[int] = None
    partner_name: Optional[str] = None


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


class AgingBucket(BaseModel):
    """Bucket del aging report."""
    range_label: str  # "0-30", "31-60", "61-90", ">90"
    invoice_count: int
    total_amount_eur: float
    percentage: float


class AgingReport(BaseModel):
    """Informe de antigüedad de deuda."""
    total_overdue_eur: float
    total_overdue_count: int
    buckets: list[AgingBucket]
    generated_at: date


class PortfolioSummary(BaseModel):
    """Resumen de cartera."""
    total_outstanding_eur: float
    total_overdue_eur: float
    total_not_due_eur: float
    overdue_count: int
    not_due_count: int
    dso: float  # Days Sales Outstanding
    average_delay_days: float
    generated_at: date


class ClientTrend(BaseModel):
    """Tendencia de comportamiento de un cliente."""
    partner_id: int
    partner_name: str
    recent_invoices: int
    recent_on_time_ratio: float
    recent_avg_delay: float
    previous_invoices: int
    previous_on_time_ratio: float
    previous_avg_delay: float
    trend: str
    change_on_time_ratio: float
    change_avg_delay: float


class DeterioratingClient(BaseModel):
    """Cliente con comportamiento de pago deteriorándose."""
    partner_id: int
    partner_name: str
    previous_on_time_ratio: float
    recent_on_time_ratio: float
    change_on_time_ratio: float
    previous_avg_delay: float
    recent_avg_delay: float
    change_avg_delay: float
    current_overdue_count: int
    current_overdue_eur: float


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


class ChartType(str, Enum):
    BAR = "bar"
    HORIZONTAL_BAR = "horizontal_bar"
    LINE = "line"
    PIE = "pie"
    DONUT = "donut"


class PredictHypotheticalInput(BaseModel):
    """Input para predecir riesgo de una factura hipotética."""
    partner_id: int = Field(description="ID del cliente")
    amount_eur: float = Field(description="Importe de la factura en EUR", gt=0)
    payment_term_days: int = Field(default=30, description="Días de plazo de pago")


class GetOverdueInvoicesInput(BaseModel):
    """Input para obtener facturas vencidas."""
    limit: int = Field(default=10, description="Máximo de facturas a devolver")
    min_days_overdue: int = Field(default=1, description="Mínimo de días de vencimiento")


class CompareClientsInput(BaseModel):
    """Input para comparar clientes."""
    partner_ids: list[int] = Field(description="Lista de IDs de clientes a comparar (mínimo 2)")


class GetUpcomingDueInvoicesInput(BaseModel):
    """Input para facturas próximas a vencer."""
    days_ahead: int = Field(default=7, description="Días hacia adelante para buscar vencimientos")
    limit: int = Field(default=20, description="Máximo de facturas a devolver")


class GetClientTrendInput(BaseModel):
    """Input para tendencia de un cliente."""
    partner_id: int = Field(description="ID del cliente")
    recent_months: int = Field(default=6, description="Meses a considerar como período reciente")


class GetInvoicesByPeriodInput(BaseModel):
    """Input para facturas por período."""
    start_date: str = Field(description="Fecha inicio (YYYY-MM-DD)")
    end_date: str = Field(description="Fecha fin (YYYY-MM-DD)")
    partner_id: Optional[int] = Field(default=None, description="ID del cliente (opcional, si no se especifica busca todos)")
    only_unpaid: bool = Field(default=False, description="Solo facturas pendientes")


class GetDeterioratingClientsInput(BaseModel):
    """Input para clientes que empeoran."""
    limit: int = Field(default=10, description="Máximo de clientes a devolver")
    min_invoices: int = Field(default=5, description="Mínimo de facturas históricas para considerar")


class GenerateChartInput(BaseModel):
    """Input para generar un gráfico."""
    chart_type: ChartType = Field(description="Tipo de gráfico")
    title: str = Field(description="Título del gráfico")
    data: dict = Field(description="Datos para el gráfico: {labels: [...], values: [...], series_name: str}")
    show_values: bool = Field(default=True, description="Mostrar valores en el gráfico")