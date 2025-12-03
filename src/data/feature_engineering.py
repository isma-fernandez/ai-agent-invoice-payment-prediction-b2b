import datetime
import pandas as pd
import numpy as np

class FeatureEngineering:
    """
    Clase cuya funcionalidad es la transformación de los datos limpios de Odoo en 
    las características que necesita el modelo de predicción de impagos.
    """
    def __init__(self, cutoff_date: str = '2025-03-12'):
        # Al no ser una base de datos actual es necesario
        # en producción no haría falta (día de hoy serviría).
        self.cutoff_date = pd.Timestamp(cutoff_date)

        # % de facturas a eliminar según días de retraso
        self.outlier_percentile = 0.995


    def add_payment_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Añade características de pago: payment_overdue_days, term_rounded.
        """
        df = df.copy()
        
        # Calcular días de retraso (solo para facturas con payment_dates)
        has_payment = df['payment_dates'].notna()
        df.loc[has_payment, 'payment_overdue_days'] = (
            df.loc[has_payment, 'payment_dates'] - df.loc[has_payment, 'invoice_date_due']
        ).dt.days
        
        # Calculo los términos de pago redondeados
        # Redondeadas porque los días suelen ser muy específicos (33, 37, 22, etc)
        # es estúpido por parte de la empresa honestamente (borrar)
        df['payment_term_in_days'] = (df['invoice_date_due'] - df['invoice_date']).dt.days
        df['term_rounded'] = df['payment_term_in_days'].apply(self._map_days_to_term)
        df = df.drop(columns=['payment_term_in_days'])
        
        return df


    def add_date_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Añade features de fecha: due_last_three_days_month, due_date_second_half_month.
        """
        df = df.copy()
        
        df['due_last_three_days_month'] = df['invoice_date_due'].apply(self._is_last_three_days)
        df['due_date_second_half_month'] = df['invoice_date_due'].dt.day > 15
        
        return df


    def calculate_historical_features_for_invoice(self, df: pd.DataFrame, idx: int,
        paid_invoices_df: pd.DataFrame, unpaid_invoices_df: pd.DataFrame) -> None:
        """
        Calcula features históricas para una factura.
        """
        row = df.loc[idx]
        partner_id = row['partner_id']
        invoice_date = row['invoice_date']
        
        # Facturas previas pagadas del cliente
        prior_invoices = paid_invoices_df[
            (paid_invoices_df['partner_id'] == partner_id) & 
            (paid_invoices_df['invoice_date'] < invoice_date)
        ]
        
        # Facturas pendientes del cliente
        outstanding_invoices = unpaid_invoices_df[
            (unpaid_invoices_df['partner_id'] == partner_id) & 
            (unpaid_invoices_df['invoice_date'] < invoice_date)
        ]
        
        # Generar características
        self._update_prior_invoices_features(df, idx, prior_invoices)
        self._update_outstanding_features(df, idx, outstanding_invoices)


    def _update_prior_invoices_features(self, df: pd.DataFrame, idx: int, 
                                        prior_invoices: pd.DataFrame) -> None:
        """
        Calcula las características relacionadas con facturas previas.
        """
        # Si hay facturas previas
        if len(prior_invoices) > 0:
            late_prior = prior_invoices[prior_invoices['payment_overdue_days'] > 0]
            
            df.loc[idx, 'avg_invoiced_prior'] = prior_invoices['amount_total_eur'].mean()
            df.loc[idx, 'num_prior_invoices'] = len(prior_invoices)
            df.loc[idx, 'total_invoice_amount_prior'] = prior_invoices['amount_total_eur'].sum()
            df.loc[idx, 'avg_delay_prior_all'] = prior_invoices['payment_overdue_days'].mean()
            df.loc[idx, 'avg_payment_term_prior_invoices'] = prior_invoices['term_rounded'].mean()
            
            # Si hay facturas previas pagadas con retraso
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
        """
        Calcula las características relacionadas con facturas pendientes.
        """
        # Si hay facturas pendientes
        if len(outstanding_invoices) > 0:
            df.loc[idx, 'num_outstanding_invoices'] = len(outstanding_invoices)
            df.loc[idx, 'total_invoice_amount_outstanding'] = outstanding_invoices['amount_total_eur'].sum()
            
            late_outstanding = outstanding_invoices[
                outstanding_invoices['invoice_date_due'] < self.cutoff_date
            ]
            
            # Si hay facturas vencidas pendientes
            if len(late_outstanding) > 0:
                df.loc[idx, 'num_outstanding_invoices_late'] = len(late_outstanding)
                df.loc[idx, 'ratio_outstanding_invoices_late'] = len(late_outstanding) / len(outstanding_invoices)
                df.loc[idx, 'total_invoice_amount_outstanding_late'] = late_outstanding['amount_total_eur'].sum()
                df.loc[idx, 'ratio_invoice_amount_outstanding_late'] = (
                    late_outstanding['amount_total_eur'].sum() / outstanding_invoices['amount_total_eur'].sum()
                )



    # ------- PROCESADO DE DATOS PARA ENTRENAMIENTO DEL MODELO -------

    def process_invoice_data_for_model(self, invoices_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforma los datos limpios en las características que necesita el modelo.
        """
        df = invoices_df.copy()
        
        # Eliminar facturas posteriores a la fecha de corte o no pagadas
        df = df[df['payment_dates'] <= self.cutoff_date]

        # Me quedo solo con las facturas pagadas
        df = df[df['payment_state'] == 'paid'].copy()

        # Eliminar facturas con fecha de vencimiento igual a fecha de factura y fecha de pago
        df = df[df['invoice_date_due'] != df['invoice_date']]
        df = df[df['payment_dates'] != df['invoice_date']]

        # Calcular métricas de pago (payment_overdue_days, term_rounded)
        df = self.add_payment_features(df)

        # Eliminar outliers en días de retraso
        delay_threshold = df['payment_overdue_days'].quantile(self.outlier_percentile)
        df = df[df['payment_overdue_days'] <= delay_threshold]

        # Asigno categorias de retraso
        df = self._assign_delay_categories(df)

        return df.reset_index(drop=True)


    def generate_complete_dataset(self, paid_invoices_df: pd.DataFrame, 
                                  unpaid_invoices_df: pd.DataFrame) -> pd.DataFrame:
        """
        Genera el dataset completo uniendo facturas y partners, y crea las características históricas.
        """
        dataset = paid_invoices_df.copy()

        # Añadir features de fecha de vencimiento
        dataset = self.add_date_features(dataset)

        # Inicializar características históricas
        dataset = self._init_historical_features(dataset)

        # Calcular características históricas
        dataset = self._calculate_historical_features(dataset, unpaid_invoices_df)

        return dataset.reset_index(drop=True)


    def _init_historical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Inicializa las columnas de características históricas.
        """
        df = df.copy()

        feature_cols = [
            'avg_invoiced_prior', 'num_prior_invoices', 'num_late_prior_invoices', 
            'ratio_late_prior_invoices', 'total_invoice_amount_prior', 
            'total_invoice_amount_late_prior', 'ratio_invoice_amount_late_prior',
            'avg_delay_prior_late_invoices', 'avg_delay_prior_all', 
            'num_outstanding_invoices', 'num_outstanding_invoices_late',
            'ratio_outstanding_invoices_late', 'total_invoice_amount_outstanding', 
            'total_invoice_amount_outstanding_late', 'ratio_invoice_amount_outstanding_late',
            'avg_payment_term_prior_invoices'
        ]
        df[feature_cols] = 0.0

        return df
    

    def _calculate_historical_features(self, dataset: pd.DataFrame, 
                                       unpaid_invoices_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula las características históricas para cada factura en el dataset.
        """
        df = dataset.copy()
        df = df.sort_values(by='invoice_date', ascending=True).reset_index(drop=True)

        for idx, row in df.iterrows():
            self.calculate_historical_features_for_invoice(
                df=df,
                idx=idx,
                paid_invoices_df=df.iloc[:idx],
                unpaid_invoices_df=unpaid_invoices_df
            )

        df['paid_late'] = df['payment_overdue_days'] > 0
            
        return df


    # -------- MÉTODOS AUXILIARES ---------


    def _is_last_three_days(self, date) -> bool:
        """
        Determina si la fecha está en los últimos 3 días del mes.
        """
        if pd.isna(date):
            return False
        month = date.month
        year = date.year
        # sumo 1 mes, resto un dia y obtengo el ultimo dia del mes original
        if month == 12:
            days_in_month = 31
        else:
            days_in_month = (pd.Timestamp(year, month + 1, 1) - pd.Timedelta(days=1)).day
        return date.day > days_in_month - 3


    def _map_days_to_term(self, days: int) -> int:
        """
        Mapea los días de término de pago a categorías redondeadas.
        """
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


    def _assign_delay_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Asigna categorías de retraso basadas en los días de retraso en el pago.
        """
        df = df.copy()
        df['payment_overdue_category'] = df['payment_overdue_days'].apply(self._categorize_delay)
        return df
    

    def _categorize_delay(self, days: int) -> str:
        """
        Mapea los días de retraso a categorías.
        """
        if days <= 0:
            return 'Puntual'
        elif 1 <= days <= 30:
            return 'Leve'
        else:
            return 'Grave'