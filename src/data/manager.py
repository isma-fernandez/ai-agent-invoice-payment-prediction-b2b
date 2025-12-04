import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict, List, Any
from pathlib import Path
import joblib

from .odoo_connector import OdooConnection
from .retriever import DataRetriever
from .cleaner import DataCleaner
from .feature_engineering import FeatureEngineering

class DataManager:
    """
    Centraliza la gestión de datos para el proyecto de predicción de pagos de facturas.
    Gestiona la extracción, limpieza y preparación de los datos.
    Tanto datos del agente como datos para el modelo de IA.
    """
    
    def __init__(self, cutoff_date: str = None):
        self.cutoff_date = cutoff_date or pd.Timestamp.now().strftime('%Y-%m-%d')

        # Conexión a Odoo
        self._odoo_connection: Optional[OdooConnection] = None
        self._data_retriever: Optional[DataRetriever] = None

        # Limpieza y procesamiento de datos
        self._cleaner: DataCleaner = DataCleaner()
        self._feature_engineering: FeatureEngineering = FeatureEngineering(cutoff_date=cutoff_date)

        # Modelos y transformaciones
        self._models: Dict[str, Any] = {}
        self._transformations: Dict[str, Any] = {}

    async def connect(self) -> None:
        """
        Establece la conexión con Odoo.
        """
        self._odoo_connection = OdooConnection()
        await self._odoo_connection.connect()
        self._data_retriever = DataRetriever(odoo_connection=self._odoo_connection)

    def load_model(self, model_path: str) -> None:
        """
        Carga el modelo de predicción desde el disco.
        # TODO: Mejorar para múltiples modelos
        # TODO: Añadir ruta y nombre a la configuración
        """
        model = joblib.load(model_path)
        self._models['invoice_risk_model'] = model

    def is_data_ready(self) -> bool:
        """
        Verifica si los datos necesarios están cargados y listos para su uso.
        """
        return self._invoices_df is not None and self._partners_df is not None
    