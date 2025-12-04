import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict, List, Any
from pathlib import Path
import joblib

from .odoo_connector import OdooConnection
from .retriever import DataRetriever
from .cleaner import DataCleaner
from .feature_engineering import FeatureEngineering

#TODO: Añadir ejemplos de uso en docstrings

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


    async def get_client_invoices(self, partner_id: int) -> pd.DataFrame:
        """Obtiene todas las facturas de un cliente y calcula las características
        derivadas.
        
        Args:
            partner_id: ID del cliente en Odoo.
            
        Returns:
            DataFrame con columnas:
            - Datos originales: id, name, partner_id, partner_name, company_name,
              currency_name, amount_total_eur, amount_residual_eur, payment_state,
              invoice_date, invoice_date_due, payment_dates
            - Características derivadas: payment_overdue_days, payment_term_days,
              avg_invoiced_prior, num_prior_invoices, ratio_late_prior_invoices,
              avg_delay_prior_all, num_outstanding_invoices, etc.
            
            DataFrame vacío si no hay facturas.
        """
        
        # Dattos raw de Odoo
        raw_data = await self._data_retriever.get_invoices_by_partner(partner_id) 
        if not raw_data:
            return pd.DataFrame()
        
        # Limpieza de los datos
        df = pd.DataFrame(raw_data)
        clean_data, _ = self._cleaner.clean_raw_data(df)

        if not clean_data:
            return pd.DataFrame()
        
        # Cálculo de características derivadas
        dataset = self._feature_engineering.generate_full_client_data(clean_data)
        return dataset


    async def get_invoice(self, invoice_id: int) -> Optional[pd.Series]:
        """
        Obtiene una factura específica.
        
        Args:
            invoice_id: ID de la factura en Odoo.
            
        Returns:
            DataFrame con todos los campos de la factura o None si no existe.
        """
        raw_data = await self._data_retriever.get_invoice_by_id(invoice_id)  
        if not raw_data:
            return None
        
        # Limpieza de los datos
        df = pd.DataFrame([raw_data])
        clean_data, _ = self._cleaner.clean_raw_data(df)
        
        return clean_data if clean_data else None

    async def search_clients(self, query: str, limit: int = 10) -> pd.DataFrame:
        """
        Busca clientes por nombre.
        
        Args:
            query: Nombre de la empresa a buscar.
            limit: Máximo de resultados.
            
        Returns:
            DataFrame con columnas: id, name, country
        """
        # TODO: Falta implementar método en DataRetriever

        ...
        
        return None

    async def get_all_partners(self) -> pd.DataFrame:
        """
        Obtiene todos los clientes.
        
        Returns:
            DataFrame con todos los partners y sus campos.
        """
        raw_data = await self._data_retriever.get_all_customer_partners()
        
        # TODO: Aquí hay que hacer algo para poder limpiar los datos del cliente 
        # sin necesidad de las facturas
        
        return pd.DataFrame(raw_data) if raw_data else pd.DataFrame()
    
    async def predict(self, invoice_id: int) -> Dict[str, Any]:
        """
        Predice el riesgo de impago de una factura.
        Devuelve también información para explicabilidad.
        
        Args:
            invoice_id: id de la factura a predecir.
            
        Returns:
            Dict con:
            - invoice_id, invoice_name, partner_id, partner_name, amount_eur
            - prediction: clase predicha Puntual, Leve, Grave
            - probabilities: dict con probabilidad por clase
            - risk_level: ALTO, MEDIO, BAJO
            - error: mensaje si algo falla
        """  
        # Obtener factura
        invoice = await self.get_invoice(invoice_id)
        if invoice is None:
            return {'error': f'Factura {invoice_id} no encontrada'} 
        # Obtener información del cliente
        partner_id = invoice['partner_id']
        if isinstance(partner_id, (list, tuple)):
            partner_id = partner_id[0]  
        # Obtener historial del cliente
        client_invoices = await self.get_client_invoices(partner_id)
        history = client_invoices[client_invoices['id'] != invoice_id]
        
        # Preparar datos para el modelo
        X = self._feature_engineering.process_invoice_for_prediction(
            new_invoice=invoice,
            client_invoices_df=history
        )
        
        # Predecir
        prediction = self._model.predict(X)[0]
        probabilities = self._model.predict_proba(X)[0]
        classes = self._model.classes_
        prob_dict = {
            str(clase): prob 
            for clase, prob in zip(classes, probabilities)
        }
        
        return {
            'invoice_id': invoice_id,
            'invoice_name': invoice['name'],
            'partner_id': partner_id,
            'partner_name': invoice['partner_name'],
            'amount_eur': round(float(invoice['amount_total_eur']), 2),
            'due_date': invoice['invoice_date_due'],
            'prediction': str(prediction),
            'probabilities': prob_dict,
        }

    async def predict_hypothetical(
            self, partner_id: int, amount_eur: float, invoice_date: str = None,
            due_date: str = None, payment_term_days: int = 30) -> Dict[str, Any]:
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
            Dict con predicción
        """
        # TODO: No soporta diferentes monedas aún
        # TODO: No tiene sentido si el cliente no tiene historial de facturas,
        # hay que tratar ese caso aparte.
        
        invoice_date = pd.Timestamp(invoice_date) if invoice_date else pd.Timestamp.now()
        if due_date:
            due_date = pd.Timestamp(due_date)
        else:
            due_date = invoice_date + pd.Timedelta(days=payment_term_days)
        
        # Historial del cliente
        history = await self.get_client_invoices(partner_id)
        partner_name = history['partner_name'].iloc[0] if len(history) > 0 else 'Unknown'
        company_name = history['company_name'].iloc[0] if len(history) > 0 else 'Unknown'
        
        hypothetic_invoice = pd.Series({
            'id': -1,
            'name': 'hypothetic_invoice',
            'partner_id': partner_id,
            'partner_name': partner_name,
            'company_name': company_name,
            'currency_name': 'EUR',
            'amount_total_eur': amount_eur,
            'amount_residual_eur': amount_eur,
            'invoice_date': invoice_date,
            'invoice_date_due': due_date,
            'payment_dates': pd.NaT,
            'payment_state': 'not_paid',
        })
        
        # Características y predecir
        X = self._feature_engineering.process_invoice_for_prediction(
            new_invoice=hypothetic_invoice,
            client_invoices_df=history
        )
        
        prediction = self._model.predict(X)[0]
        probabilities = self._model.predict_proba(X)[0]   
        classes = self._model.classes_
        prob_dict = {
            str(clases): round(float(prob), 4) 
            for clases, prob in zip(classes, probabilities)
        }
        
        return {
            'hypothetic': True,
            'partner_id': partner_id,
            'partner_name': partner_name,
            'amount_eur': round(amount_eur, 2),
            'invoice_date': invoice_date.strftime('%Y-%m-%d'),
            'due_date': due_date.strftime('%Y-%m-%d'),
            'payment_term_days': payment_term_days,
            'prediction': str(prediction),
            'probabilities': prob_dict,
        }





