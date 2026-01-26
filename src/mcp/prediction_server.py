from fastmcp import FastMCP
import joblib
import pandas as pd
from src.config.prediction_mcp_settings import prediction_mcp_settings

mcp = FastMCP("prediction-mcp")

MODEL_FEATURES = [
    'amount_total_eur', 'term', 'currency_name', 'company_name',
    'due_last_three_days_month', 'due_date_second_half_month',
    'num_prior_invoices', 'num_late_prior_invoices', 'ratio_late_prior_invoices',
    'avg_delay_prior_late_invoices', 'avg_delay_prior_all', 'avg_payment_term_prior_invoices',
    'avg_invoiced_prior', 'total_invoice_amount_prior', 'total_invoice_amount_late_prior',
    'ratio_invoice_amount_late_prior', 'num_outstanding_invoices', 'num_outstanding_invoices_late',
    'ratio_outstanding_invoices_late', 'total_invoice_amount_outstanding',
    'total_invoice_amount_outstanding_late', 'ratio_invoice_amount_outstanding_late',
    'partner_freq'
]

LABEL_MAPPING = {0: 'Grave', 1: 'Leve', 2: 'Puntual'}

_model = None


def get_model():
    """Carga el modelo de prediccion de impagos."""
    global _model
    if _model is None:
        _model = joblib.load(prediction_mcp_settings.MODEL_PATH)
    return _model


@mcp.tool()
def predict(features: dict) -> dict:
    """Predice el riesgo de impago a partir de las features calculadas.

    Args:
        features: Diccionario con las 23 features del modelo:
            - amount_total_eur: Importe total en EUR
            - term: Plazo de pago (0, 30, 45, 60, 90, 120)
            - currency_name: Moneda (EUR, USD, etc.)
            - company_name: Nombre de la empresa
            - due_last_three_days_month: Si vence en últimos 3 días del mes (0/1)
            - due_date_second_half_month: Si vence en segunda mitad del mes (0/1)
            - num_prior_invoices: Número de facturas previas pagadas
            - num_late_prior_invoices: Número de facturas previas pagadas tarde
            - ratio_late_prior_invoices: Ratio de facturas pagadas tarde
            - avg_delay_prior_late_invoices: Promedio días retraso (solo tardías)
            - avg_delay_prior_all: Promedio días retraso (todas)
            - avg_payment_term_prior_invoices: Promedio plazo facturas previas
            - avg_invoiced_prior: Promedio importe facturas previas
            - total_invoice_amount_prior: Total facturado previo
            - total_invoice_amount_late_prior: Total facturado previo (tardías)
            - ratio_invoice_amount_late_prior: Ratio importe tardío
            - num_outstanding_invoices: Facturas pendientes previas
            - num_outstanding_invoices_late: Facturas pendientes vencidas
            - ratio_outstanding_invoices_late: Ratio pendientes vencidas
            - total_invoice_amount_outstanding: Total pendiente
            - total_invoice_amount_outstanding_late: Total pendiente vencido
            - ratio_invoice_amount_outstanding_late: Ratio pendiente vencido
            - partner_freq: Frecuencia del cliente (num facturas totales)

    Returns:
        dict con prediction (Grave/Leve/Puntual) y probabilities
    """
    model = get_model()
    
    feature_cols = [f for f in MODEL_FEATURES if f != 'partner_name']
    X = pd.DataFrame([{col: features.get(col, 0) for col in feature_cols}])
    prediction_idx = int(model.predict(X)[0])
    prediction = LABEL_MAPPING[prediction_idx] 
    probabilities = model.predict_proba(X)[0]
    classes = model.classes_
    prob_dict = {
        LABEL_MAPPING[int(clase)]: round(float(prob), 4)
        for clase, prob in zip(classes, probabilities)
    }
    
    return {
        "prediction": prediction,
        "probabilities": prob_dict
    }


if __name__ == "__main__":
    mcp.run()
