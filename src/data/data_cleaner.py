import pandas as pd
import numpy as np
from forex_python.converter import CurrencyRates

class DataCleaner:
    """
    Clase cuya funcionalidad es la limpieza y transformación inicial de los datos de Odoo.
    Prepara los datos para que puedan ser utilizados por el Feature Engineering.
    """
    def __init__(self):
        # Clientes a excluir
        self.clients_to_exclude = "Marketplace"

        # Configuración para limpieza de estados de pago
        self.partial_to_paid_threshold = 0.5

        self._currency_rates = {}


    def clean_raw_data(self, invoices_df: pd.DataFrame, partners_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Limpia los datos recibidos de la base de datos
        """
        

        invoices_cleaned = self._clean_invoices(invoices_df=invoices_df)
        partners_cleaned = self._clean_partners(partners_df=partners_df, invoices_df=invoices_cleaned)

        return invoices_cleaned, partners_cleaned


    def _clean_invoices(self, invoices_df: pd.DataFrame):
        """
        Limpia los datos de facturas.
        """
        df = invoices_df.copy()

        # Convertir datos faltantes de Odoo a NaN
        df = self._odoo_missing_values_to_null(df)

        # Convertir campos *_id en dos columnas separadas
        df = self._split_id_name_fields(df)
        self._currency_rates = self._get_currency_rates(df['currency_name'].unique().tolist())

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
        df = df[~df['partner_name'].str.contains(self.clients_to_exclude)]

        return df.reset_index(drop=True)


    def _clean_partners(self, partners_df: pd.DataFrame, invoices_df: pd.DataFrame = None):
        """
        Limpia los datos de partners.
        """
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
        if invoices_df is not None:
            df = self._fill_invoice_info(partners_df=df, invoices_df=invoices_df)

        return df.reset_index(drop=True)


    def _fill_invoice_info(self, partners_df: pd.DataFrame, invoices_df: pd.DataFrame) -> pd.DataFrame:
        """
        Rellena las columnas invoice_count, invoice_ids y total_invoiced_eur en el dataframe de partners.
        """
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
        df[object_cols] = df[object_cols].map(lambda x: np.nan if x == [] else x)
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
        """
        Limpia las facturas según su estado de pago.
        """
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
        """
        Ajusta el estado de pago de facturas parciales a pagadas si el residual es menor que un umbral.
        """
        df = df.copy()
        df.loc[(df['payment_state'] == 'partial') & (df['amount_residual'] 
            < self.partial_to_paid_threshold), 'payment_state'] = 'paid'
        return df


    def _convert_amounts_to_eur(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convierte los montos a EUR usando las tasas de cambio disponibles.
        """
        df = df.copy()
    
        # Convertir amount_total a EUR
        df['amount_total_eur'] = df.apply(
            lambda row: row['amount_total'] * self._currency_rates.get(row['currency_name'], 1) 
            if row['currency_name'] != 'EUR' else row['amount_total'], axis=1
        )

        df['amount_residual_eur'] = df.apply(
            lambda row: row['amount_residual'] * self._currency_rates.get(row['currency_name'], 1) 
            if row['currency_name'] != 'EUR' else row['amount_residual'], axis=1
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