from langchain_core.tools import tool
from src.data.odoo_connector import OdooConnection
from src.data.models import Invoice, Partner

odoo_connector = OdooConnection()


@tool
def calculate_invoice_risk(invoice: Invoice):
    """
    Método que devuelve el riesgo de impago de una factura
    """
    ...

@tool
def calculate_client_risk(partner: Partner):
    """
    Método que devuelve el riesgo de impago de un cliente
    """
    ...

@tool
def get_client_historic(partner: Partner):
    """
    Método que devuelve el historico de un cliente.
    Útil para que el LLM tenga contexto (Ej: Cuántas facturas impagadas tiene x cliente? ...)
    """
    ...


