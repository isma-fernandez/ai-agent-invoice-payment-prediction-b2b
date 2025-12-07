import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict, List, Any
from pathlib import Path
from datetime import date
import joblib

from .odoo_connector import OdooConnection
from .retriever import DataRetriever
from .cleaner import DataCleaner
from .feature_engineering import FeatureEngineering
from .models import (
    ClientSearchResult, ClientInfo, InvoiceSummary, 
    PredictionResult, RiskCategory, PaymentState
)

class DataManager:
    """
    Centraliza la gestión de datos para el proyecto de predicción de pagos de facturas.
    Gestiona la extracción, limpieza y preparación de los datos.
    Tanto datos del agente como datos para el modelo de IA.

    """
    
    def __init__(self, cutoff_date: str = None):
        """Inicializa el DataManager.
        Args:
            cutoff_date: Fecha de corte para cálculos de features (YYYY-MM-DD).
        Attributes:
            cutoff_date: Fecha de corte para cálculos de features.
            _odoo_connection: Conexión a Odoo.
            _data_retriever: Objeto de extracción de datos.
            _cleaner: Objeto de limpieza de datos.
            _feature_engineering: Objeto de ingeniería de características.
            _models: Diccionario de modelos cargados.
            _model: Modelo principal para predicción.
            _transformations: Transformaciones aplicadas a los datos.
        """
        self.cutoff = cutoff_date or pd.Timestamp.now().strftime('%Y-%m-%d')

        # Conexión a Odoo
        self._odoo_connection: Optional[OdooConnection] = None
        self._data_retriever: Optional[DataRetriever] = None
        # Limpieza y procesamiento de datos
        self._cleaner: DataCleaner = DataCleaner()
        self._feature_engineering: FeatureEngineering = FeatureEngineering(cutoff_date=cutoff_date)
        # Modelos y transformaciones
        self._models: Dict[str, Any] = {} # Soporte para múltiples modelos (futura regresión)
        self._model: Optional[Any] = None # Modelo principal
        self._transformations: Dict[str, Any] = {}


    async def connect(self) -> None:
        """Establece la conexión con Odoo e inicializa el DataRetriever.
        """
        self._odoo_connection = OdooConnection()
        await self._odoo_connection.connect()
        self._data_retriever = DataRetriever(odoo_connection=self._odoo_connection)


    def load_model(self, model_path: str) -> None:
        """Carga un modelo de predicción desde el disco.
        
        Args:
            model_path: Ruta al archivo del modelo (joblib).
        """
        # TODO: Añadir ruta y nombre a la configuración
        # TODO: Soporte para múltiples modelos
        model = joblib.load(model_path)
        self._models['invoice_risk_model'] = model
        self._model = model


    async def _get_client_invoices_df(self, partner_id: int) -> pd.DataFrame:
        """Obtiene todas las facturas de un cliente y calcula las características
        derivadas."""

        raw_data = await self._data_retriever.get_invoices_by_partner(partner_id) 
        if not raw_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(raw_data)
        clean_data, _ = self._cleaner.clean_raw_data(df)

        if clean_data is None or clean_data.empty:
            return pd.DataFrame()
        
        dataset = self._feature_engineering.generate_full_client_data(clean_data)
        return dataset


    async def _get_invoice_df(self, invoice_id: int) -> Optional[pd.DataFrame]:
        """
        Obtiene una factura específica."""
        raw_data = await self._data_retriever.get_invoice_by_id(invoice_id)  
        if not raw_data:
            return None
        
        df = pd.DataFrame([raw_data])
        clean_data, _ = self._cleaner.clean_raw_data(df)
        
        if clean_data is None or clean_data.empty:
            return None
            
        return clean_data


    # NOTA: Se utiliza para encontrar el ID de un cliente a partir de su nombre
    async def search_clients(self, name: str, limit: int = 5) -> List[ClientSearchResult]:
        """
        Busca clientes por nombre.
        
        Args:
            name: Nombre de la empresa a buscar.
            limit: Máximo de resultados.
            
        Returns:
            Lista de ClientSearchResult con los clientes encontrados.
        """
        raw_data = await self._data_retriever.search_client_by_name(name, limit)
        if not raw_data:
            return []
        results = [ClientSearchResult(id=record['id'], name=record['name']) for record in raw_data]
        
        return results

    # NOTA: Una vez tenemos el ID del cliente, obtenemos su info
    async def get_client_info(self, partner_id: int) -> Optional[ClientInfo]:
        """
        Obtiene información y estadísticas agregadas de un cliente.
        
        Args:
            partner_id: ID del cliente en Odoo.
            
        Returns:
            ClientInfo con estadísticas del cliente o None si no existe.
        """
        df = await self._get_client_invoices_df(partner_id)
        
        if df.empty:
            return None
        
        stats = self._feature_engineering.calculate_client_stats(df)
        
        return ClientInfo(
            id=partner_id,
            name=df['partner_name'].iloc[0],
            country_name=df.get('country_name', pd.Series([None])).iloc[0],
            **stats
        )

    # NOTA: Realmente solo sirve para entrenar nuevos modelos
    async def get_all_partners(self) -> pd.DataFrame:
        """
        Obtiene todos los clientes.
        Útil para entrenar nuevos modelos.
        
        Returns:
            DataFrame con todos los partners y sus campos.
        """
        raw_data = await self._data_retriever.get_all_customer_partners()
        
        return pd.DataFrame(raw_data) if raw_data else pd.DataFrame()
    

    # TODO: El raise puede traer problemas
    async def predict(self, invoice_id: int) -> PredictionResult:
        """
        Predice el riesgo de impago de una factura.
        Devuelve también información para explicabilidad.
        
        Args:
            invoice_id: id de la factura a predecir.
            
        Returns:
            PredictionResult con:
            - invoice_id, invoice_name, partner_id, partner_name, amount_eur
            - prediction: clase predicha Puntual, Leve, Grave
            - probabilities: dict con probabilidad por clase
            
        Raises:
            ValueError: Si la factura no existe.
        """  
        invoice_df = await self._get_invoice_df(invoice_id)
        if invoice_df is None:
            raise ValueError(f"La factura con ID {invoice_id} no existe.")
        
        invoice = invoice_df.iloc[0]
        
        partner_id = invoice['partner_id']
        if isinstance(partner_id, (list, tuple)):
            partner_id = partner_id[0]  
        client_invoices = await self._get_client_invoices_df(partner_id)
        history = client_invoices[client_invoices['id'] != invoice_id]
        
        X = self._feature_engineering.process_invoice_for_prediction(
            new_invoice=invoice,
            client_invoices_df=history
        )
        
        prediction = self._model.predict(X)[0]
        probabilities = self._model.predict_proba(X)[0]
        classes = self._model.classes_
        prob_dict = {
            str(clase): round(float(prob), 4)
            for clase, prob in zip(classes, probabilities)
        }
        
        return PredictionResult(
            partner_id=int(partner_id),
            partner_name=invoice['partner_name'],
            is_hypothetical=False,
            invoice_id=invoice_id,
            invoice_name=invoice['name'],
            amount_eur=round(float(invoice['amount_total_eur']), 2),
            due_date=invoice['invoice_date_due'].date() if pd.notna(invoice['invoice_date_due']) else None,
            prediction=RiskCategory(prediction),
            probabilities=prob_dict
        )


    async def predict_hypothetical(
            self, partner_id: int, amount_eur: float, invoice_date: str = None,
            due_date: str = None, payment_term_days: int = 30) -> PredictionResult:
        """
        Predice riesgo para una factura que aún no se ha creado.
        
        Útil si se pide al agente: "Si le hago una factura con importe X, cuál sería el riesgo?"
        
        Args:
            partner_id: ID del cliente.
            amount_eur: Importe de la factura.
            invoice_date: Fecha de factura (valor por defecto: hoy).
            due_date: Fecha de vencimiento (valor por defecto: calculada con payment_term_days).
            payment_term_days: Días de plazo de pago (valor por defecto: 30).
            
        Returns:
            PredictionResult con la predicción o None si el cliente no tiene historial de facturas.
        """
        # TODO: No soporta diferentes monedas aún
        # TODO: No tiene sentido si el cliente no tiene historial de facturas,
        # hay que tratar ese caso aparte.
        
        invoice_date_ts = pd.Timestamp(invoice_date) if invoice_date else pd.Timestamp.now()
        if due_date:
            due_date_ts = pd.Timestamp(due_date)
        else:
            due_date_ts = invoice_date_ts + pd.Timedelta(days=payment_term_days)
        
        history = await self._get_client_invoices_df(partner_id)
        
        if history.empty:
            return None
        
        partner_name = history['partner_name'].iloc[0]
        company_name = history['company_name'].iloc[0]
        
        hypothetic_invoice = pd.Series({
            'id': -1,
            'name': 'hypothetic_invoice',
            'partner_id': partner_id,
            'partner_name': partner_name,
            'company_name': company_name,
            'currency_name': 'EUR',
            'amount_total_eur': amount_eur,
            'amount_residual_eur': amount_eur,
            'invoice_date': invoice_date_ts,
            'invoice_date_due': due_date_ts,
            'payment_dates': pd.NaT,
            'payment_state': 'not_paid',
        })
        
        X = self._feature_engineering.process_invoice_for_prediction(
            new_invoice=hypothetic_invoice,
            client_invoices_df=history
        )
        
        prediction = self._model.predict(X)[0]
        probabilities = self._model.predict_proba(X)[0]   
        classes = self._model.classes_
        prob_dict = {
            str(clase): round(float(prob), 4) 
            for clase, prob in zip(classes, probabilities)
        }
        
        return PredictionResult(
            partner_id=partner_id,
            partner_name=partner_name,
            is_hypothetical=True,
            invoice_id=None,
            invoice_name=None,
            amount_eur=round(amount_eur, 2),
            due_date=due_date_ts.date(),
            prediction=RiskCategory(prediction),
            probabilities=prob_dict
        )
    
    async def get_invoice_by_name(self, invoice_name: str) -> Optional[InvoiceSummary]:
        """Recupera una factura por su nombre.
        
        Args:
            invoice_name: Nombre de la factura a buscar.
            
        Returns:
            InvoiceSummary si se encuentra, None en caso contrario.
        """
        raw_data = await self._data_retriever.search_invoice_by_name(invoice_name)
        if not raw_data:
            return None
        partner_id = raw_data['partner_id']
        if isinstance(partner_id, (list, tuple)):
            partner_id = partner_id[0]
        invoice_id = raw_data['id']
        df = await self._get_client_invoices_df(partner_id)
        
        if df.empty:
            return None
        invoice_df = df[df['id'] == invoice_id]
        
        if invoice_df.empty:
            return None
        
        row = invoice_df.iloc[0]
        days_overdue = None
        if row['payment_state'] == 'not_paid' and pd.notna(row['invoice_date_due']):
            cutoff = pd.Timestamp(self.cutoff)
            if row['invoice_date_due'] < cutoff:
                days_overdue = (cutoff - row['invoice_date_due']).days

        return InvoiceSummary(
            id=int(row['id']),
            name=row['name'],
            amount_eur=round(float(row['amount_total_eur']), 2),
            invoice_date=row['invoice_date'].date() if pd.notna(row['invoice_date']) else None,
            due_date=row['invoice_date_due'].date() if pd.notna(row['invoice_date_due']) else None,
            payment_state=PaymentState(row['payment_state']),
            payment_date=row['payment_dates'].date() if pd.notna(row.get('payment_dates')) else None,
            paid_late=bool(row['paid_late']) if pd.notna(row.get('paid_late')) else None,
            delay_days=int(row['payment_overdue_days']) if pd.notna(row.get('payment_overdue_days')) else None,
            days_overdue=days_overdue
        )

    async def get_client_invoices(self, partner_id: int, limit: int = 20, 
                                   only_unpaid: bool = False) -> List[InvoiceSummary]:
        """Obtiene las facturas de un cliente para el agente.
        
        Args:
            partner_id: ID del cliente en Odoo.
            limit: Máximo de facturas a devolver.
            only_unpaid: Si True, solo devuelve facturas pendientes de pago.
            
        Returns:
            Lista de InvoiceSummary ordenada por fecha (más recientes primero).
        """
        df = await self._get_client_invoices_df(partner_id)
        
        if df.empty:
            return []
        
        if only_unpaid:
            df = df[df['payment_state'] == 'not_paid']
        
        df = df.head(limit)
        
        cutoff = pd.Timestamp(self.cutoff)
        invoices = []
        for _, row in df.iterrows():
            days_overdue = None
            if row['payment_state'] == 'not_paid' and pd.notna(row['invoice_date_due']):
                if row['invoice_date_due'] < cutoff:
                    days_overdue = (cutoff - row['invoice_date_due']).days
            
            invoices.append(InvoiceSummary(
                id=int(row['id']),
                name=row['name'],
                amount_eur=round(float(row['amount_total_eur']), 2),
                invoice_date=row['invoice_date'].date() if pd.notna(row['invoice_date']) else None,
                due_date=row['invoice_date_due'].date() if pd.notna(row['invoice_date_due']) else None,
                payment_state=PaymentState(row['payment_state']),
                payment_date=row['payment_dates'].date() if pd.notna(row.get('payment_dates')) else None,
                paid_late=bool(row['paid_late']) if pd.notna(row.get('paid_late')) else None,
                delay_days=int(row['payment_overdue_days']) if pd.notna(row.get('payment_overdue_days')) else None,
                days_overdue=days_overdue
            ))
        
        return invoices