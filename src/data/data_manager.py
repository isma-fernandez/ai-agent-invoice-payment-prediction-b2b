import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict, List, Any
from pathlib import Path
import joblib

from .odoo_connector import OdooConnection
from .data_retriever import DataRetriever
from .data_cleaner import DataCleaner
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

        # Datos en memoria
        self._invoices_df: Optional[pd.DataFrame] = None
        self._partners_df: Optional[pd.DataFrame] = None
        self._unpaid_invoices_df: Optional[pd.DataFrame] = None

    async def connect(self) -> None:
        """
        Establece la conexión con Odoo.
        """
        self._odoo_connection = OdooConnection()
        await self._odoo_connection.connect()
        self._data_retriever = DataRetriever(odoo_connection=self._odoo_connection)

    async def retrieve_data_from_odoo(self) -> None:
        """
        Recupera los datos de Odoo y los almacena en memoria.
        """
        if not self._data_retriever:
            raise RuntimeError("La conexión a Odoo no está establecida.")

        # Datos crudos
        invoices_raw = await self._data_retriever.get_invoices()
        partners_raw = await self._data_retriever.get_partners()
        invoices_raw_df = pd.DataFrame(invoices_raw)
        partners_raw_df = pd.DataFrame(partners_raw)

        # Limpieza de datos
        invoices_cleaned_df, partners_cleaned_df = self._cleaner.clean_raw_data(
            invoices_df=invoices_raw_df,
            partners_df=partners_raw_df
        )

        self._invoices_df = invoices_cleaned_df
        self._partners_df = partners_cleaned_df