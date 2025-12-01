import datetime
import pandas as pd
import numpy as np
from forex_python.converter import CurrencyRates

class FeatureEngineering:
    """
    Clase cuya funcionalidad es la transformación de los datos de Odoo en 
    las características que necesita el modelo de predicción de impagos.
    Incluye la limpieza también
    """
    def __init__(self, cutoff_date: str = '2025-03-12'):
        # Al no ser una base de datos actual es necesario
        # en producción no haría falta (día de hoy serviría).
        self.cutoff_date = cutoff_date

        # Clientes duplicados
        self.duplicate_partner_ids = [731]

        # Clientes a excluir
        self.clients_to_exclude = ["Marketplace"]

        # % de facturas a eliminar según días de retraso
        self.outlier_percentile = 0.995
        self.partial_to_paid_threshold = 0.5

        self.__currency_rates = {}

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

        # Calcular días de retraso
        df['payment_overdue_days'] = (df['payment_dates'] - df['invoice_date_due']).dt.days

        # Eliminar outliers en días de retraso
        delay_threshold = df['payment_overdue_days'].quantile(self.outlier_percentile)
        df = df[df['payment_overdue_days'] <= delay_threshold]

        # Asigno categorias de retraso
        df = self._assign_delay_categories(df)

        # Calculo los términos de pago redondeados
        df['payment_term_in_days'] = (df['invoice_date_due'] - df['invoice_date']).dt.days
        df['term_rounded'] = df['payment_term_in_days'].apply(self._map_days_to_term)
        df = df.drop(columns=['payment_term_in_days'])

        return df.reset_index(drop=True)

    def generate_complete_dataset(self, paid_invoices_df: pd.DataFrame, unpaid_invoices_df: pd.DataFrame, 
                                  partners_df: pd.DataFrame) -> pd.DataFrame:
        """
        Genera el dataset completo uniendo facturas y partners, y crea las características históricas.
        """
        dataset = paid_invoices_df.copy()

        # Inicializar características históricas
        dataset = self._init_historical_features(dataset)

        # Calcular características históricas
        dataset = self._calculate_historical_features(dataset, unpaid_invoices_df)

        return dataset.reset_index(drop=True)
        





    def clean_raw_data(self, invoices_df: pd.DataFrame, partners_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Limpia los datos recibidos de la base de datos
        """
        self.__currency_rates = self._get_currency_rates(invoices_df['currency_name'].unique().tolist())

        invoices_cleaned = self._clean_invoices(invoices_df=invoices_df)
        partners_cleaned = self._clean_partners(partners_df=partners_df)

        return invoices_cleaned, partners_cleaned

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
            'avg_payment_term_prior_invoices', 'due_last_three_days_month', 'due_date_second_half_month'
        ]
        df[feature_cols] = 0.0
        df[['due_last_three_days_month', 'due_date_second_half_month']] = False

        return df


    def _calculate_historical_features(self, dataset: pd.DataFrame, unpaid_invoices_df: pd.DataFrame) -> pd.DataFrame:
        df = dataset.copy()
        df = df.sort_values(by='invoice_date', ascending=True).reset_index(drop=True)

        grouped_partner = df.groupby("partner_id")
        for index, row in df.iterrows():
            partner_id = row['partner_id']
            id = row['id']
            invoices_partner = grouped_partner.get_group(partner_id)
            prior_invoices_partner = invoices_partner[invoices_partner['invoice_date'] < row['invoice_date']]
            late_prior_invoices_partner = prior_invoices_partner[prior_invoices_partner['payment_overdue_days'] > 0]
            if len(prior_invoices_partner) > 0:
                df.loc[df["id"] == id, 'avg_invoiced_prior'] = prior_invoices_partner['amount_total_eur'].mean()
                df.loc[df["id"] == id, 'num_prior_invoices'] = len(prior_invoices_partner)
                df.loc[df["id"] == id, 'total_invoice_amount_prior'] = prior_invoices_partner['amount_total_eur'].sum()
                if len(late_prior_invoices_partner) > 0:
                    df.loc[df["id"] == id, 'num_late_prior_invoices'] = len(late_prior_invoices_partner)
                    df.loc[df["id"] == id, 'ratio_late_prior_invoices'] = (
                        len(late_prior_invoices_partner) / len(prior_invoices_partner)
                    )
                    df.loc[df["id"] == id, 'total_invoice_amount_late_prior'] = late_prior_invoices_partner['amount_total_eur'].sum()
                    df.loc[df["id"] == id, 'ratio_invoice_amount_late_prior'] = (
                        late_prior_invoices_partner['amount_total_eur'].sum() / prior_invoices_partner['amount_total_eur'].sum()
                    )
                    df.loc[df["id"] == id, 'avg_delay_prior_late_invoices'] = late_prior_invoices_partner['payment_overdue_days'].mean()
                    df.loc[df["id"] == id, 'avg_delay_prior_all'] = prior_invoices_partner['payment_overdue_days'].mean()
                    due_day = row['invoice_date_due'].day
                    month = row['invoice_date_due'].month
                    year = row['invoice_date_due'].year
                    # sumo 1 mes, resto un dia y obtengo el ultimo dia del mes original
                    days_in_month = (pd.Timestamp(year, month % 12 + 1, 1) - pd.Timedelta(days=1)).day 
                    if due_day > days_in_month - 3:
                        dataset.loc[dataset["id"] == id, 'due_last_three_days_month'] = True
                    if due_day > 15:
                        df.loc[df["id"] == id, 'due_date_second_half_month'] = True
                    df.loc[df["id"] == id, 'avg_payment_term_prior_invoices'] = prior_invoices_partner['term'].mean()
            outstanding_invoices_partner = (unpaid_invoices_df[(unpaid_invoices_df['partner_id'] == partner_id) 
                                                & (unpaid_invoices_df['invoice_date'] < row['invoice_date'])])
            if len(outstanding_invoices_partner) > 0:
                df.loc[df["id"] == id, 'num_outstanding_invoices'] = len(outstanding_invoices_partner)
                late_outstanding_invoices_partner = (outstanding_invoices_partner[
                    outstanding_invoices_partner['invoice_date_due'] < pd.Timestamp(2025, 3, 12)
                    ])
                if len(late_outstanding_invoices_partner) > 0:
                    df.loc[df["id"] == id, 'num_outstanding_invoices_late'] = len(late_outstanding_invoices_partner)
                    df.loc[df["id"] == id, 'ratio_outstanding_invoices_late'] = (
                        len(late_outstanding_invoices_partner) / len(outstanding_invoices_partner)
                    )
                    df.loc[df["id"] == id, 'total_invoice_amount_outstanding'] = (
                        outstanding_invoices_partner['amount_total_eur'].sum()
                    )
                    df.loc[df["id"] == id, 'total_invoice_amount_outstanding_late'] = (
                        late_outstanding_invoices_partner['amount_total_eur'].sum()
                    )
                    df.loc[df["id"] == id, 'ratio_invoice_amount_outstanding_late'] = (
                        late_outstanding_invoices_partner['amount_total_eur'].sum() / outstanding_invoices_partner['amount_total_eur'].sum()
                    )
        df['paid_late'] = df['payment_overdue_days'] > 0
        return df
    def _clean_invoices(self, invoices_df: pd.DataFrame):
        df = invoices_df.copy()

        # Convertir datos faltantes de Odoo a NaN
        df = self._odoo_missing_values_to_null(df)

        # Convertir campos *_id en dos columnas separadas
        df = self._split_id_name_fields(df)

        # Procesar estados de pago
        df = self._clean_payment_state(df)

        # Eliminar facturas con amount_total == 0
        df = df[df['amount_total'] != 0]

        # Drop filas sin nombre de factura / partner
        df = df.dropna(subset=['name', 'partner_name'])

        # Convertir amount_total a EUR
        df = self._convert_amounts_to_eur(df)

        # Limpiar y procesar fechas de pago
        df = self._clean_payment_dates(df)
        df = df.dropna(subset=['payment_dates'])

        # Convertir columnas de fecha a datetime y eliminar filas sin fecha
        df = self._convert_to_datetime(df, df.columns[df.columns.str.contains('date') & ~df.columns.str.contains('payment_dates')].tolist())
        df = df.dropna(subset=['invoice_date', 'invoice_date_due', 'payment_dates'])

        # Eliminar facturas de marketplace (no aportan información relevante)
        df = df[~df['partner_name'].isin(self.clients_to_exclude)]

        return df.reset_index(drop=True)

    def _clean_partners(self, partners_df: pd.DataFrame, invoices_df: pd.DataFrame = None):
        df = partners_df.copy()

        # Convertir datos faltantes de Odoo a NaN
        df = self._odoo_missing_values_to_null(df)

        # Solo conservar clientes que son empresas
        df = df[df['company_type'] == 'company']
        df = df.drop(columns=['company_type'])

        # Extraer datos de columnas *_id
        df = self._split_id_name_fields(df)
        df = df.drop(columns=['country_id'])

        # Actualizar invoices_ids y columnas derivadas
        if invoices_df:
            df = self._fill_invoice_info(partners_df=df, invoices_df=invoices_df)

        return df.reset_index(drop=True)

    def _map_days_to_term(self, days: int) -> str:
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
            return ">90"

    def _assign_delay_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['payment_overdue_category'] = df['payment_overdue_days'].apply(self._categorize_delay)
        return df
    
    def _categorize_delay(self, days: int) -> str:
        if days <= 0:
            return 'Puntual'
        elif 1 <= days <= 30:
            return 'Leve'
        else:
            return 'Grave'

    def _fill_invoice_info(self, partners_df: pd.DataFrame, invoices_df: pd.DataFrame) -> pd.DataFrame:
        df = partners_df.copy()
        invoice_counts = invoices_df.groupby('partner_id').size().to_dict()
        # Relleno de invoice_count
        df['invoice_count'] = df['id'].map(invoice_counts).fillna(0).astype(int)
        # Relleno de invoice_ids
        df['invoice_ids'] = df['id'].map(
            lambda id: invoices_df[invoices_df['partner_id'] == id]['id'].tolist()
        )
        # Relleno de total_invoiced_eur
        df['total_invoiced_eur'] = df['id'].map(
            lambda id: invoices_df[invoices_df['partner_id'] == id]['amount_total_eur'].sum()
        )
        
        return df
    
    def _odoo_missing_values_to_null(self, df):
        """
        Convierte los valores que Odoo usa para representar datos faltantes a NaN.
        """
        object_cols = df.select_dtypes(include='object').columns
        print(object_cols)
        df[object_cols] = (df[object_cols].replace({False: pd.NA, '' : pd.NA, '/' : pd.NA}))
        df[object_cols] = df[object_cols].applymap(lambda x: np.nan if x == [] else x)
        return df
    
    def _convert_to_datetime(self, df, columns):
        """
        Convierte las columnas especificadas a tipo datetime.
        """
        for col in columns:
            try:
                # formato que no soporta nativamente to_datetime
                if df[col].astype(str).str.contains('/').any():
                    df[col] = pd.to_datetime(df[col], errors='coerce', format='%d/%m/%Y')
                else:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            except Exception as e:
                print(f"Error al convertir '{col}': {e}")
        return df
    

    def _split_id_name_fields(self, df):
        """
        Encuentra campos que son tuplas (id, nombre) y los separa en dos columnas.
        """
        id_name_fields = df.columns[df.columns.str.endswith('_id')].tolist()
        for field in id_name_fields:
            df[field[:-3] + '_id'] = df[field].apply(lambda x: x[0] if isinstance(x, list) and len(x) == 2 else np.nan)
            df[field[:-3] + '_name'] = df[field].apply(lambda x: x[1] if isinstance(x, list) and len(x) == 2 else np.nan)
            df = df.drop(columns=[field])
        return df
    
    def _clean_payment_state(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # Elimina facturas revertidas
        df = df[df['payment_state'] != 'reversed']  

        # Convertir 'in_payment' a 'paid'
        df['payment_state'] = df['payment_state'].replace('in_payment', 'paid')

        # Convertir facturas parciales específicas a 'paid' y eliminar 'partial' restantes
        df = self._fix_partial_to_paid_invoices(df)
        df = df.drop(columns=['amount_residual'])

        # Convertir 'partial' restantes a 'not_paid'
        df['payment_state'] = df['payment_state'].replace('partial', 'not_paid')
        
        return df
    
    def _fix_partial_to_paid_invoices(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.loc[(df['payment_state'] == 'partial') & (df['amount_residual'] 
            < self.partial_to_paid_threshold), 'payment_state'] = 'paid'
        return df
        

    def _convert_amounts_to_eur(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Convertir amount_total a EUR
        df['amount_total_eur'] = df.apply(
            lambda row: row['amount_total'] * self.__currency_rates.get(row['currency_name'], 1) 
            if row['currency_name'] != 'EUR' else row['amount_total'], axis=1
        )
        
        return df
    
    def _get_currency_rates(self, currencies_df: list) -> dict:
        """
        Obtiene las tasas de conversión a EUR para las monedas especificadas.
        """
        c = CurrencyRates()

        rates = {}
        rates['COP'] = 0.00022  # Valor fijo temporal
        for currency in currencies_df:
            if currency != 'EUR' and currency not in rates:
                try:
                    rate = c.get_rate(currency, 'EUR')
                    rates[currency] = rate
                except Exception as e:
                    print(f"Error retrieving rate for {currency}: {e}")
                    raise e
        return rates
    
    def _clean_payment_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Limpia y procesa las fechas de pago.
        """
        df = df.copy()
        
        # Eliminar facturas pagadas sin fecha de pago
        paid_without_date = (df['payment_dates'].isna()) & (df['payment_state'] == 'paid')
        df = df[~paid_without_date]
        
        # En el caso de múltiples fechas quedarse con la primera
        df['payment_dates'] = df['payment_dates'].astype(str).str.split(r",\s*").str[0]
        df['payment_dates'] = df['payment_dates'].replace('nan', pd.NA)
        
        df = self._convert_to_datetime(df, ['payment_dates'])
        return df