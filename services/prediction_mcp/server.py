from fastmcp import FastMCP
from typing import Dict, List

from services.prediction_mcp.predictor import Predictor
from services.prediction_mcp.trainer import Trainer

mcp = FastMCP("prediction-mcp")

_predictor = None
_trainer = None


def get_predictor() -> Predictor:
    """Obtiene el predictor."""
    global _predictor
    if _predictor is None:
        _predictor = Predictor()
    return _predictor


def get_trainer(cutoff_date: str = None) -> Trainer:
    """Obtiene el trainer."""
    global _trainer
    if _trainer is None or cutoff_date:
        _trainer = Trainer(cutoff_date=cutoff_date)
    return _trainer


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


@mcp.tool()
def generate_training_data(invoices: list, cutoff_date: str = None) -> dict:
    """Genera dataset de entrenamiento a partir de facturas limpias.

    Args:
        invoices: Lista de facturas limpias (de DataCleaner), cada una con:
            - id: ID de la factura
            - partner_id: ID del cliente
            - partner_name: Nombre del cliente
            - amount_total_eur: Importe total
            - invoice_date: Fecha de emisión
            - invoice_date_due: Fecha de vencimiento
            - payment_state: Estado de pago (paid / not_paid)
            - payment_dates: Fecha de pago (solo si paid)
            
        cutoff_date: Fecha de corte para entrenamiento (YYYY-MM-DD).
            Si es None, usa la fecha actual.

    Returns:
        dict con:
            - X: Lista de diccionarios con features
            - y: Lista de categorías target (Grave / Leve / Puntual)
            - feature_names: Lista de nombres de features
    """
    trainer = get_trainer(cutoff_date=cutoff_date)
    X_list, y_list = trainer.generate_training_dataset_from_raw(invoices)
    
    feature_names = [f for f in trainer._fe.MODEL_FEATURES if f != 'partner_name'] + ['partner_freq']
    
    return {
        "X": X_list,
        "y": y_list,
        "feature_names": feature_names
    }


if __name__ == "__main__":
    mcp.run()
