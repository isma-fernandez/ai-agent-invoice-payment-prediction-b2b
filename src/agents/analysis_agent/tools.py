from langchain_core.tools import tool
from src.data.models import (
    PredictInvoiceInput, PredictHypotheticalInput, CompareClientsInput,
    GetClientTrendInput, GetDeterioratingClientsInput, PredictionResult,
    ClientInfo, AgingReport, PortfolioSummary, ClientTrend, DeterioratingClient,
    GenerateChartInput, ChartType, GetAgingReportInput
)
from src.agents.shared import get_data_manager
from src.utils.chart_generator import chart_generator


@tool(args_schema=PredictInvoiceInput)
async def predict_invoice_risk(invoice_id: int) -> PredictionResult | None:
    """Predice el riesgo de impago de una factura existente a partir de su ID.
    Devuelve la categoría de riesgo y las probabilidades asociadas.

    Args:
        invoice_id (int): ID de la factura en el sistema.

    Returns:
        PredictionResult | None: Resultado de la predicción de riesgo.
    """
    dm = get_data_manager()
    return await dm.predict(invoice_id=invoice_id)


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
    dm = get_data_manager()
    return await dm.predict_hypothetical(
        partner_id=partner_id,
        amount_eur=amount_eur,
        payment_term_days=payment_term_days
    )

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
    dm = get_data_manager()
    return await dm.get_high_risk_clients(limit=limit)


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
    dm = get_data_manager()
    return await dm.compare_clients(partner_ids=partner_ids)


@tool(args_schema=GetAgingReportInput)
async def get_aging_report(partner_id: int = None) -> AgingReport:
    """Genera un informe de antigüedad de deuda (aging report).
    Distribuye las facturas vencidas en buckets: 0-30, 31-60, 61-90, >90 días.

    Args:
        partner_id: ID del cliente (opcional). Si se proporciona, genera el aging
                   solo para ese cliente. Si no, genera el aging de toda la cartera.

    Returns:
        AgingReport: Informe con total_overdue_eur, total_overdue_count y buckets.
    """
    dm = get_data_manager()
    return await dm.get_aging_report(partner_id=partner_id)


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
    dm = get_data_manager()
    return await dm.get_portfolio_summary()


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
    dm = get_data_manager()
    return await dm.get_client_trend(partner_id=partner_id, recent_months=recent_months)


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
    dm = get_data_manager()
    return await dm.get_deteriorating_clients(limit=limit, min_invoices=min_invoices)


@tool(args_schema=GenerateChartInput)
async def generate_chart(chart_type: ChartType, title: str, data: dict, show_values: bool = True) -> str:
    """Genera un gráfico visual para mostrar datos de forma más clara.

    CUÁNDO USAR GRÁFICOS:
    - Aging report: gráfico de barras o donut para mostrar distribución de deuda
    - Portfolio summary: donut para vencido vs no vencido
    - Comparación de clientes: barras horizontales comparando risk_score o métricas
    - Clientes de alto riesgo: barras horizontales con risk_score
    - Tendencias: líneas mostrando evolución temporal
    - Distribución de probabilidades en predicciones: donut o barras

    TIPOS DE GRÁFICO:
    - bar: Barras verticales (comparaciones, distribuciones)
    - horizontal_bar: Barras horizontales (rankings, comparaciones de nombres largos)
    - line: Líneas (tendencias temporales, evolución)
    - pie: Circular (distribución porcentual, partes de un todo)
    - donut: Circular con hueco (similar a pie, más moderno)

    FORMATO DE DATA:
    - Para bar/horizontal_bar/line/pie/donut simples:
      {"labels": ["A", "B", "C"], "values": [10, 20, 30]}
    - Para gráficos con múltiples series (bar/line):
      {"labels": ["Q1", "Q2"], "series": [{"name": "2024", "values": [10, 20]}, {"name": "2025", "values": [15, 25]}]}

    Args:
        chart_type (ChartType): Tipo de gráfico (bar, horizontal_bar, line, pie, donut).
        title (str): Título descriptivo del gráfico.
        data (dict): Datos del gráfico con labels y values (o series para múltiples).
        show_values (bool): Mostrar valores numéricos en el gráfico.

    Returns:
        str: Marcador del gráfico en formato "CHART:id" para renderizar en la UI.
    """
    chart_id = await chart_generator.create_chart(
        chart_type=chart_type,
        title=title,
        data=data,
        show_values=show_values
    )
    return f"CHART:{chart_id}"

ANALYSIS_TOOLS = [
    predict_invoice_risk,
    predict_hypothetical_invoice,
    get_high_risk_clients,
    compare_clients,
    get_aging_report,
    get_portfolio_summary,
    get_client_trend,
    get_deteriorating_clients,
    generate_chart
]