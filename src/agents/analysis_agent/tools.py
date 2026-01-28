import json
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
async def predict_invoice_risk(invoice_id: int) -> str:
    """Predice el riesgo de impago de una factura existente a partir de su ID.
    Devuelve la categoría de riesgo, probabilidades y un gráfico donut.

    Args:
        invoice_id (int): ID de la factura en el sistema.

    Returns:
        str: Resultado de la predicción con gráfico incluido.
    """
    dm = get_data_manager()
    result = await dm.predict(invoice_id=invoice_id)
    
    if result is None:
        return "No se encontró la factura o no se pudo realizar la predicción."
    
    probs = result.probabilities
    chart_id = await chart_generator.create_chart(
        chart_type="donut",
        title="Distribución de Probabilidades de Riesgo",
        data={
            "labels": ["Puntual", "Leve", "Grave"],
            "values": [
                probs.get("Puntual", 0) * 100,
                probs.get("Leve", 0) * 100,
                probs.get("Grave", 0) * 100
            ]
        },
        show_values=True
    )
    fig = chart_generator.get_chart(chart_id)
    chart_json = fig.to_json()
    chart_generator.clear_chart(chart_id)
    
    return f"{result.model_dump_json()} CHART_JSON:{chart_json}"


@tool(args_schema=PredictHypotheticalInput)
async def predict_hypothetical_invoice(partner_id: int, amount_eur: float, payment_term_days: int = 30) -> str:
    """Predice el riesgo de impago de una factura hipotética.
    Proporciona el ID del cliente, monto en EUR y días de plazo.
    Devuelve la categoría de riesgo, probabilidades y un gráfico donut.

    Args:
        partner_id (int): ID del cliente.
        amount_eur (float): Importe de la factura en EUR.
        payment_term_days (int): Días de plazo de pago desde la fecha actual.

    Returns:
        str: Resultado de la predicción con gráfico incluido.
    """
    dm = get_data_manager()
    result = await dm.predict_hypothetical(
        partner_id=partner_id,
        amount_eur=amount_eur,
        payment_term_days=payment_term_days
    )
    
    if result is None:
        return "No se pudo realizar la predicción hipotética."
    
    # Generar gráfico
    probs = result.probabilities
    chart_id = await chart_generator.create_chart(
        chart_type="donut",
        title="Probabilidades de Riesgo - Factura Hipotética",
        data={
            "labels": ["Puntual", "Leve", "Grave"],
            "values": [
                probs.get("Puntual", 0) * 100,
                probs.get("Leve", 0) * 100,
                probs.get("Grave", 0) * 100
            ]
        },
        show_values=True
    )
    fig = chart_generator.get_chart(chart_id)
    chart_json = fig.to_json()
    chart_generator.clear_chart(chart_id)
    
    return f"{result.model_dump_json()} CHART_JSON:{chart_json}"


@tool
async def get_high_risk_clients(limit: int = None) -> str:
    """Obtiene los clientes con mayor riesgo de impago ordenados por puntuación.
    Calcula un risk_score (0-100) basado en ratio de puntualidad,
    promedio de retraso y facturas vencidas actuales.
    Incluye gráfico de barras horizontales.

    Args:
        limit (int): Máximo de clientes a devolver.

    Returns:
        str: Clientes con datos y gráfico incluido.
    """
    dm = get_data_manager()
    if limit is None:
        clients = await dm.get_high_risk_clients()
    else:
        clients = await dm.get_high_risk_clients(limit=limit)
    
    if not clients:
        return "No se encontraron clientes de alto riesgo."
    
    chart_clients = clients[:10]
    labels = [c.partner_name[:25] for c in chart_clients]
    values = [c.risk_score for c in chart_clients]
    
    chart_id = await chart_generator.create_chart(
        chart_type="horizontal_bar",
        title="Top Clientes por Riesgo (Risk Score)",
        data={"labels": labels, "values": values},
        show_values=True
    )
    fig = chart_generator.get_chart(chart_id)
    chart_json = fig.to_json()
    chart_generator.clear_chart(chart_id)
    
    clients_data = [c.model_dump() for c in clients]
    return f"{json.dumps(clients_data)} CHART_JSON:{chart_json}"


@tool(args_schema=CompareClientsInput)
async def compare_clients(partner_ids: list[int]) -> str:
    """Compara estadísticas de pago entre varios clientes específicos.
    Útil para evaluar qué clientes pagan mejor.
    Incluye gráfico de barras horizontales comparando risk_score.

    Args:
        partner_ids (list[int]): Lista de IDs de clientes a comparar (mínimo 2).

    Returns:
        str: Clientes ordenados de mejor a peor pagador con gráfico.
    """
    dm = get_data_manager()
    clients = await dm.compare_clients(partner_ids=partner_ids)
    
    if not clients:
        return "No se encontraron los clientes especificados."
    
    labels = [c.partner_name[:25] for c in clients]
    values = [c.risk_score for c in clients]
    
    chart_id = await chart_generator.create_chart(
        chart_type="horizontal_bar",
        title="Comparativa de Clientes (Risk Score)",
        data={"labels": labels, "values": values},
        show_values=True
    )
    fig = chart_generator.get_chart(chart_id)
    chart_json = fig.to_json()
    chart_generator.clear_chart(chart_id)
    
    clients_data = [c.model_dump() for c in clients]
    return f"{json.dumps(clients_data)} CHART_JSON:{chart_json}"


@tool(args_schema=GetAgingReportInput)
async def get_aging_report(partner_id: int = None) -> str:
    """Genera un informe de antigüedad de deuda (aging report).
    Distribuye las facturas vencidas en buckets: 0-30, 31-60, 61-90, >90 días.
    Incluye gráfico de barras con la distribución.

    Args:
        partner_id: ID del cliente (opcional). Si se proporciona, genera el aging
                   solo para ese cliente. Si no, genera el aging de toda la cartera.

    Returns:
        str: Informe con datos y gráfico incluido.
    """
    dm = get_data_manager()
    report = await dm.get_aging_report(partner_id=partner_id)
    
    labels = []
    values = []
    for bucket in report.buckets:
        labels.append(bucket.range_label)
        values.append(bucket.total_amount_eur)
    
    title = "Aging Report - Distribución de Deuda"
    if partner_id:
        title = f"Aging Report - Cliente ID {partner_id}"
    
    chart_id = await chart_generator.create_chart(
        chart_type="bar",
        title=title,
        data={"labels": labels, "values": values},
        show_values=True
    )
    fig = chart_generator.get_chart(chart_id)
    chart_json = fig.to_json()
    chart_generator.clear_chart(chart_id)
    
    return f"{report.model_dump_json()} CHART_JSON:{chart_json}"


@tool
async def get_portfolio_summary() -> str:
    """Genera un resumen ejecutivo de la cartera de cobros.
    Incluye: total pendiente (vencido + no vencido), total vencido,
    DSO (Days Sales Outstanding), número de facturas por estado,
    y promedio de días de retraso histórico.
    Incluye gráfico donut con vencido vs no vencido.

    Returns:
        str: Resumen con datos y gráfico incluido.
    """
    dm = get_data_manager()
    summary = await dm.get_portfolio_summary()
    
    not_overdue = summary.total_outstanding_eur - summary.total_overdue_eur
    chart_id = await chart_generator.create_chart(
        chart_type="donut",
        title="Estado de la Cartera",
        data={
            "labels": ["Vencido", "No Vencido"],
            "values": [summary.total_overdue_eur, max(0, not_overdue)]
        },
        show_values=True
    )
    fig = chart_generator.get_chart(chart_id)
    chart_json = fig.to_json()
    chart_generator.clear_chart(chart_id)
    
    return f"{summary.model_dump_json()} CHART_JSON:{chart_json}"


@tool(args_schema=GetClientTrendInput)
async def get_client_trend(partner_id: int, recent_months: int = 6) -> str:
    """Analiza la tendencia de comportamiento de pago de un cliente.
    Compara el período reciente (últimos N meses) con el período anterior.
    Indica si el cliente está "mejorando", "empeorando" o "estable".
    Incluye gráfico de barras comparativo.

    Args:
        partner_id (int): ID del cliente a analizar.
        recent_months (int): Meses a considerar como período reciente.

    Returns:
        str: Análisis con métricas de ambos períodos, tendencia y gráfico.
    """
    dm = get_data_manager()
    trend = await dm.get_client_trend(partner_id=partner_id, recent_months=recent_months)
    
    if trend is None:
        return "No se encontró el cliente o no hay suficientes datos para analizar tendencia."
    
    chart_id = await chart_generator.create_chart(
        chart_type="bar",
        title=f"Evolución de Puntualidad - {trend.partner_name}",
        data={
            "labels": ["Período Anterior", "Período Reciente"],
            "series": [
                {
                    "name": "Puntualidad %",
                    "values": [
                        trend.previous_on_time_ratio * 100,
                        trend.recent_on_time_ratio * 100
                    ]
                },
                {
                    "name": "Retraso Promedio (días)",
                    "values": [
                        trend.previous_avg_delay,
                        trend.recent_avg_delay
                    ]
                }
            ]
        },
        show_values=True
    )
    fig = chart_generator.get_chart(chart_id)
    chart_json = fig.to_json()
    chart_generator.clear_chart(chart_id)
    
    return f"{trend.model_dump_json()} CHART_JSON:{chart_json}"


@tool(args_schema=GetDeterioratingClientsInput)
async def get_deteriorating_clients(limit: int = 10, min_invoices: int = 5) -> str:
    """Identifica clientes cuyo comportamiento de pago está EMPEORANDO.
    Compara métricas recientes vs históricas para detectar deterioro.
    Solo incluye clientes con historial suficiente (min_invoices).
    Incluye gráfico de barras horizontales.

    Args:
        limit (int): Máximo de clientes a devolver.
        min_invoices (int): Mínimo de facturas históricas requeridas para análisis.

    Returns:
        str: Clientes en deterioro con métricas comparativas y gráfico.
    """
    dm = get_data_manager()
    clients = await dm.get_deteriorating_clients(limit=limit, min_invoices=min_invoices)
    
    if not clients:
        return "No se encontraron clientes con deterioro significativo."
    
    chart_clients = clients[:10]
    labels = [c.partner_name[:25] for c in chart_clients]
    values = [abs(c.change_on_time_ratio * 100) for c in chart_clients]
    
    chart_id = await chart_generator.create_chart(
        chart_type="horizontal_bar",
        title="Clientes en Deterioro (Caída en Puntualidad %)",
        data={"labels": labels, "values": values},
        show_values=True
    )
    fig = chart_generator.get_chart(chart_id)
    chart_json = fig.to_json()
    chart_generator.clear_chart(chart_id)
    
    clients_data = [c.model_dump() for c in clients]
    return f"{json.dumps(clients_data)} CHART_JSON:{chart_json}"


@tool(args_schema=GenerateChartInput)
async def generate_chart(chart_type: ChartType, title: str, data: dict, show_values: bool = True) -> str:
    """Genera un gráfico visual personalizado.
    Usar solo si necesitas un gráfico diferente a los que ya generan las otras tools.

    TIPOS DE GRÁFICO:
    - bar: Barras verticales (comparaciones, distribuciones)
    - horizontal_bar: Barras horizontales (rankings, comparaciones de nombres largos)
    - line: Líneas (tendencias temporales, evolución)
    - pie: Circular (distribución porcentual, partes de un todo)
    - donut: Circular con hueco (similar a pie, más moderno)

    FORMATO DE DATA:
    - Simple: {"labels": ["A", "B", "C"], "values": [10, 20, 30]}
    - Múltiples series: {"labels": ["Q1", "Q2"], "series": [{"name": "2024", "values": [10, 20]}]}

    Args:
        chart_type (ChartType): Tipo de gráfico (bar, horizontal_bar, line, pie, donut).
        title (str): Título descriptivo del gráfico.
        data (dict): Datos del gráfico con labels y values (o series para múltiples).
        show_values (bool): Mostrar valores numéricos en el gráfico.

    Returns:
        str: Referencia del gráfico en formato "CHART_JSON:{json}".
    """
    chart_id = await chart_generator.create_chart(
        chart_type=chart_type,
        title=title,
        data=data,
        show_values=show_values
    )

    fig = chart_generator.get_chart(chart_id)
    chart_json = fig.to_json()
    chart_generator.clear_chart(chart_id)
    return f"CHART_JSON:{chart_json}"


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
