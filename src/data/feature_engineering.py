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

        """# Clientes con países faltantes
        self.missing_country_mapping = {
            9308: "Spain",
            13304: "Mexico",
            14264: "France",
            12514: "Poland"
        }
        
        # Facturas parciales que realmente estan pagadas (residuales muy bajos)
        self.partial_to_paid_invoice_ids = [174403, 149233, 139026, 104262, 47707]
        
        """

        # Clientes duplicados
        self.duplicate_partner_ids = [731]

        # Clientes a excluir
        self.clients_to_exclude = ["Marketplace"]

        # % de facturas a eliminar según días de retraso
        self.outlier_percentile = 0.995

        # Facturas parciales que realmente estan pagadas (residuales muy bajos)
        self.partial_to_paid_invoice_ids = [174403, 149233, 139026, 104262, 47707]

        self.__currency_rates = {}

    def process_raw_data(self, invoices_df: pd.DataFrame, partners_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Transforma los datos raw de Odoo en características derivadas
        """
        

    def _clean_raw_data(self, invoices_df: pd.DataFrame, partners_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Limpia los datos recibidos de la base de datos
        """
        self.__currency_rates = self._get_currency_rates(invoices_df['currency_name'].unique().tolist())

        invoices_cleaned = self._clean_invoices(invoices_df=invoices_df)
        partners_cleaned = self._clean_partners(partners_df=partners_df)

        return invoices_cleaned, partners_cleaned

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


    def _clean_partners(self, partners_df: pd.DataFrame):
        ...

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
        # Convertir facturas parciales específicas a 'paid'
        df.loc[df['id'].isin(self.partial_to_paid_invoice_ids), 'payment_state'] = 'paid'
        # Convertir 'partial' restantes a 'not_paid'
        df['payment_state'] = df['payment_state'].replace('partial', 'not_paid')
        
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
            if currency != 'EUR':
                try:
                    rate = c.get_rate(currency, 'EUR')
                    rates[currency] = rate
                except Exception as e:
                    print(f"Error retrieving rate for {currency}: {e}")