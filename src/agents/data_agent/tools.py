from langchain_core.tools import tool
from src.data.models import (
    SearchClientInput, GetClientInfoInput, GetClientInvoicesInfoInput,
    GetInvoiceByName, GetOverdueInvoicesInput, GetUpcomingDueInvoicesInput,
    GetInvoicesByPeriodInput, ClientSearchResult, ClientInfo, InvoiceSummary,
)
from src.agents.shared import get_data_manager


# Mensajes para chat.py
TOOL_MESSAGES = {
    "predict_invoice_risk": "Analizando riesgo de la factura...",
    "predict_hypothetical_invoice": "Calculando predicción hipotética...",
    "get_high_risk_clients": "Identificando clientes de alto riesgo...",
    "compare_clients": "Comparando clientes...",
    "get_aging_report": "Generando informe de antigüedad...",
    "get_portfolio_summary": "Generando resumen de cartera...",
    "get_client_trend": "Analizando tendencia del cliente...",
    "get_deteriorating_clients": "Identificando clientes en deterioro...",
}

@tool
async def check_connection() -> bool:
    """Verifica si el DataManager está conectado."""
    try:
        dm = get_data_manager()
        return await dm.odoo_connection.is_connected()
    except Exception:
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
    dm = get_data_manager()
    return await dm.search_clients(name=name, limit=limit)


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
    dm = get_data_manager()
    return await dm.get_client_info(partner_id=partner_id)


@tool(args_schema=GetClientInvoicesInfoInput)
async def get_client_invoices(partner_id: int, limit: int = 5, only_unpaid: bool = False, paid_only: bool = False) -> \
list[InvoiceSummary] | None:
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
    dm = get_data_manager()
    return await dm.get_client_invoices(partner_id=partner_id, limit=limit, only_unpaid=only_unpaid,
                                                  paid_only=paid_only)


@tool(args_schema=GetInvoiceByName)
async def get_invoice_by_name(invoice_name: str) -> InvoiceSummary | None:
    """Recupera una factura por su nombre.

    Args:
        invoice_name (str): Nombre de la factura a buscar.

    Returns:
        InvoiceSummary | None: Resumen de la factura."""
    dm = get_data_manager()
    return await dm.get_invoice_by_name(invoice_name=invoice_name)


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
    dm = get_data_manager()
    return await dm.get_overdue_invoices(limit=limit, min_days_overdue=min_days_overdue)


@tool(args_schema=GetUpcomingDueInvoicesInput)
async def get_upcoming_due_invoices(days_ahead: int = 7, limit: int = 20) -> list[InvoiceSummary]:
    """Obtiene facturas pendientes que vencen en los próximos días.
    Útil para gestión preventiva de cobros (contactar clientes ANTES del vencimiento).
    Devuelve facturas ordenadas por fecha de vencimiento más próxima.
    El campo days_overdue será NEGATIVO indicando días hasta el vencimiento.
    Ej: days_overdue = -3 significa "vence en 3 días".

    Args:
        days_ahead (int): Días hacia adelante para buscar (ej: 7 = próxima semana).
        limit (int): Máximo de facturas a devolver.

    Returns:
        list[InvoiceSummary]: Lista de facturas próximas a vencer.
    """
    dm = get_data_manager()
    return await dm.get_upcoming_due_invoices(days_ahead=days_ahead, limit=limit)


@tool(args_schema=GetInvoicesByPeriodInput)
async def get_invoices_by_period(start_date: str, end_date: str,
                                 partner_id: int = None, only_unpaid: bool = False) -> list[InvoiceSummary]:
    """Obtiene facturas emitidas en un período específico.
    Puede filtrarse opcionalmente por cliente y/o solo pendientes.
    Útil para análisis temporal: "facturas del Q3", "facturas de enero",
    "qué le facturamos a X el año pasado".
    Las fechas deben estar en formato YYYY-MM-DD.

    Args:
        start_date (str): Fecha inicio en formato YYYY-MM-DD.
        end_date (str): Fecha fin en formato YYYY-MM-DD.
        partner_id (int, optional): ID del cliente para filtrar (None = todos).
        only_unpaid (bool): Si True, solo devuelve facturas pendientes de pago.

    Returns:
        list[InvoiceSummary]: Facturas del período ordenadas por fecha (recientes primero).
    """
    dm = get_data_manager()
    return await dm.get_invoices_by_period(
        start_date=start_date,
        end_date=end_date,
        partner_id=partner_id,
        only_unpaid=only_unpaid
    )

DATA_TOOLS = [
    check_connection,
    search_client,
    get_client_info,
    get_client_invoices,
    get_invoice_by_name,
    get_overdue_invoices,
    get_upcoming_due_invoices,
    get_invoices_by_period,
]
