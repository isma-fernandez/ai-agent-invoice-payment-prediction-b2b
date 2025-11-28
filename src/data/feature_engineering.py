import datetime
import pandas as pd

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
        # No es lo ideal pero no hay forma de sacarlo sin pagar
        self.manual_rates = {
            'COP': 0.00022
        }

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

    
    def process_raw_data(self):
        """
        Transforma los datos raw de Odoo en características derivadas
        """

    def _clean_raw_data(self, invoices_df: pd.DataFrame, partners_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Limpia los datos recibidos de la base de datos
        """

    def _clean_invoices(self, invoices_df: pd.DataFrame):
        ...

    def _clean_partners(self, partners_df: pd.DataFrame):
        ...

    def _odoo_missing_values_to_null(self, df):
        object_cols = df.select_dtypes(include='object').columns
        print(object_cols)
        df[object_cols] = (df[object_cols].replace({False: pd.NA, '' : pd.NA, '/' : pd.NA}))
        df[object_cols] = df[object_cols].applymap(lambda x: np.nan if x == [] else x)
        return df
    
    def _convert_to_datetime(df, columns):
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