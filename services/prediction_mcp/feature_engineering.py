import pandas as pd
import numpy as np
from typing import Any, Dict, Optional, Tuple

class FeatureEngineering:
    """Transformación de datos limpios de Odoo en características para el modelo.

    Esta clase genera las características (features) necesarias tanto para el 
    entrenamiento del modelo de predicción de impagos como para el agente.

    Attributes:
        MODEL_FEATURES (list): Lista de características finales seleccionadas para el modelo.
        HISTORICAL_FEATURES (list): Lista de características calculadas basadas en el historial.
        cutoff_date (pd.Timestamp): Fecha de corte para los cálculos.
        outlier_percentile (float): Percentil utilizado para filtrar outliers (0.995).

    """


    # Características del modelo
    MODEL_FEATURES = [
        'amount_total_eur', 'term', 'currency_name', 'company_name', 
        'due_last_three_days_month', 'due_date_second_half_month',
        'num_prior_invoices', 'num_late_prior_invoices', 'ratio_late_prior_invoices',
        'avg_delay_prior_late_invoices', 'avg_delay_prior_all', 'avg_payment_term_prior_invoices',
        'avg_invoiced_prior', 'total_invoice_amount_prior', 'total_invoice_amount_late_prior', 
        'ratio_invoice_amount_late_prior', 'num_outstanding_invoices', 'num_outstanding_invoices_late', 
        'ratio_outstanding_invoices_late', 'total_invoice_amount_outstanding', 
        'total_invoice_amount_outstanding_late', 'ratio_invoice_amount_outstanding_late'
    ]


    # Características derivadas
    HISTORICAL_FEATURES = [
        'avg_invoiced_prior', 'num_prior_invoices', 'num_late_prior_invoices', 
        'ratio_late_prior_invoices', 'total_invoice_amount_prior', 
        'total_invoice_amount_late_prior', 'ratio_invoice_amount_late_prior',
        'avg_delay_prior_late_invoices', 'avg_delay_prior_all', 
        'num_outstanding_invoices', 'num_outstanding_invoices_late',
        'ratio_outstanding_invoices_late', 'total_invoice_amount_outstanding', 
        'total_invoice_amount_outstanding_late', 'ratio_invoice_amount_outstanding_late',
        'avg_payment_term_prior_invoices'
    ]

    def __init__(self, cutoff_date: str = None):
        """Inicializa la clase FeatureEngineering.

        Args:
            cutoff_date (str, optional): Fecha de corte para determinar facturas vencidas.
                Si es None, usa la fecha actual (para producción).
        """
        if cutoff_date:
            self.cutoff_date = pd.Timestamp(cutoff_date)
        else:
            self.cutoff_date = pd.Timestamp.now()

        # % de facturas a eliminar según días de retraso (outliers)
        self.outlier_percentile = 0.995


    def process_invoice_for_prediction(self, new_invoice: pd.Series,
                                       client_invoices_df: pd.DataFrame) -> pd.DataFrame:
        """Procesa una factura nueva para obtener predicción del modelo.
        
        Args:
            new_invoice (pd.Series): Datos de la factura nueva (ya limpia).
            client_invoices_df (pd.DataFrame): DataFrame con el historial de facturas del cliente.
            
        Returns:
            pd.DataFrame: DataFrame de una fila con las features listas para el modelo.
        """
        # Separar historial del cliente en pagadas e impagadas
        paid_history = client_invoices_df[client_invoices_df['payment_state'] == 'paid'].copy()
        unpaid_history = client_invoices_df[client_invoices_df['payment_state'] == 'not_paid'].copy()
        
        # Añadir payment_overdue_days a las pagadas del historial
        if len(paid_history) > 0:
            paid_history = self._add_payment_features(paid_history)
        
        # Crear DataFrame de una fila con la nueva factura
        df = pd.DataFrame([new_invoice])
        
        # Añadir term(sin payment_overdue_days porque no tiene sentido)
        df = self._add_payment_features(df, calculate_overdue=False)
        
        # Añadir features de fecha
        df = self._add_date_features(df)
        
        # Inicializar características históricas
        df = self._init_historical_features(df)
        
        # Calcular características históricas usando el historial del cliente
        invoice_date = df.loc[0, 'invoice_date']
        
        # Solo facturas anteriores a la nueva
        prior_paid = paid_history[paid_history['invoice_date'] < invoice_date]
        prior_unpaid = unpaid_history[unpaid_history['invoice_date'] < invoice_date]
        
        self._update_prior_invoices_features(df, 0, prior_paid)
        self._update_outstanding_features(df, 0, prior_unpaid)
        
        # Añadir partner_freq basado en el historial
        partner_freq = len(client_invoices_df) + 1
        df['partner_freq'] = partner_freq
        
        # Convertir bool a int
        df['due_last_three_days_month'] = df['due_last_three_days_month'].astype(int)
        df['due_date_second_half_month'] = df['due_date_second_half_month'].astype(int)
        
        # Seleccionar características del modelo
        feature_cols = [f for f in self.MODEL_FEATURES if f != 'partner_name'] + ['partner_freq']
        
        return df[feature_cols]


    def _add_payment_features(self, df: pd.DataFrame, 
                              calculate_overdue: bool = True) -> pd.DataFrame:
        """Añade características de pago: payment_overdue_days, term.
        """
        df = df.copy()
        
        if calculate_overdue and 'payment_dates' in df.columns:
            has_payment = df['payment_dates'].notna()
            df.loc[has_payment, 'payment_overdue_days'] = (
                df.loc[has_payment, 'payment_dates'] - df.loc[has_payment, 'invoice_date_due']
            ).dt.days
        
        df['payment_term_in_days'] = (df['invoice_date_due'] - df['invoice_date']).dt.days
        df['term'] = df['payment_term_in_days'].apply(self._map_days_to_term)
        df = df.drop(columns=['payment_term_in_days'])
        
        return df


    def _add_date_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Añade características de fecha.
        Añade: due_last_three_days_month, due_date_second_half_month.
        """
        df = df.copy()
        df['due_last_three_days_month'] = df['invoice_date_due'].apply(self._is_last_three_days)
        df['due_date_second_half_month'] = df['invoice_date_due'].dt.day > 15
        return df


    def _init_historical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Inicializa las columnas de características históricas a 0.
        """
        df = df.copy()
        df[self.HISTORICAL_FEATURES] = 0.0
        return df


    def _update_prior_invoices_features(self, df: pd.DataFrame, idx: int, 
                                        prior_invoices: pd.DataFrame) -> None:
        """Calcula las características relacionadas con facturas previas pagadas.
        """
        if len(prior_invoices) == 0:
            return
            
        late_prior = prior_invoices[prior_invoices['payment_overdue_days'] > 0]
        
        df.loc[idx, 'avg_invoiced_prior'] = prior_invoices['amount_total_eur'].mean()
        df.loc[idx, 'num_prior_invoices'] = len(prior_invoices)
        df.loc[idx, 'total_invoice_amount_prior'] = prior_invoices['amount_total_eur'].sum()
        df.loc[idx, 'avg_delay_prior_all'] = prior_invoices['payment_overdue_days'].mean()
        df.loc[idx, 'avg_payment_term_prior_invoices'] = prior_invoices['term'].mean()
        
        if len(late_prior) > 0:
            df.loc[idx, 'num_late_prior_invoices'] = len(late_prior)
            df.loc[idx, 'ratio_late_prior_invoices'] = len(late_prior) / len(prior_invoices)
            df.loc[idx, 'total_invoice_amount_late_prior'] = late_prior['amount_total_eur'].sum()
            df.loc[idx, 'ratio_invoice_amount_late_prior'] = (
                late_prior['amount_total_eur'].sum() / prior_invoices['amount_total_eur'].sum()
            )
            df.loc[idx, 'avg_delay_prior_late_invoices'] = late_prior['payment_overdue_days'].mean()


    def _update_outstanding_features(self, df: pd.DataFrame, idx: int, 
                                     outstanding_invoices: pd.DataFrame) -> None:
        """Calcula las características relacionadas con facturas pendientes (outstanding).
        """
        if len(outstanding_invoices) == 0:
            return
            
        df.loc[idx, 'num_outstanding_invoices'] = len(outstanding_invoices)
        df.loc[idx, 'total_invoice_amount_outstanding'] = outstanding_invoices['amount_total_eur'].sum()
        
        late_outstanding = outstanding_invoices[
            outstanding_invoices['invoice_date_due'] < self.cutoff_date
        ]
        
        if len(late_outstanding) > 0:
            df.loc[idx, 'num_outstanding_invoices_late'] = len(late_outstanding)
            df.loc[idx, 'ratio_outstanding_invoices_late'] = len(late_outstanding) / len(outstanding_invoices)
            df.loc[idx, 'total_invoice_amount_outstanding_late'] = late_outstanding['amount_total_eur'].sum()
            df.loc[idx, 'ratio_invoice_amount_outstanding_late'] = (
                late_outstanding['amount_total_eur'].sum() / outstanding_invoices['amount_total_eur'].sum()
            )


    def _is_last_three_days(self, date) -> bool:
        """Determina si la fecha está en los últimos 3 días del mes.
        """
        if pd.isna(date):
            return False
        month = date.month
        year = date.year
        
        if month == 12:
            days_in_month = 31
        else:
            days_in_month = (pd.Timestamp(year, month + 1, 1) - pd.Timedelta(days=1)).day
        
        return date.day > days_in_month - 3


    def _map_days_to_term(self, days) -> int:
        """Mapea los días de término de pago a categorías redondeadas (bins).
        """
        if pd.isna(days):
            return 30
        if days <= 20:
            return 0
        elif days <= 40:
            return 30
        elif days <= 55:
            return 45
        elif days <= 75:
            return 60
        elif days <= 95:
            return 90
        else:
            return 120
