"""Mensajes de estado para la interfaz de usuario."""

AGENT_MESSAGES = {
    "data_agent": "Consultando datos en Odoo...",
    "analysis_agent": "Realizando análisis...",
    "memory_agent": "Gestionando memoria...",
    "final_answer": "Generando respuesta...",
    "router": "Delegando tareas...",
}

TOOL_MESSAGES = {
    # DataAgent tools
    "check_connection": "Verificando conexión con Odoo...",
    "search_client": "Buscando cliente...",
    "get_client_info": "Obteniendo información del cliente...",
    "get_client_invoices": "Recuperando facturas del cliente...",
    "get_invoice_by_name": "Buscando factura...",
    "get_overdue_invoices": "Obteniendo facturas vencidas...",
    "get_upcoming_due_invoices": "Buscando facturas próximas a vencer...",
    "get_invoices_by_period": "Recuperando facturas del período...",
    # AnalysisAgent tools
    "predict_invoice_risk": "Analizando riesgo de la factura...",
    "predict_hypothetical_invoice": "Calculando predicción hipotética...",
    "get_high_risk_clients": "Identificando clientes de alto riesgo...",
    "compare_clients": "Comparando clientes...",
    "get_aging_report": "Generando informe de antigüedad...",
    "get_portfolio_summary": "Generando resumen de cartera...",
    "get_client_trend": "Analizando tendencia del cliente...",
    "get_deteriorating_clients": "Identificando clientes en deterioro...",
    # MemoryAgent tools
    "save_client_note": "Guardando nota del cliente...",
    "get_client_notes": "Recuperando notas del cliente...",
    "save_alert": "Registrando alerta...",
    "get_active_alerts": "Consultando alertas activas...",
}


def get_agent_message(agent_name: str) -> str | None:
    """Obtiene el mensaje de estado para un agente."""
    agent_name_lower = agent_name.lower()
    for key, message in AGENT_MESSAGES.items():
        if key in agent_name_lower:
            return message
    return None


def get_tool_message(tool_name: str) -> str:
    """Obtiene el mensaje de estado para una herramienta."""
    return TOOL_MESSAGES.get(tool_name, "Procesando...")