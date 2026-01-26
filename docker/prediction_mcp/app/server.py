from fastmcp import FastMCP
from typing import Dict, List

from app.predictor import Predictor

mcp = FastMCP("prediction-mcp")

_predictor = None


def get_predictor() -> Predictor:
    """Obtiene el predictor."""
    global _predictor
    if _predictor is None:
        _predictor = Predictor()
    return _predictor


@mcp.tool()
def predict_invoice(invoice: dict, client_history: list) -> dict:
    """Predice el riesgo de impago de una factura.

    Args:
        invoice: Datos de la factura a predecir con campos:
            - amount_total_eur: Importe total en EUR
            - invoice_date: Fecha de emisión (YYYY-MM-DD)
            - invoice_date_due: Fecha de vencimiento (YYYY-MM-DD)
            - currency_name: Moneda (EUR, USD, etc.)
            - company_name: Nombre de la empresa

        client_history: Lista de facturas anteriores del cliente, cada una con:
            - amount_total_eur: Importe total en EUR
            - invoice_date: Fecha de emisión
            - invoice_date_due: Fecha de vencimiento
            - payment_state: Estado de pago (paid / not_paid)
            - payment_date: Fecha de pago (solo si paid)

    Returns:
        dict con:
            - prediction: Categoría de riesgo (Grave / Leve / Puntual)
            - probabilities: Probabilidades para cada categoría
    """
    predictor = get_predictor()
    return predictor.predict(invoice, client_history)


if __name__ == "__main__":
    mcp.run()
