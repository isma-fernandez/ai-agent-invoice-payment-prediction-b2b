from langchain_core.tools import tool
from src.data.manager import DataManager
from src.data.models import *

data_manager = DataManager()

@tool(args_schema=SearchClientInput)
def search_client(name: str, limit: int) -> list[ClientSearchResult] | None:
    """Busca clientes por nombre para conseguir el ID."""
    return data_manager.search_clients(name=name, limit=limit)

@tool(args_schema=GetClientInfoInput)
def get_client_info(client_id: int) -> ClientInfo | None:
    """Recupera información y estadísticas de un cliente a partir de su ID.
    Incluyendo número de facturas, monto total facturado, nombre, país
    número de facturas pagadas e impagadas, monto total pendiente, 
    ratio de pago a tiempo y promedio de días de retraso.
    """
    return data_manager.get_client_info(client_id=client_id)

@tool(args_schema=GetClientInvoicesInfoInput)
def get_client_invoices(partner_id: int, limit: int, unpaid_only: bool) -> list[InvoiceSummary] | None:
    """Recupera un resumen de las facturas de un cliente a partir de su ID.
    Se puede especificar un límite de facturas a devolver y si se quieren
    solo las facturas pendientes de pago.
    Esto incluye ID de factura, nombre, monto en EUR, fecha de factura,
    fecha de vencimiento, estado de pago, fecha de pago (si aplica),
    si se pagó tarde (si aplica), días de retraso (si aplica) y días de vencimiento (si aplica).
    """
    return data_manager.get_client_invoices(partner_id=partner_id, limit=limit, unpaid_only=unpaid_only)

@tool(args_schema=GetInvoiceByName)
def get_invoice_by_name(invoice_name: str) -> InvoiceSummary | None:
    """Recupera una factura por su nombre."""
    return data_manager.get_invoice_by_name(invoice_name=invoice_name)

@tool(args_schema=PredictInvoiceInput)
def predict_invoice_risk(invoice_id: int) -> PredictionResult | None:
    """Predice el riesgo de impago de una factura existente a partir de su ID.
    Devuelve la categoría de riesgo y las probabilidades asociadas.
    """
    return data_manager.predict(invoice_id=invoice_id)

@tool(args_schema=PredictHypotheticalInput)
def predict_hypothetical_invoice(partner_id: int, amount_eur: float, due_date: date) -> PredictionResult | None:
    """Predice el riesgo de impago de una factura hipotética.
    Proporciona el ID del cliente, monto en EUR y fecha de vencimiento.
    Devuelve la categoría de riesgo y las probabilidades asociadas.
    """
    return data_manager.predict_hypothetical(
        partner_id=partner_id,
        amount_eur=amount_eur,
        due_date=due_date
    )

tools=[
    search_client, 
    get_client_info, 
    get_client_invoices, 
    get_invoice_by_name, 
    predict_invoice_risk, 
    predict_hypothetical_invoice
]