import pandas as pd
import numpy as np
from typing import Dict, List, Optional


class DataProcessor:
    """Convierte datos crudos (JSON) a formato DataFrame para el modelo."""
    # Campos necsarios para la factura a predecir
    REQUIRED_INVOICE_FIELDS = [
        'amount_total_eur',
        'invoice_date',
        'invoice_date_due',
        'currency_name',
        'company_name'
    ]
    # Campos necesarios para el historial del cliente
    REQUIRED_HISTORY_FIELDS = [
        'amount_total_eur',
        'invoice_date',
        'invoice_date_due',
        'payment_state'
    ]

    def process_invoice(self, invoice_data: Dict) -> pd.Series:
        """Convierte los datos de una factura a pd.Series.

        Args:
            invoice_data: Diccionario con los datos de la factura.

        Returns:
            pd.Series con los datos de la factura.
        """
        # Validar campos necesarios
        self._validate_fields(invoice_data, self.REQUIRED_INVOICE_FIELDS, "invoice")

        # Conversión de json a dataframe
        invoice = pd.Series({
            'id': invoice_data.get('id', -1),
            'name': invoice_data.get('name', 'invoice_to_predict'),
            'partner_id': invoice_data.get('partner_id'),
            'partner_name': invoice_data.get('partner_name', ''),
            'company_name': invoice_data.get('company_name', ''),
            'currency_name': invoice_data.get('currency_name', 'EUR'),
            'amount_total_eur': float(invoice_data['amount_total_eur']),
            'amount_residual_eur': float(invoice_data.get('amount_residual_eur', invoice_data['amount_total_eur'])),
            'invoice_date': pd.Timestamp(invoice_data['invoice_date']),
            'invoice_date_due': pd.Timestamp(invoice_data['invoice_date_due']),
            'payment_dates': pd.NaT,
            'payment_state': invoice_data.get('payment_state', 'not_paid'),
        })

        return invoice

    def process_client_history(self, history_data: List[Dict]) -> pd.DataFrame:
        """Convierte el historial del cliente a pd.DataFrame.

        Args:
            history_data: Lista de diccionarios con las facturas del cliente.

        Returns:
            pd.DataFrame con el historial del cliente.
        """
        if not history_data:
            return pd.DataFrame()

        for i, inv in enumerate(history_data):
            self._validate_fields(inv, self.REQUIRED_HISTORY_FIELDS, f"history[{i}]")

        df = pd.DataFrame(history_data)

        df['amount_total_eur'] = df['amount_total_eur'].astype(float)
        if 'amount_residual_eur' not in df.columns:
            df['amount_residual_eur'] = df.apply(
                lambda row: 0.0 if row['payment_state'] == 'paid' else row['amount_total_eur'],
                axis=1
            )
        else:
            df['amount_residual_eur'] = df['amount_residual_eur'].astype(float)

        # Convertir fechas
        df['invoice_date'] = pd.to_datetime(df['invoice_date'])
        df['invoice_date_due'] = pd.to_datetime(df['invoice_date_due'])
        if 'payment_date' in df.columns:
            df['payment_dates'] = pd.to_datetime(df['payment_date'], errors='coerce')
            df = df.drop(columns=['payment_date'])
        else:
            df['payment_dates'] = pd.NaT

        # Campos opcionales (para las facturas hipotéticas)
        if 'id' not in df.columns:
            df['id'] = range(len(df))
        if 'name' not in df.columns:
            df['name'] = [f'invoice_{i}' for i in range(len(df))]
        if 'partner_id' not in df.columns:
            df['partner_id'] = None
        if 'partner_name' not in df.columns:
            df['partner_name'] = ''
        if 'company_name' not in df.columns:
            df['company_name'] = ''
        if 'currency_name' not in df.columns:
            df['currency_name'] = 'EUR'

        return df

    def _validate_fields(self, data: Dict, required_fields: List[str], context: str) -> None:
        """Valida que los campos necesarios estén presentes.

        Args:
            data: Diccionario a validar.
            required_fields: Lista de campos necesarios.
            context: Contexto para el mensaje de error.

        Raises:
            ValueError: Si falta algún campo requerido.
        """
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise ValueError(f"Campos necesarios faltantes en {context}: {missing}")
