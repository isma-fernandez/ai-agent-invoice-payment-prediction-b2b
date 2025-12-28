from langchain_core.tools import tool
from src.data.manager import DataManager
from src.data.models import *
from src.agent.memory.store import MemoryStore
from src.agent.memory.models import Memory, MemoryType

data_manager: DataManager = None
memory_store: MemoryStore = None


async def initialize_data_manager(model_path: str = None):
    """Inicializa el DataManager. Llamar antes de usar las tools."""
    global data_manager, memory_store
    data_manager = DataManager(cutoff_date="2025-01-01")
    await data_manager.connect()
    #TODO: reactivar
    #if model_path:
        #data_manager.load_model(model_path)
    memory_store = MemoryStore()


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
    return await data_manager.get_upcoming_due_invoices(days_ahead=days_ahead, limit=limit)


@tool
async def get_aging_report() -> AgingReport:
    """Genera un informe de antigüedad de deuda (aging report).
    Distribuye las facturas vencidas en buckets: 0-30, 31-60, 61-90, >90 días.
    Incluye importe total, número de facturas y porcentaje por cada bucket.
    Informe estándar en gestión de cobros para entender la composición de la deuda.

    Returns:
        AgingReport: Informe con total_overdue_eur, total_overdue_count y buckets.
    """
    return await data_manager.get_aging_report()


@tool
async def get_portfolio_summary() -> PortfolioSummary:
    """Genera un resumen ejecutivo de la cartera de cobros.
    Incluye: total pendiente (vencido + no vencido), total vencido,
    DSO (Days Sales Outstanding), número de facturas por estado,
    y promedio de días de retraso histórico.
    Útil para tener una visión global del estado de cobros.

    Returns:
        PortfolioSummary: Resumen con métricas clave de cartera.
    """
    return await data_manager.get_portfolio_summary()


@tool(args_schema=GetClientTrendInput)
async def get_client_trend(partner_id: int, recent_months: int = 6) -> ClientTrend | None:
    """Analiza la tendencia de comportamiento de pago de un cliente.
    Compara el período reciente (últimos N meses) con el período anterior.
    Indica si el cliente está "mejorando", "empeorando" o "estable".
    Útil para detectar cambios en el comportamiento antes de que sea tarde.
    Requiere usar search_client primero para obtener el partner_id.

    Args:
        partner_id (int): ID del cliente a analizar.
        recent_months (int): Meses a considerar como período reciente.

    Returns:
        ClientTrend | None: Análisis con métricas de ambos períodos y tendencia.
    """
    return await data_manager.get_client_trend(partner_id=partner_id, recent_months=recent_months)


@tool(args_schema=GetDeterioratingClientsInput)
async def get_deteriorating_clients(limit: int = 10, min_invoices: int = 5) -> list[DeterioratingClient]:
    """Identifica clientes cuyo comportamiento de pago está EMPEORANDO.
    Compara métricas recientes vs históricas para detectar deterioro.
    Solo incluye clientes con historial suficiente (min_invoices).
    Ordenados por mayor deterioro primero (cambio más negativo en on_time_ratio).
    Útil para intervención proactiva con clientes problemáticos.

    Args:
        limit (int): Máximo de clientes a devolver.
        min_invoices (int): Mínimo de facturas históricas requeridas para análisis.

    Returns:
        list[DeterioratingClient]: Clientes en deterioro con métricas comparativas.
    """
    return await data_manager.get_deteriorating_clients(limit=limit, min_invoices=min_invoices)


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
    return await data_manager.get_invoices_by_period(
        start_date=start_date,
        end_date=end_date,
        partner_id=partner_id,
        only_unpaid=only_unpaid
    )

#
# ======================= MEMORY TOOLS ===============================
#
async def initialize_memory_store(db_path: str = "data/agent_memory.db"):
    """Inicializa el store de memoria."""
    global memory_store
    memory_store = MemoryStore(db_path)


@tool
async def save_client_note(partner_id: int, partner_name: str, note: str) -> str:
    """Guarda una nota permanente sobre un cliente.
    Usar cuando el usuario pida recordar algo sobre un cliente o cuando
    se detecte información importante (ej: "este cliente siempre paga tarde",
    "contactar solo por email", "riesgo de impago detectado").

    Args:
        partner_id (int): ID del cliente.
        partner_name (str): Nombre del cliente.
        note (str): Nota a guardar sobre el cliente.

    Returns:
        str: Confirmación de que se guardó la nota.
    """
    memory = Memory(
        memory_type=MemoryType.CLIENT_NOTE,
        content=note,
        partner_id=partner_id,
        partner_name=partner_name
    )
    memory_store.save(memory)
    return f"Nota guardada para {partner_name}: {note}"


@tool
async def get_client_notes(partner_id: int) -> list[Memory]:
    """Recupera las notas guardadas sobre un cliente.
    Usar al inicio de cualquier consulta sobre un cliente para tener contexto.

    Args:
        partner_id (int): ID del cliente.

    Returns:
        list[Memory]: Lista de notas sobre el cliente.
    """
    return memory_store.get_by_partner(partner_id)


@tool
async def save_alert(content: str, partner_id: int = None, partner_name: str = None) -> str:
    """Guarda una alerta importante.
    Usar para destacar situaciones que requieren atención: clientes en riesgo,
    facturas críticas, patrones preocupantes detectados.

    Args:
        content (str): Descripción de la alerta.
        partner_id (int, optional): ID del cliente si aplica.
        partner_name (str, optional): Nombre del cliente si aplica.

    Returns:
        str: Confirmación de la alerta guardada.
    """
    memory = Memory(
        memory_type=MemoryType.ALERT,
        content=content,
        partner_id=partner_id,
        partner_name=partner_name
    )
    memory_store.save(memory)
    return f"Alerta guardada: {content}"


@tool
async def get_active_alerts(limit: int = 10) -> list[Memory]:
    """Recupera las alertas activas.
    Útil para mostrar al usuario un resumen de situaciones pendientes.

    Args:
        limit (int): Máximo de alertas a devolver.

    Returns:
        list[Memory]: Lista de alertas activas.
    """
    return memory_store.get_by_type(MemoryType.ALERT, limit)


tools = [
    search_client,
    get_client_info,
    get_client_invoices,
    get_invoice_by_name,
    predict_invoice_risk,
    predict_hypothetical_invoice,
    check_connection,
    get_overdue_invoices,
    get_high_risk_clients,
    compare_clients,
    get_upcoming_due_invoices,
    get_aging_report,
    get_portfolio_summary,
    get_client_trend,
    get_deteriorating_clients,
    get_invoices_by_period,
    save_client_note,
    get_client_notes,
    save_alert,
    get_active_alerts,
]
