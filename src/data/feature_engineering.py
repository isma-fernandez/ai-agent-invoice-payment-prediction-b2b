import pandas as pd
import numpy as np
from typing import Optional, Tuple

# TODO: Añadir ejemplos de uso en docstrings

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
        'amount_total_eur', 'term_rounded', 'currency_name', 'company_name', 
        'partner_name', 'due_last_three_days_month', 'due_date_second_half_month',
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


    def generate_full_client_data(self, invoices_df: pd.DataFrame) -> pd.DataFrame:
        """Genera un dataset con toda la información del cliente y sus facturas.
        
        Incluye todas las features calculadas sin eliminar ninguna columna.
        # TODO: Debe revisarse si es necesario para el agente o no.
        
        Acciones principales:
            1. Añade características de pago.
            2. Añade características basadas en fecha.
            3. Calcula características históricas para cada factura.
            4. Añade columnas de target para análisis (paid_late, payment_overdue_category).

        Args:
            invoices_df (pd.DataFrame): DataFrame con facturas limpias (de DataCleaner).
            
        Returns:
            pd.DataFrame: DataFrame con todas las columnas originales + features calculadas.
        """
        df = invoices_df.copy()
        
        # Separar pagadas e impagadas
        paid_df = df[df['payment_state'] == 'paid'].copy()
        unpaid_df = df[df['payment_state'] == 'not_paid'].copy()
        
        # Añadir características de pago a las pagadas
        if len(paid_df) > 0:
            paid_df = self._add_payment_features(paid_df)
        
        # Añadir term_rounded a las impagadas (sin payment_overdue_days)
        if len(unpaid_df) > 0:
            unpaid_df = self._add_payment_features(unpaid_df, calculate_overdue=False)
        
        # Juntar todo
        df = pd.concat([paid_df, unpaid_df], ignore_index=True)
        
        # Añadir características basadas en invoice_date
        df = self._add_date_features(df)
        
        # Inicializar y calcular características basadas en el historial del cliente
        df = self._init_historical_features(df)
        df = df.sort_values(by='invoice_date', ascending=True).reset_index(drop=True)
        
        # Calcular historial para cada factura
        for idx in range(len(df)):
            invoice_date = df.loc[idx, 'invoice_date']
            partner_id = df.loc[idx, 'partner_id']

            # Facturas previas pagadas 
            prior_paid = paid_df[
                (paid_df['partner_id'] == partner_id) & 
                (paid_df['invoice_date'] < invoice_date)
            ]
            
            # Facturas previas pendientes
            outstanding = unpaid_df[
                (unpaid_df['partner_id'] == partner_id) & 
                (unpaid_df['invoice_date'] < invoice_date)
            ]
            
            self._update_prior_invoices_features(df, idx, prior_paid)
            self._update_outstanding_features(df, idx, outstanding)
        
        # Añadir columna paid_late para las pagadas
        if 'payment_overdue_days' in df.columns:
            df['paid_late'] = df['payment_overdue_days'] > 0
        
        # Añadir categoría de retraso para las pagadas
        df = self._assign_delay_categories(df)
        
        return df.sort_values(by='invoice_date', ascending=False).reset_index(drop=True)


    def generate_training_dataset(self, invoices_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Genera el dataset para entrenar el modelo con el formato requerido.
        
        Proceso:
            1. Filtra solo facturas pagadas antes de cutoff_date.
            2. Elimina outliers y facturas no útiles.
            3. Calcula features históricas.
            4. Divide en X e y.
        
        Args:
            invoices_df (pd.DataFrame): DataFrame con facturas limpias (de DataCleaner).
            
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
        paid_df = self._add_payment_features(paid_df)
        
        # Eliminar outliers en días de retraso
        delay_threshold = paid_df['payment_overdue_days'].quantile(self.outlier_percentile)
        paid_df = paid_df[paid_df['payment_overdue_days'] <= delay_threshold]
        
        # Asignar categorías (target)
        paid_df = self._assign_delay_categories(paid_df)
        
        # Añadir características basadas en invoice_date
        paid_df = self._add_date_features(paid_df)
        
        # Inicializar y calcular características históricas
        paid_df = self._init_historical_features(paid_df)
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
        feature_cols = [f for f in self.MODEL_FEATURES if f != 'partner_name'] + ['partner_freq']
        
        X = paid_df[feature_cols].copy()
        y = paid_df['payment_overdue_category'].copy()
        
        return X, y

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
        
        # Añadir term_rounded (sin payment_overdue_days porque no tiene sentido)
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


    def _calculate_historical_features_for_invoice(self, df: pd.DataFrame, idx: int,
        paid_invoices_df: pd.DataFrame, unpaid_invoices_df: pd.DataFrame) -> None:
        """Calcula características históricas para una factura específica.

        Args:
            df (pd.DataFrame): DataFrame principal donde se actualizarán los datos.
            idx (int): Índice de la factura actual en el DataFrame.
            paid_invoices_df (pd.DataFrame): Historial de facturas pagadas.
            unpaid_invoices_df (pd.DataFrame): Historial de facturas impagadas.
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
        
        self._update_prior_invoices_features(df, idx, prior_invoices)
        self._update_outstanding_features(df, idx, outstanding_invoices)


    def _add_payment_features(self, df: pd.DataFrame, 
                              calculate_overdue: bool = True) -> pd.DataFrame:
        """Añade características de pago: payment_overdue_days, term_rounded.

        Args:
            df (pd.DataFrame): DataFrame a procesar.
            calculate_overdue (bool, optional): Si True, calcula días de retraso. Defaults to True.

        Returns:
            pd.DataFrame: DataFrame con las nuevas columnas.
        """
        df = df.copy()
        
        if calculate_overdue and 'payment_dates' in df.columns:
            has_payment = df['payment_dates'].notna()
            df.loc[has_payment, 'payment_overdue_days'] = (
                df.loc[has_payment, 'payment_dates'] - df.loc[has_payment, 'invoice_date_due']
            ).dt.days
        
        df['payment_term_in_days'] = (df['invoice_date_due'] - df['invoice_date']).dt.days
        df['term_rounded'] = df['payment_term_in_days'].apply(self._map_days_to_term)
        df = df.drop(columns=['payment_term_in_days'])
        
        return df


    def _add_date_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Añade características de fecha.
        
        Añade: due_last_three_days_month, due_date_second_half_month.

        Args:
            df (pd.DataFrame): DataFrame a procesar.

        Returns:
            pd.DataFrame: DataFrame con las nuevas columnas booleanas.
        """
        df = df.copy()
        df['due_last_three_days_month'] = df['invoice_date_due'].apply(self._is_last_three_days)
        df['due_date_second_half_month'] = df['invoice_date_due'].dt.day > 15
        return df


    def _init_historical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Inicializa las columnas de características históricas a 0.

        Args:
            df (pd.DataFrame): DataFrame a inicializar.

        Returns:
            pd.DataFrame: DataFrame con columnas históricas en 0.0.
        """
        df = df.copy()
        df[self.HISTORICAL_FEATURES] = 0.0
        return df


    def _update_prior_invoices_features(self, df: pd.DataFrame, idx: int, 
                                        prior_invoices: pd.DataFrame) -> None:
        """Calcula las características relacionadas con facturas previas pagadas.
        
        Actualiza el DataFrame 'df' in-place en la posición 'idx'.

        Args:
            df (pd.DataFrame): DataFrame principal.
            idx (int): Índice de la fila a actualizar.
            prior_invoices (pd.DataFrame): Subset de facturas previas pagadas.
        """
        if len(prior_invoices) == 0:
            return
            
        late_prior = prior_invoices[prior_invoices['payment_overdue_days'] > 0]
        
        df.loc[idx, 'avg_invoiced_prior'] = prior_invoices['amount_total_eur'].mean()
        df.loc[idx, 'num_prior_invoices'] = len(prior_invoices)
        df.loc[idx, 'total_invoice_amount_prior'] = prior_invoices['amount_total_eur'].sum()
        df.loc[idx, 'avg_delay_prior_all'] = prior_invoices['payment_overdue_days'].mean()
        df.loc[idx, 'avg_payment_term_prior_invoices'] = prior_invoices['term_rounded'].mean()
        
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

        Args:
            df (pd.DataFrame): DataFrame principal.
            idx (int): Índice de la fila a actualizar.
            outstanding_invoices (pd.DataFrame): Subset de facturas pendientes.
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


    def _assign_delay_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        """Asigna categorías de retraso basadas en payment_overdue_days.

        Args:
            df (pd.DataFrame): DataFrame con columna 'payment_overdue_days'.

        Returns:
            pd.DataFrame: DataFrame con columna 'payment_overdue_category'.
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

        Args:
            days (float): Número de días de retraso.

        Returns:
            str: Categoría ('Puntual', 'Leve', 'Grave') o None.
        """
        if pd.isna(days):
            return None
        if days <= 0:
            return 'Puntual'
        elif 1 <= days <= 30:
            return 'Leve'
        else:
            return 'Grave'


    def _is_last_three_days(self, date) -> bool:
        """Determina si la fecha está en los últimos 3 días del mes.

        Args:
            date (pd.Timestamp): Fecha a evaluar.

        Returns:
            bool: True si es uno de los últimos 3 días del mes.
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

        Args:
            days (int): Días de término de pago.

        Returns:
            int: Categoría redondeada (0, 30, 45, 60, 90, 120).
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