import pandas as pd
import numpy as np
from typing import Tuple

RATES = {
    'MXN': 0.048, 
    'USD': 0.92,   
    'SEK': 0.087, 
    'COP': 0.00022, 
    'GBP': 1.17,    
}


class DataCleaner:
    """Clase para la limpieza y transformación inicial de los datos de Odoo.

    Prepara los datos para que puedan ser utilizados por el Feature Engineering. 
    Limpia TODAS las facturas (tanto pagadas como impagadas).

    Attributes:
        clients_to_exclude (str): Nombre o patrón de clientes a excluir (ej. "Marketplace").
        partial_to_paid_threshold (float): Valor residual máximo para considerar una factura pagada.
    """

    def __init__(self):
        # Clientes a excluir
        self.clients_to_exclude = "Marketplace"

        # Configuración para limpieza de estados de pago
        self.partial_to_paid_threshold = 0.5

        # TODO: buscar una forma de actualizar estas tasas dinámicamente
        self._currency_rates = RATES


    def clean_raw_data(self, invoices_df: pd.DataFrame, 
                       partners_df: pd.DataFrame = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Limpia los datos recibidos de la base de datos.

        Puede utilizarse para limpiar las facturas de un solo cliente o de todos los clientes.

        Args:
            invoices_df (pd.DataFrame): DataFrame con los datos de las facturas de Odoo.
            partners_df (pd.DataFrame, optional): DataFrame con los datos de los partners de Odoo.

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: Tupla con DataFrames limpios de facturas y partners.
        """
        invoices_cleaned = self._clean_invoices(invoices_df=invoices_df)
        partners_cleaned = self._clean_partners(partners_df=partners_df, invoices_df=invoices_cleaned)

        return invoices_cleaned, partners_cleaned


    def _clean_invoices(self, invoices_df: pd.DataFrame) -> pd.DataFrame:
        """Limpia los datos de facturas.

        Pasos realizados:
            1. Convierte datos faltantes de Odoo a NaN.
            2. Separa campos *_id en dos columnas (id y name).
            3. Limpia estados de pago (paid, partial, not_paid).
            4. Elimina facturas con amount_total == 0.
            5. Convierte amount_total y amount_residual a EUR.
            6. Limpia y procesa fechas de pago, convierte a datetime y elimina filas sin fecha.
            7. Elimina facturas de marketplace.

        Args:
            invoices_df (pd.DataFrame): DataFrame con los datos de las facturas de Odoo.

        Returns:
            pd.DataFrame: DataFrame limpio de facturas.
        """
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
        # NO hacer dropna de payment_dates, las impagadas no tienen fecha de pago

        # Convertir columnas de fecha a datetime y eliminar filas sin fecha
        date_cols = df.columns[
            df.columns.str.contains('date') & ~df.columns.str.contains('payment_dates')
        ].tolist()
        df = self._convert_to_datetime(df, date_cols)
        df = df.dropna(subset=['invoice_date', 'invoice_date_due'])

        # Eliminar facturas de marketplace (no aportan información relevante)
        df = df[~df['partner_name'].str.contains(self.clients_to_exclude, na=False)]

        return df.reset_index(drop=True)


    def _clean_partners(self, partners_df: pd.DataFrame, 
                        invoices_df: pd.DataFrame = None) -> pd.DataFrame:
        """Limpia los datos de partners.

        Pasos realizados:
            1. Convierte datos faltantes de Odoo a NaN.
            2. Solo conserva clientes que son empresas.
            3. Separa campos *_id en dos columnas (id y name).
            4. Rellena invoices_ids y columnas derivadas.

        Args:
            partners_df (pd.DataFrame): DataFrame con los datos de los partners de Odoo.
            invoices_df (pd.DataFrame, optional): DataFrame con los datos de las facturas.

        Returns:
            pd.DataFrame: DataFrame limpio de partners.
        """
        df = partners_df.copy()

        # Convertir datos faltantes de Odoo a NaN
        df = self._odoo_missing_values_to_null(df)

        # Solo conservar clientes que son empresas
        df = df[df['company_type'] == 'company']
        df = df.drop(columns=['company_type'], errors='ignore')

        # Extraer datos de columnas *_id
        df = self._split_id_name_fields(df)
        df = df.drop(columns=['country_id'], errors='ignore')

        # Actualizar invoices_ids y columnas derivadas
        if invoices_df is not None:
            df = self._fill_invoice_info(partners_df=df, invoices_df=invoices_df)

        return df.reset_index(drop=True)


    def _fill_invoice_info(self, partners_df: pd.DataFrame, 
                           invoices_df: pd.DataFrame) -> pd.DataFrame:
        """Rellena las columnas invoice_count, invoice_ids y total_invoiced_eur.

        Args:
            partners_df (pd.DataFrame): DataFrame con los datos de los partners.
            invoices_df (pd.DataFrame): DataFrame con los datos de las facturas.

        Returns:
            pd.DataFrame: DataFrame de partners con las columnas rellenadas.
        """
        df = partners_df.copy()
        invoice_counts = invoices_df.groupby('partner_id').size().to_dict()
        
        df['invoice_count'] = df['id'].map(invoice_counts).fillna(0).astype(int)
        
        invoice_ids_map = invoices_df.groupby('partner_id')['id'].apply(list).to_dict()
        df['invoice_ids'] = df['id'].map(invoice_ids_map).apply(lambda x: x if isinstance(x, list) else [])
        
        total_invoiced_map = invoices_df.groupby('partner_id')['amount_total_eur'].sum().to_dict()
        df['total_invoiced_eur'] = df['id'].map(total_invoiced_map).fillna(0)
        
        return df


    def _odoo_missing_values_to_null(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convierte los valores que Odoo usa para representar datos faltantes a NaN.
        
        Estos incluyen False, cadenas vacías, '/' (nombre de facturas) y listas vacías.

        Args:
            df (pd.DataFrame): DataFrame a limpiar.

        Returns:
            pd.DataFrame: DataFrame con valores faltantes convertidos a NaN.
        """
        df = df.copy()
        object_cols = df.select_dtypes(include='object').columns
        
        df[object_cols] = df[object_cols].replace({False: np.nan, '': np.nan, '/': np.nan})
        
        for col in object_cols:
            df[col] = df[col].apply(lambda x: np.nan if isinstance(x, list) and len(x) == 0 else x)
        
        return df


    def _convert_to_datetime(self, df: pd.DataFrame, columns: list) -> pd.DataFrame:
        """Convierte las columnas especificadas a tipo datetime.
        
        Soporta formatos con '/' (dd/mm/yyyy) y otros formatos estándar.

        Args:
            df (pd.DataFrame): DataFrame a convertir.
            columns (list): Lista de nombres de columnas a convertir.

        Returns:
            pd.DataFrame: DataFrame con las columnas convertidas a datetime.
        """
        df = df.copy()
        for col in columns:
            if col not in df.columns:
                continue
            try:
                # Formato raro que usa la empresa
                if df[col].astype(str).str.contains('/').any():
                    df[col] = pd.to_datetime(df[col], errors='coerce', format='%d/%m/%Y')
                else:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
            except Exception as e:
                print(f"Error al convertir '{col}': {e}")
        return df


    def _split_id_name_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Encuentra campos que son tuplas (id, nombre) y los separa en dos columnas.

        Args:
            df (pd.DataFrame): DataFrame a procesar.

        Returns:
            pd.DataFrame: DataFrame con las columnas separadas.
        """
        df = df.copy()
        id_name_fields = df.columns[df.columns.str.endswith('_id')].tolist()
        
        for field in id_name_fields:
            base_name = field[:-3]
            
            df[base_name + '_name'] = df[field].apply(
                lambda x: x[1] if isinstance(x, (list, tuple)) and len(x) == 2 else np.nan
            )
            df[field] = df[field].apply(
                lambda x: x[0] if isinstance(x, (list, tuple)) and len(x) == 2 else np.nan
            )
            
        return df


    def _clean_payment_state(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia las facturas según su estado de pago.

        Acciones:
        - Elimina facturas 'reversed'.
        - Convierte 'in_payment' a 'paid'.
        - Convierte 'partial' a 'not_paid' o 'paid' (según el residual).

        Args:
            df (pd.DataFrame): DataFrame a procesar.

        Returns:
            pd.DataFrame: DataFrame con los estados de pago limpiados.
        """
        df = df.copy()

        df = df[df['payment_state'] != 'reversed']  
        df['payment_state'] = df['payment_state'].replace('in_payment', 'paid')
        df = self._fix_partial_to_paid_invoices(df)
        df['payment_state'] = df['payment_state'].replace('partial', 'not_paid')

        return df


    def _fix_partial_to_paid_invoices(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ajusta estado de pago de facturas parciales a pagadas si residual < umbral.

        Args:
            df (pd.DataFrame): DataFrame a procesar.

        Returns:
            pd.DataFrame: DataFrame con los estados de pago ajustados.
        """
        df = df.copy()
        mask = (df['payment_state'] == 'partial') & (df['amount_residual'] < self.partial_to_paid_threshold)
        df.loc[mask, 'payment_state'] = 'paid'
        return df


    def _convert_amounts_to_eur(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convierte los montos a EUR usando las tasas de cambio disponibles.

        Args:
            df (pd.DataFrame): DataFrame a procesar.

        Returns:
            pd.DataFrame: DataFrame con amount_total_eur y amount_residual_eur añadidas.
        """
        df = df.copy()
    
        df['amount_total_eur'] = df.apply(lambda row: self._convert_to_eur(row, 'amount_total'), axis=1)
        df['amount_residual_eur'] = df.apply(lambda row: self._convert_to_eur(row, 'amount_residual'), axis=1)
        
        return df

    def _convert_to_eur(self, row, amount_col):
        """Convierte un monto específico a EUR según la moneda indicada en la fila.

        Args:
            row (pd.Series): Fila del DataFrame.
            amount_col (str): Nombre de la columna con el monto a convertir.

        Returns:
            float: Monto convertido a EUR.
        """
        currency = row.get('currency_name', 'EUR')
        amount = row[amount_col]
        if currency != 'EUR' and currency in self._currency_rates:
            return amount * self._currency_rates[currency]
        return amount

    def _clean_payment_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia y procesa las fechas de pago.
        
        Acciones:
        - Elimina facturas 'paid' sin fecha.
        - Conserva solo la primera fecha si hay múltiples.
        - Convierte a datetime.

        Args:
            df (pd.DataFrame): DataFrame a procesar.

        Returns:
            pd.DataFrame: DataFrame con las fechas de pago limpiadas.
        """
        df = df.copy()
        
        paid_without_date = (df['payment_dates'].isna()) & (df['payment_state'] == 'paid')
        df = df[~paid_without_date]
        
        has_date = df['payment_dates'].notna()
        
        df.loc[has_date, 'payment_dates'] = (
            df.loc[has_date, 'payment_dates']
            .astype(str)
            .str.split(r",\s*")
            .str[0]
        )

        df['payment_dates'] = df['payment_dates'].replace('nan', np.nan)
        
        df = self._convert_to_datetime(df, ['payment_dates'])
        return df