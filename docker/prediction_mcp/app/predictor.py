import joblib
import pandas as pd
from typing import Dict, List

from .data_processor import DataProcessor
from .feature_engineering import FeatureEngineering


class Predictor:
    """Encapsula el modelo de predicción y toda la lógica asociada."""

    LABEL_MAPPING = {0: 'Grave', 1: 'Leve', 2: 'Puntual'}

    def __init__(self, model_path: str = "models/late_invoice_payment_classification.pkl"):
        """Inicializa el predictor cargando el modelo.

        Args:
            model_path: Ruta al archivo del modelo entrenado.
        """
        self.model_path = model_path
        self._model = None
        self._data_processor = DataProcessor()
        self._feature_engineering = FeatureEngineering()

    def _load_model(self):
        """Carga el modelo de predicción."""
        if self._model is None:
            self._model = joblib.load(self.model_path)
        return self._model

    def predict(self, invoice: Dict, client_history: List[Dict]) -> Dict:
        """Predice el riesgo de impago de una factura.

        Args:
            invoice: Diccionario con los datos de la factura a predecir.
            client_history: Lista de diccionarios con el historial de facturas del cliente.

        Returns:
            Dict con prediction (Grave/Leve/Puntual) y probabilities.
        """
        model = self._load_model()

        # Convertir datos crudos a formato DataFrame
        invoice_series = self._data_processor.process_invoice(invoice)
        history_df = self._data_processor.process_client_history(client_history)

        # Calcular features
        X = self._feature_engineering.process_invoice_for_prediction(
            new_invoice=invoice_series,
            client_invoices_df=history_df
        )

        # Predicción
        prediction_idx = int(model.predict(X)[0])
        prediction = self.LABEL_MAPPING[prediction_idx]

        # Probabilidades
        probabilities = model.predict_proba(X)[0]
        classes = model.classes_
        prob_dict = {
            self.LABEL_MAPPING[int(clase)]: round(float(prob), 4)
            for clase, prob in zip(classes, probabilities)
        }

        return {
            "prediction": prediction,
            "probabilities": prob_dict
        }
