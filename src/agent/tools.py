from langchain_core.tools import tool
from src.data.manager import DataManager
from src.data.models import *

data_manager: DataManager = None


async def initialize_data_manager(model_path: str = None):
    """Inicializa el DataManager. Llamar antes de usar las tools."""
    global data_manager
    data_manager = DataManager(cutoff_date="2025-01-01")
    await data_manager.connect()
    #TODO: reactivar
    #if model_path:
        #data_manager.load_model(model_path)


@tool
async def check_connection() -> bool:
    """Verifica si el DataManager está conectado."""
    if data_manager is not None and await data_manager.odoo_connection.is_connected():
        print("Conexión exitosa al Odoo.")
        return True
    print("No hay conexión al Odoo.")
    return False


@tool(args_schema=SearchClientInput)
async def search_client(name: str, limit: int = 5) -> list[ClientSearchResult] | None:
    """Busca clientes por nombre para conseguir el ID.
    También necesita el limita de resultados a devolver.
    
    Args:
        name (str): Nombre o parte del nombre del cliente a buscar.
        limit (int): Máximo de resultados a devolver.
    
    Returns:
        list[ClientSearchResult] | None: Lista de resultados de búsqueda de clientes."""
    return await data_manager.search_clients(name=name, limit=limit)


@tool(args_schema=GetClientInfoInput)
async def get_client_info(partner_id: int) -> ClientInfo | None:
    """Recupera información y estadísticas de un cliente a partir de su ID.
    Incluyendo número de facturas, monto total facturado, nombre, país
    número de facturas pagadas e impagadas, monto total pendiente, 
    ratio de pago a tiempo, promedio de días de retraso y obtiene
    también el riesgo del cliente.

    Args:
        partner_id (int): ID del cliente en el sistema.

    Returns:
        ClientInfo | None: Información del cliente.
    """
    return await data_manager.get_client_info(partner_id=partner_id)


@tool(args_schema=GetClientInvoicesInfoInput)
async def get_client_invoices(partner_id: int, limit: int = 5, only_unpaid: bool = False, paid_only: bool = False) -> list[InvoiceSummary] | None:
    """Recupera un resumen de las facturas de un cliente a partir de su ID.
    Se puede especificar un límite de facturas a devolver y si se quieren
    solo las facturas pendientes de pago.
    Esto incluye ID de factura, nombre, monto en EUR, fecha de factura,
    fecha de vencimiento, estado de pago, fecha de pago,
    si se pagó tarde, días de retraso y días de vencimiento.

    Args:
        partner_id (int): ID del cliente en el sistema.
        limit (int): Máximo de facturas a devolver.
        only_unpaid (bool): Si es True, solo devuelve facturas pendientes de pago.
        paid_only (bool): Si es True, solo devuelve facturas pagadas.

    Returns:
        list[InvoiceSummary] | None: Lista de resúmenes de facturas.
    """
    return await data_manager.get_client_invoices(partner_id=partner_id, limit=limit, only_unpaid=only_unpaid, paid_only=paid_only)


@tool(args_schema=GetInvoiceByName)
async def get_invoice_by_name(invoice_name: str) -> InvoiceSummary | None:
    """Recupera una factura por su nombre.
    
    Args:
        invoice_name (str): Nombre de la factura a buscar.
        
    Returns:
        InvoiceSummary | None: Resumen de la factura."""
    return await data_manager.get_invoice_by_name(invoice_name=invoice_name)


@tool(args_schema=PredictInvoiceInput)
async def predict_invoice_risk(invoice_id: int) -> PredictionResult | None:
    """Predice el riesgo de impago de una factura existente a partir de su ID.
    Devuelve la categoría de riesgo y las probabilidades asociadas.

    Args:
        invoice_id (int): ID de la factura en el sistema.

    Returns:
        PredictionResult | None: Resultado de la predicción de riesgo.
    """
    return await data_manager.predict(invoice_id=invoice_id)


@tool(args_schema=PredictHypotheticalInput)
async def predict_hypothetical_invoice(partner_id: int, amount_eur: float, payment_term_days: int = 30) -> PredictionResult | None:
    """Predice el riesgo de impago de una factura hipotética.
    Proporciona el ID del cliente, monto en EUR y fecha de vencimiento.
    Devuelve la categoría de riesgo y las probabilidades asociadas.

    Args:
        partner_id (int): ID del cliente.
        amount_eur (float): Importe de la factura en EUR.
        payment_term_days (int): Días de plazo de pago desde la fecha actual.

    Returns:
        PredictionResult | None: Resultado de la predicción de riesgo.
    """
    return await data_manager.predict_hypothetical(
        partner_id=partner_id,
        amount_eur=amount_eur,
        payment_term_days=payment_term_days
    )

@tool(args_schema=GetOverdueInvoicesInput)
async def get_overdue_invoices(limit: int = 10, min_days_overdue: int = 1) -> list[InvoiceSummary]:
    """Obtiene las facturas vencidas de todos los clientes del sistema.
    Útil para identificar cobros urgentes. Busca en TODOS los clientes, no solo uno.
    Esto incluye ID de factura, nombre, monto en EUR, fecha de factura,
    fecha de vencimiento, días de vencimiento, ID y nombre del cliente.
    Ordenadas por días de vencimiento (más urgentes primero).

    Args:
        limit (int): Máximo de facturas a devolver.
        min_days_overdue (int): Mínimo de días vencidos para incluir.

    Returns:
        list[InvoiceSummary]: Lista de facturas vencidas con información del cliente.
    """
    return await data_manager.get_overdue_invoices(limit=limit, min_days_overdue=min_days_overdue)


@tool
async def get_high_risk_clients(limit: int = 10) -> list[ClientInfo]:
    """Obtiene los clientes con mayor riesgo de impago ordenados por puntuación.
    Calcula un risk_score (0-100) basado en ratio de puntualidad,
    promedio de retraso y facturas vencidas actuales.
    Esto incluye ID, nombre, estadísticas de facturación, ratio de pago
    a tiempo, promedio de días de retraso y puntuación de riesgo.

    Args:
        limit (int): Máximo de clientes a devolver.

    Returns:
        list[ClientInfo]: Clientes ordenados por riesgo (mayor primero).
    """
    return await data_manager.get_high_risk_clients(limit=limit)


@tool(args_schema=CompareClientsInput)
async def compare_clients(partner_ids: list[int]) -> list[ClientInfo]:
    """Compara estadísticas de pago entre varios clientes específicos.
    Útil para evaluar qué clientes pagan mejor. Usar search_client antes para obtener IDs.
    Esto incluye para cada cliente: estadísticas de facturación, ratio de pago
    a tiempo, promedio de días de retraso y risk_score (0-100).

    Args:
        partner_ids (list[int]): Lista de IDs de clientes a comparar (mínimo 2).

    Returns:
        list[ClientInfo]: Clientes ordenados de mejor a peor pagador.
    """
    return await data_manager.compare_clients(partner_ids=partner_ids)



tools=[
    search_client, 
    get_client_info, 
    get_client_invoices, 
    get_invoice_by_name, 
    predict_invoice_risk, 
    predict_hypothetical_invoice,
    check_connection,
    get_overdue_invoices,
    get_high_risk_clients,
    compare_clients
]