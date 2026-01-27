import pandas as pd
import numpy as np
from typing import Tuple, List, Dict

from app.feature_engineering import FeatureEngineering


class Trainer:
    """Genera el dataset para el entrenamiento del modelo de predicción de impagos.
    
    Esta clase se encarga de procesar facturas limpias y generar el dataset
    con las features necesarias para entrenar el modelo.
    """

    def __init__(self, cutoff_date: str = None):
        """Inicializa el Trainer.
        
        Args:
            cutoff_date: Fecha de corte para determinar facturas vencidas.
                Si es None, usa la fecha actual.
        """
        self._fe = FeatureEngineering(cutoff_date=cutoff_date)
        self.cutoff_date = self._fe.cutoff_date
        # % de facturas a eliminar según días de retraso (outliers)
        self.outlier_percentile = 0.995

    def generate_training_dataset(self, invoices_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Genera el dataset para entrenar el modelo con el formato requerido.
        
        Proceso:
            1. Filtra solo facturas pagadas antes de cutoff_date.
            2. Elimina outliers y facturas no útiles.
            3. Calcula features históricas.
            4. Divide en X e y.
        
        Args:
            invoices_df: DataFrame con facturas limpias (de DataCleaner).
            
        Returns:
            Tuple[pd.DataFrame, pd.Series]: Tupla con (X, y) listos para entrenar.
        """
        df = invoices_df.copy()
        
        # Separar pagadas e impagadas (impagadas se usan para calcular outstanding features)
        paid_df = df[df['payment_state'] == 'paid'].copy()
        unpaid_df = df[df['payment_state'] == 'not_paid'].copy()
        
        # Solo facturas pagadas antes de cutoff (en producción, serán todas)
        paid_df = paid_df[paid_df['payment_dates'] <= self.cutoff_date]
        
        # Eliminar facturas no útiles (pagos el mismo día o vencimiento)
        paid_df = paid_df[paid_df['invoice_date_due'] != paid_df['invoice_date']]
        paid_df = paid_df[paid_df['payment_dates'] != paid_df['invoice_date']]
        
        # Añadir características de pago (payment_overdue_days, term_rounded)
        paid_df = self._fe._add_payment_features(paid_df)
        
        # Eliminar outliers en días de retraso
        delay_threshold = paid_df['payment_overdue_days'].quantile(self.outlier_percentile)
        paid_df = paid_df[paid_df['payment_overdue_days'] <= delay_threshold]
        
        # Asignar categorías (target)
        paid_df = self._assign_delay_categories(paid_df)
        
        # Añadir características basadas en invoice_date
        paid_df = self._fe._add_date_features(paid_df)
        
        # Inicializar y calcular características históricas
        paid_df = self._fe._init_historical_features(paid_df)
        paid_df = paid_df.sort_values(by='invoice_date', ascending=True).reset_index(drop=True)
        
        for idx in range(len(paid_df)):
            self._calculate_historical_features_for_invoice(
                df=paid_df,
                idx=idx,
                paid_invoices_df=paid_df.iloc[:idx],
                unpaid_invoices_df=unpaid_df
            )
        
        paid_df['paid_late'] = paid_df['payment_overdue_days'] > 0
        
        # Añadir partner_freq (frequency encoding)
        freq = paid_df['partner_name'].value_counts()
        paid_df['partner_freq'] = paid_df['partner_name'].map(freq)
        
        # Convertir bool a int
        paid_df['due_last_three_days_month'] = paid_df['due_last_three_days_month'].astype(int)
        paid_df['due_date_second_half_month'] = paid_df['due_date_second_half_month'].astype(int)
        feature_cols = [f for f in self._fe.MODEL_FEATURES if f != 'partner_name'] + ['partner_freq']
        
        X = paid_df[feature_cols].copy()
        y = paid_df['payment_overdue_category'].copy()
        
        return X, y

    def _calculate_historical_features_for_invoice(self, df: pd.DataFrame, idx: int,
        paid_invoices_df: pd.DataFrame, unpaid_invoices_df: pd.DataFrame) -> None:
        """Calcula características históricas para una factura específica.
        """
        row = df.loc[idx]
        partner_id = row['partner_id']
        invoice_date = row['invoice_date']
        
        prior_invoices = paid_invoices_df[
            (paid_invoices_df['partner_id'] == partner_id) & 
            (paid_invoices_df['invoice_date'] < invoice_date)
        ]
        
        outstanding_invoices = unpaid_invoices_df[
            (unpaid_invoices_df['partner_id'] == partner_id) & 
            (unpaid_invoices_df['invoice_date'] < invoice_date)
        ]
        
        self._fe._update_prior_invoices_features(df, idx, prior_invoices)
        self._fe._update_outstanding_features(df, idx, outstanding_invoices)

    def _assign_delay_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        """Asigna categorías de retraso basadas en payment_overdue_days.
        """
        df = df.copy()
        if 'payment_overdue_days' in df.columns:
            df['payment_overdue_category'] = df['payment_overdue_days'].apply(self._categorize_delay)
        return df

    def _categorize_delay(self, days) -> str:
        """Mapea los días de retraso a categorías.
        Categorías:
            - Puntual: days <= 0
            - Leve: 1 <= days <= 30
            - Grave: days > 30
        """
        if pd.isna(days):
            return None
        if days <= 0:
            return 'Puntual'
        elif 1 <= days <= 30:
            return 'Leve'
        else:
            return 'Grave'

    def generate_training_dataset_from_raw(self, invoices_data: List[Dict]) -> Tuple[List[Dict], List[str]]:
        """Genera dataset de entrenamiento desde datos crudos (JSON).
        
        Args:
            invoices_data: Lista de diccionarios con datos de facturas.
            
        Returns:
            Tuple con (X como lista de dicts, y como lista de strings).
        """
        # Convertir a DataFrame
        df = pd.DataFrame(invoices_data)
        
        # Convertir fechas
        date_cols = ['invoice_date', 'invoice_date_due', 'payment_dates']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col])
        
        # Generar dataset
        X, y = self.generate_training_dataset(df)
        
        # Convertir a formato JSON-serializable
        X_list = X.to_dict(orient='records')
        y_list = y.tolist()
        
        return X_list, y_list
