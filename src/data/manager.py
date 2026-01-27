import pandas as pd
from typing import Optional, Dict, List, Any
import joblib

from src.utils.odoo_connector import OdooConnection
from .retriever import DataRetriever
from .cleaner import DataCleaner
from .models import (
    ClientSearchResult, ClientInfo, InvoiceSummary,
    PredictionResult, RiskCategory, PaymentState,
    AgingReport, PortfolioSummary, ClientTrend,
    DeterioratingClient, AgingBucket
)


class DataManager:
    """
    Centraliza la gestión de datos para el proyecto de predicción de pagos de facturas.

    IMPORTANTE - Convenciones de campos de importe:
    - amount_total_eur: Importe TOTAL de la factura (para estadísticas históricas)
    - amount_residual_eur: Importe PENDIENTE de pago (para deuda actual)

    Para calcular deuda vencida/pendiente SIEMPRE usar amount_residual_eur.
    """

    LABEL_MAPPING = {0: 'Grave', 1: 'Leve', 2: 'Puntual'}

    def __init__(self, cutoff_date: str = None):
        """Inicializa el DataManager."""
        self.cutoff = cutoff_date or pd.Timestamp.now().strftime('%Y-%m-%d')
        self.cutoff_ts = pd.Timestamp(self.cutoff)

        # Conexión a Odoo
        self.odoo_connection: Optional[OdooConnection] = None
        self.data_retriever: Optional[DataRetriever] = None

        # Limpieza de datos
        self._cleaner: DataCleaner = DataCleaner()

        # Modelos
        self._models: Dict[str, Any] = {}
        self._model: Optional[Any] = None
        self._transformations: Dict[str, Any] = {}

    def is_model_loaded(self):
        return self._model is not None

    async def connect(self) -> None:
        """Establece la conexión con Odoo."""
        self.odoo_connection = OdooConnection()
        await self.odoo_connection.connect()
        self.data_retriever = DataRetriever(
            odoo_connection=self.odoo_connection,
            cutoff_date=self.cutoff
        )

    def load_model(self, model_path: str) -> None:
        """Carga un modelo de predicción."""
        model = joblib.load(model_path)
        self._models['invoice_risk_model'] = model
        self._model = model

    # =========================================================================
    # MÉTODOS INTERNOS DE PROCESAMIENTO
    # =========================================================================

    async def _get_client_invoices_df(self, partner_id: int) -> pd.DataFrame:
        """Obtiene TODAS las facturas de un cliente con campos de retraso calculados."""
        raw_data = await self.data_retriever.get_invoices_by_partner(partner_id)
        if not raw_data:
            return pd.DataFrame()

        df = pd.DataFrame(raw_data)
        clean_data, _ = self._cleaner.clean_raw_data(df)

        if clean_data is None or clean_data.empty:
            return pd.DataFrame()

        # Calcular campos de retraso para facturas pagadas
        dataset = self._add_payment_delay_columns(clean_data)
        return dataset

    def _add_payment_delay_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Añade datos de retraso de pago.
        
        Calcula:
        - payment_overdue_days: días entre fecha de pago y fecha de vencimiento
        - paid_late: True si payment_overdue_days > 0
        """
        df = df.copy()
        
        # Solo calcular para facturas pagadas
        paid_mask = (df['payment_state'] == 'paid') & df['payment_dates'].notna()
        if paid_mask.any():
            df.loc[paid_mask, 'payment_overdue_days'] = (
                df.loc[paid_mask, 'payment_dates'] - df.loc[paid_mask, 'invoice_date_due']
            ).dt.days
            df.loc[paid_mask, 'paid_late'] = df.loc[paid_mask, 'payment_overdue_days'] > 0
        return df

    async def _get_invoice_df(self, invoice_id: int) -> Optional[pd.DataFrame]:
        """Obtiene una factura específica."""
        raw_data = await self.data_retriever.get_invoice_by_id(invoice_id)
        if not raw_data:
            return None

        df = pd.DataFrame([raw_data])
        clean_data, _ = self._cleaner.clean_raw_data(df)

        if clean_data is None or clean_data.empty:
            return None

        return clean_data

    async def _clean_raw_invoices(self, raw_invoices: list) -> pd.DataFrame:
        """Limpia una lista de facturas raw."""
        if not raw_invoices:
            return pd.DataFrame()

        df = pd.DataFrame(raw_invoices)
        clean_df, _ = self._cleaner.clean_raw_data(df)
        return clean_df if clean_df is not None else pd.DataFrame()

    def _calculate_risk_score(self, client: ClientInfo) -> float:
        """Calcula puntuación de riesgo 0-100."""
        score = 0.0

        # Factor 1: Ratio de puntualidad (40%)
        score += (1 - client.on_time_ratio) * 40

        # Factor 2: Promedio de días de retraso (30%)
        delay_score = min(client.avg_delay_days / 60, 1.0) * 30
        score += delay_score

        # Factor 3: Facturas vencidas actuales (30%)
        if client.total_invoices > 0:
            overdue_ratio = client.overdue_invoices / client.total_invoices
            score += overdue_ratio * 30

        return round(min(score, 100), 2)

    def _is_overdue(self, due_date, cutoff: pd.Timestamp = None) -> bool:
        """Determina si una fecha de vencimiento está vencida."""
        if cutoff is None:
            cutoff = self.cutoff_ts
        if pd.isna(due_date):
            return False
        return due_date < cutoff

    def _calculate_days_overdue(self, due_date, cutoff: pd.Timestamp = None) -> Optional[int]:
        """Calcula días de vencimiento."""
        if cutoff is None:
            cutoff = self.cutoff_ts
        if pd.isna(due_date):
            return None
        if due_date >= cutoff:
            return None
        return (cutoff - due_date).days

    # =========================================================================
    # MÉTODOS DE BÚSQUEDA
    # =========================================================================

    async def search_clients(self, name: str, limit: int = 5) -> List[ClientSearchResult]:
        """Busca clientes por nombre."""
        raw_data = await self.data_retriever.search_client_by_name(name, limit)
        if not raw_data:
            return []
        return [ClientSearchResult(id=record['id'], name=record['name']) for record in raw_data]

    async def get_invoice_by_name(self, invoice_name: str) -> Optional[InvoiceSummary]:
        """Recupera una factura por su nombre."""
        raw_data = await self.data_retriever.search_invoice_by_name(invoice_name)
        if not raw_data:
            return None

        partner_id = raw_data['partner_id']
        if isinstance(partner_id, (list, tuple)):
            partner_id = partner_id[0]
        invoice_id = raw_data['id']

        df = await self._get_client_invoices_df(partner_id)

        if df.empty:
            return None
        invoice_df = df[df['id'] == invoice_id]

        if invoice_df.empty:
            return None

        row = invoice_df.iloc[0]
        days_overdue = self._calculate_days_overdue(row['invoice_date_due'])

        return InvoiceSummary(
            id=int(row['id']),
            name=row['name'],
            amount_eur=round(float(row['amount_residual_eur']), 2),  # RESIDUAL para deuda
            invoice_date=row['invoice_date'].date() if pd.notna(row['invoice_date']) else None,
            due_date=row['invoice_date_due'].date() if pd.notna(row['invoice_date_due']) else None,
            payment_state=PaymentState(row['payment_state']),
            payment_date=row['payment_dates'].date() if pd.notna(row.get('payment_dates')) else None,
            paid_late=bool(row['paid_late']) if pd.notna(row.get('paid_late')) else None,
            delay_days=int(row['payment_overdue_days']) if pd.notna(row.get('payment_overdue_days')) else None,
            days_overdue=days_overdue,
            partner_id=partner_id,
        )

    # =========================================================================
    # MÉTODOS DE INFORMACIÓN DE CLIENTE
    # =========================================================================

    async def get_client_info(self, partner_id: int) -> Optional[ClientInfo]:
        """Obtiene información y estadísticas de un cliente."""
        df = await self._get_client_invoices_df(partner_id)

        if df.empty:
            return None

        paid_df = df[df['payment_state'] == 'paid']
        unpaid_df = df[df['payment_state'] == 'not_paid']

        overdue_df = unpaid_df[unpaid_df['invoice_date_due'] < self.cutoff_ts]

        paid_count = len(paid_df)
        on_time_ratio = 0.0
        avg_delay_days = 0.0

        if paid_count > 0:
            on_time_count = (~paid_df['paid_late']).sum()
            on_time_ratio = round(on_time_count / paid_count, 4)
            avg_delay_days = round(float(paid_df['payment_overdue_days'].mean()), 2)

        client_info = ClientInfo(
            id=partner_id,
            name=df['partner_name'].iloc[0],
            country_name=df.get('country_name', pd.Series([None])).iloc[0],
            total_invoices=len(df),
            paid_invoices=paid_count,
            unpaid_invoices=len(unpaid_df),
            overdue_invoices=len(overdue_df),
            total_invoiced_eur=round(float(df['amount_total_eur'].sum()), 2),
            total_outstanding_eur=round(float(unpaid_df['amount_residual_eur'].sum()), 2),
            on_time_ratio=on_time_ratio,
            avg_delay_days=avg_delay_days,
        )

        client_info.risk_score = self._calculate_risk_score(client_info)
        return client_info

    async def get_client_invoices(self, partner_id: int, limit: int = 20,
                                  only_unpaid: bool = False,
                                  paid_only: bool = False) -> List[InvoiceSummary]:
        """Obtiene las facturas de un cliente."""
        df = await self._get_client_invoices_df(partner_id)

        if df.empty:
            return []

        if only_unpaid:
            df = df[df['payment_state'] == 'not_paid']
        if paid_only:
            df = df[df['payment_state'] == 'paid']

        df = df.head(limit)

        invoices = []
        for _, row in df.iterrows():
            days_overdue = None
            if row['payment_state'] == 'not_paid':
                days_overdue = self._calculate_days_overdue(row['invoice_date_due'])

            # Para facturas pagadas, mostrar amount_total
            # Para facturas pendientes, mostrar amount_residual
            if row['payment_state'] == 'paid':
                amount = float(row['amount_total_eur'])
            else:
                amount = float(row['amount_residual_eur'])

            invoices.append(InvoiceSummary(
                id=int(row['id']),
                name=row['name'],
                amount_eur=round(amount, 2),
                invoice_date=row['invoice_date'].date() if pd.notna(row['invoice_date']) else None,
                due_date=row['invoice_date_due'].date() if pd.notna(row['invoice_date_due']) else None,
                payment_state=PaymentState(row['payment_state']),
                payment_date=row['payment_dates'].date() if pd.notna(row.get('payment_dates')) else None,
                paid_late=bool(row['paid_late']) if pd.notna(row.get('paid_late')) else None,
                delay_days=int(row['payment_overdue_days']) if pd.notna(row.get('payment_overdue_days')) else None,
                days_overdue=days_overdue,
                partner_id=partner_id,
            ))

        return invoices

    async def get_all_partners(self) -> pd.DataFrame:
        """Obtiene todos los clientes."""
        raw_data = await self.data_retriever.get_all_customer_partners()
        return pd.DataFrame(raw_data) if raw_data else pd.DataFrame()

    # =========================================================================
    # MÉTODOS DE PREDICCIÓN
    # =========================================================================

    def _invoice_to_dict(self, row: pd.Series) -> dict:
        """Convierte una fila de factura a diccionario para el MCP."""
        return {
            "id": int(row['id']) if pd.notna(row.get('id')) else None,
            "name": row.get('name'),
            "partner_id": int(row['partner_id']) if pd.notna(row.get('partner_id')) else None,
            "partner_name": row.get('partner_name'),
            "company_name": row.get('company_name'),
            "currency_name": row.get('currency_name', 'EUR'),
            "amount_total_eur": float(row['amount_total_eur']),
            "amount_residual_eur": float(row.get('amount_residual_eur', row['amount_total_eur'])),
            "invoice_date": row['invoice_date'].strftime('%Y-%m-%d') if pd.notna(row.get('invoice_date')) else None,
            "invoice_date_due": row['invoice_date_due'].strftime('%Y-%m-%d') if pd.notna(row.get('invoice_date_due')) else None,
            "payment_date": row['payment_dates'].strftime('%Y-%m-%d') if pd.notna(row.get('payment_dates')) else None,
            "payment_state": row.get('payment_state', 'not_paid'),
        }

    def _history_to_list(self, df: pd.DataFrame) -> list:
        """Convierte un DataFrame de historial a lista de diccionarios para el MCP."""
        if df.empty:
            return []
        return [self._invoice_to_dict(row) for _, row in df.iterrows()]

    async def predict(self, invoice_id: int) -> PredictionResult:
        """Predice el riesgo de impago de una factura."""
        from src.mcp.prediction_client import get_prediction_client

        invoice_df = await self._get_invoice_df(invoice_id)
        if invoice_df is None:
            raise ValueError(f"La factura con ID {invoice_id} no existe.")

        invoice = invoice_df.iloc[0]

        partner_id = invoice['partner_id']
        if isinstance(partner_id, (list, tuple)):
            partner_id = partner_id[0]
        client_invoices = await self._get_client_invoices_df(partner_id)
        history = client_invoices[client_invoices['id'] != invoice_id]

        # Convertir a datos crudos y enviar al MCP
        invoice_dict = self._invoice_to_dict(invoice)
        history_list = self._history_to_list(history)

        mcp_client = get_prediction_client()
        result = await mcp_client.predict(invoice_dict, history_list)

        prediction = result["prediction"]
        prob_dict = result["probabilities"]

        return PredictionResult(
            partner_id=int(partner_id),
            partner_name=invoice['partner_name'],
            is_hypothetical=False,
            invoice_id=invoice_id,
            invoice_name=invoice['name'],
            amount_eur=round(float(invoice['amount_residual_eur']), 2),
            due_date=invoice['invoice_date_due'].date() if pd.notna(invoice['invoice_date_due']) else None,
            prediction=RiskCategory(prediction),
            probabilities=prob_dict
        )

    async def predict_hypothetical(
            self, partner_id: int, amount_eur: float, invoice_date: str = None,
            due_date: str = None, payment_term_days: int = 30) -> PredictionResult:
        """Predice riesgo para una factura hipotética."""
        from src.mcp.prediction_client import get_prediction_client

        invoice_date_ts = pd.Timestamp(invoice_date) if invoice_date else pd.Timestamp.now()
        if due_date:
            due_date_ts = pd.Timestamp(due_date)
        else:
            due_date_ts = invoice_date_ts + pd.Timedelta(days=payment_term_days)

        history = await self._get_client_invoices_df(partner_id)

        if history.empty:
            return None

        partner_name = history['partner_name'].iloc[0]
        company_name = history['company_name'].iloc[0]

        # Construir factura hipotética como diccionario
        invoice_dict = {
            "amount_total_eur": amount_eur,
            "invoice_date": invoice_date_ts.strftime('%Y-%m-%d'),
            "invoice_date_due": due_date_ts.strftime('%Y-%m-%d'),
            "currency_name": "EUR",
            "company_name": company_name,
        }

        history_list = self._history_to_list(history)

        mcp_client = get_prediction_client()
        result = await mcp_client.predict(invoice_dict, history_list)

        prediction = result["prediction"]
        prob_dict = result["probabilities"]

        return PredictionResult(
            partner_id=partner_id,
            partner_name=partner_name,
            is_hypothetical=True,
            invoice_id=None,
            invoice_name=None,
            amount_eur=round(amount_eur, 2),
            due_date=due_date_ts.date(),
            prediction=RiskCategory(prediction),
            probabilities=prob_dict
        )

    # =========================================================================
    # MÉTODOS DE FACTURAS GLOBALES
    # =========================================================================

    async def get_overdue_invoices(self, limit: int = None, min_days_overdue: int = 1) -> List[InvoiceSummary]:
        """Obtiene facturas vencidas de todos los clientes."""
        raw_invoices = await self.data_retriever.get_all_overdue_invoices(
            min_days_overdue=min_days_overdue,
            limit=None  # Recuperar todas, filtrar después
        )

        if not raw_invoices:
            return []

        df = await self._clean_raw_invoices(raw_invoices)

        if df.empty:
            return []

        # Filtrar solo no pagadas
        df = df[df['payment_state'] == 'not_paid']

        # Calcular días vencidos
        df['days_overdue'] = (self.cutoff_ts - df['invoice_date_due']).dt.days
        df = df[df['days_overdue'] >= min_days_overdue]

        # Ordenar por días vencidos
        df = df.sort_values('days_overdue', ascending=False)

        if limit is not None and limit > 0:
            df = df.head(limit)

        results = []
        for _, row in df.iterrows():
            results.append(InvoiceSummary(
                id=int(row['id']),
                name=row['name'],
                amount_eur=round(float(row['amount_residual_eur']), 2),
                invoice_date=row['invoice_date'].date() if pd.notna(row['invoice_date']) else None,
                due_date=row['invoice_date_due'].date() if pd.notna(row['invoice_date_due']) else None,
                payment_state=PaymentState.NOT_PAID,
                days_overdue=int(row['days_overdue']),
                partner_id=int(row['partner_id']),
                partner_name=row.get('partner_name')
            ))

        return results

    async def get_upcoming_due_invoices(self, days_ahead: int = 7, limit: int = 20) -> List[InvoiceSummary]:
        """Obtiene facturas que vencen en los próximos X días."""
        end_date = (self.cutoff_ts + pd.Timedelta(days=days_ahead)).strftime('%Y-%m-%d')

        raw_invoices = await self.data_retriever.get_invoices_due_between(
            start_date=self.cutoff,
            end_date=end_date,
            only_unpaid=True
        )

        if not raw_invoices:
            return []

        df = await self._clean_raw_invoices(raw_invoices)

        if df.empty:
            return []

        df = df[df['payment_state'] == 'not_paid']
        df['days_until_due'] = (df['invoice_date_due'] - self.cutoff_ts).dt.days
        df = df.sort_values('days_until_due').head(limit)

        results = []
        for _, row in df.iterrows():
            results.append(InvoiceSummary(
                id=int(row['id']),
                name=row['name'],
                amount_eur=round(float(row['amount_residual_eur']), 2),
                invoice_date=row['invoice_date'].date() if pd.notna(row['invoice_date']) else None,
                due_date=row['invoice_date_due'].date() if pd.notna(row['invoice_date_due']) else None,
                payment_state=PaymentState.NOT_PAID,
                days_overdue=-int(row['days_until_due']),
                partner_id=int(row['partner_id']),
                partner_name=row.get('partner_name')
            ))

        return results

    async def get_invoices_by_period(self, start_date: str, end_date: str,
                                     partner_id: int = None, only_unpaid: bool = False) -> List[InvoiceSummary]:
        """Obtiene facturas emitidas en un período."""
        raw_invoices = await self.data_retriever.get_invoices_by_period(
            start_date=start_date,
            end_date=end_date,
            partner_id=partner_id,
            only_unpaid=only_unpaid
        )

        if not raw_invoices:
            return []

        df = await self._clean_raw_invoices(raw_invoices)

        if df.empty:
            return []

        if only_unpaid:
            df = df[df['payment_state'] == 'not_paid']

        df = df.sort_values('invoice_date', ascending=False)

        results = []
        for _, row in df.iterrows():
            days_overdue = self._calculate_days_overdue(row['invoice_date_due'])

            # Usar amount apropiado según estado
            if row['payment_state'] == 'paid':
                amount = float(row['amount_total_eur'])
            else:
                amount = float(row['amount_residual_eur'])

            results.append(InvoiceSummary(
                id=int(row['id']),
                name=row['name'],
                amount_eur=round(amount, 2),
                invoice_date=row['invoice_date'].date() if pd.notna(row['invoice_date']) else None,
                due_date=row['invoice_date_due'].date() if pd.notna(row['invoice_date_due']) else None,
                payment_state=PaymentState(row['payment_state']),
                days_overdue=days_overdue,
                partner_id=int(row['partner_id']),
                partner_name=row.get('partner_name')
            ))

        return results

    # =========================================================================
    # MÉTODOS DE ANÁLISIS DE CARTERA
    # =========================================================================

    async def get_high_risk_clients(self, limit: int = None) -> List[ClientInfo]:
        """Obtiene los clientes con mayor riesgo."""
        partner_ids = await self.data_retriever.get_partners_with_overdue_invoices()
        if not partner_ids:
            return []

        results = []
        for partner_id in partner_ids:
            client_info = await self.get_client_info(partner_id)
            if client_info is None:
                continue
            results.append(client_info)

        results.sort(key=lambda x: x.risk_score, reverse=True)

        if limit is None:
            return results
        return results[:limit]

    async def compare_clients(self, partner_ids: List[int]) -> List[ClientInfo]:
        """Compara clientes."""
        if len(partner_ids) < 2:
            return []

        results = []
        for partner_id in partner_ids:
            client_info = await self.get_client_info(partner_id)
            if client_info is None:
                continue
            results.append(client_info)

        results.sort(key=lambda x: x.risk_score)
        return results

    async def get_aging_report(self, partner_id: int = None) -> AgingReport:
        """Genera informe de antigüedad de deuda (aging report).
        """
        if partner_id:
            # Aging para un cliente específico
            df = await self._get_client_invoices_df(partner_id)

            if df.empty:
                return AgingReport(
                    total_overdue_eur=0,
                    total_overdue_count=0,
                    buckets=[],
                    generated_at=self.cutoff_ts.date()
                )

            # Filtrar solo facturas vencidas no pagadas
            df = df[
                (df['payment_state'] == 'not_paid') &
                (df['invoice_date_due'] < self.cutoff_ts)
                ]
        else:
            # Aging global
            raw_invoices = await self.data_retriever.get_all_overdue_invoices(
                min_days_overdue=1,
                limit=None
            )

            if not raw_invoices:
                return AgingReport(
                    total_overdue_eur=0,
                    total_overdue_count=0,
                    buckets=[],
                    generated_at=self.cutoff_ts.date()
                )

            df = await self._clean_raw_invoices(raw_invoices)

            if df.empty:
                return AgingReport(
                    total_overdue_eur=0,
                    total_overdue_count=0,
                    buckets=[],
                    generated_at=self.cutoff_ts.date()
                )

            df = df[df['payment_state'] == 'not_paid']

        if df.empty:
            return AgingReport(
                total_overdue_eur=0,
                total_overdue_count=0,
                buckets=[],
                generated_at=self.cutoff_ts.date()
            )

        # Calcular días vencidos
        df = df.copy()
        df['days_overdue'] = (self.cutoff_ts - df['invoice_date_due']).dt.days
        df = df[df['days_overdue'] > 0]

        if df.empty:
            return AgingReport(
                total_overdue_eur=0,
                total_overdue_count=0,
                buckets=[],
                generated_at=self.cutoff_ts.date()
            )

        # Inicializar buckets
        buckets_data = {
            '0-30': {'count': 0, 'amount': 0.0},
            '31-60': {'count': 0, 'amount': 0.0},
            '61-90': {'count': 0, 'amount': 0.0},
            '>90': {'count': 0, 'amount': 0.0},
        }

        for _, row in df.iterrows():
            days = row['days_overdue']
            # IMPORTANTE: Usar amount_residual_eur para deuda real pendiente
            amount = float(row['amount_residual_eur'])

            if days <= 30:
                buckets_data['0-30']['count'] += 1
                buckets_data['0-30']['amount'] += amount
            elif days <= 60:
                buckets_data['31-60']['count'] += 1
                buckets_data['31-60']['amount'] += amount
            elif days <= 90:
                buckets_data['61-90']['count'] += 1
                buckets_data['61-90']['amount'] += amount
            else:
                buckets_data['>90']['count'] += 1
                buckets_data['>90']['amount'] += amount

        total_amount = df['amount_residual_eur'].sum()

        # Generar buckets
        buckets = []
        for label, data in buckets_data.items():
            pct = (data['amount'] / total_amount * 100) if total_amount > 0 else 0
            buckets.append(AgingBucket(
                range_label=label,
                invoice_count=data['count'],
                total_amount_eur=round(data['amount'], 2),
                percentage=round(pct, 2)
            ))

        return AgingReport(
            total_overdue_eur=round(float(total_amount), 2),
            total_overdue_count=sum(b.invoice_count for b in buckets),
            buckets=buckets,
            generated_at=self.cutoff_ts.date()
        )

    async def get_portfolio_summary(self) -> PortfolioSummary:
        """Genera resumen de cartera."""
        raw_unpaid = await self.data_retriever.get_all_unpaid_invoices(limit=None)
        df_unpaid = await self._clean_raw_invoices(raw_unpaid)

        total_outstanding = 0.0
        total_overdue = 0.0
        total_not_due = 0.0
        overdue_count = 0
        not_due_count = 0

        if not df_unpaid.empty:
            df_unpaid = df_unpaid[df_unpaid['payment_state'] == 'not_paid']

            for _, row in df_unpaid.iterrows():
                # IMPORTANTE: Usar amount_residual_eur
                amount = float(row['amount_residual_eur'])
                due_date = row['invoice_date_due']

                total_outstanding += amount

                if due_date < self.cutoff_ts:
                    total_overdue += amount
                    overdue_count += 1
                else:
                    total_not_due += amount
                    not_due_count += 1

        # Calcular DSO
        all_invoices = await self.data_retriever.get_all_outbound_invoices()
        df_all = await self._clean_raw_invoices(all_invoices)

        total_delay_days = 0.0
        paid_count = 0

        if not df_all.empty:
            paid_df = df_all[df_all['payment_state'] == 'paid']
            if len(paid_df) > 0:
                paid_df = self._add_payment_delay_columns(paid_df)
                total_delay_days = paid_df['payment_overdue_days'].sum()
                paid_count = len(paid_df)

        avg_delay = (total_delay_days / paid_count) if paid_count > 0 else 0
        dso = 30 + avg_delay

        return PortfolioSummary(
            total_outstanding_eur=round(total_outstanding, 2),
            total_overdue_eur=round(total_overdue, 2),
            total_not_due_eur=round(total_not_due, 2),
            overdue_count=overdue_count,
            not_due_count=not_due_count,
            dso=round(dso, 1),
            average_delay_days=round(avg_delay, 1),
            generated_at=self.cutoff_ts.date()
        )

    # =========================================================================
    # MÉTODOS DE ANÁLISIS DE TENDENCIAS
    # =========================================================================

    async def get_client_trend(self, partner_id: int, recent_months: int = 6) -> Optional[ClientTrend]:
        """Analiza la tendencia de comportamiento de pago de un cliente."""
        df = await self._get_client_invoices_df(partner_id)

        if df.empty:
            return None

        paid_df = df[df['payment_state'] == 'paid'].copy()
        if len(paid_df) < 4:
            return None

        recent_start = self.cutoff_ts - pd.DateOffset(months=recent_months)
        recent = paid_df[paid_df['invoice_date'] >= recent_start]
        previous = paid_df[paid_df['invoice_date'] < recent_start]

        def calc_stats(subset):
            if len(subset) == 0:
                return 0, 0.0, 0.0
            on_time = (~subset['paid_late']).sum() / len(subset)
            avg_delay = subset['payment_overdue_days'].mean()
            return len(subset), round(on_time, 4), round(avg_delay, 2)

        recent_count, recent_otr, recent_delay = calc_stats(recent)
        prev_count, prev_otr, prev_delay = calc_stats(previous)
        change_otr = recent_otr - prev_otr
        change_delay = recent_delay - prev_delay

        if prev_count == 0:
            trend = "sin_historial"
        elif change_otr > 0.05 or change_delay < -5:
            trend = "mejorando"
        elif change_otr < -0.05 or change_delay > 5:
            trend = "empeorando"
        else:
            trend = "estable"

        return ClientTrend(
            partner_id=partner_id,
            partner_name=df['partner_name'].iloc[0],
            recent_invoices=recent_count,
            recent_on_time_ratio=recent_otr,
            recent_avg_delay=recent_delay,
            previous_invoices=prev_count,
            previous_on_time_ratio=prev_otr,
            previous_avg_delay=prev_delay,
            trend=trend,
            change_on_time_ratio=round(change_otr, 4),
            change_avg_delay=round(change_delay, 2)
        )

    async def get_deteriorating_clients(self, limit: int = 10, min_invoices: int = 5) -> List[DeterioratingClient]:
        """Identifica clientes cuyo comportamiento de pago está empeorando."""
        partner_ids = await self.data_retriever.get_partners_with_overdue_invoices()

        all_invoices = await self.data_retriever.get_all_outbound_invoices()
        df = pd.DataFrame(all_invoices)
        if not df.empty:
            clean_df, _ = self._cleaner.clean_raw_data(df)
            if clean_df is not None and not clean_df.empty:
                all_partner_ids = clean_df['partner_id'].unique().tolist()
                partner_ids = list(set(partner_ids + all_partner_ids))

        results = []
        for pid in partner_ids:
            trend = await self.get_client_trend(pid, recent_months=6)
            if trend is None:
                continue
            if trend.previous_invoices < min_invoices:
                continue
            if trend.trend != "empeorando":
                continue
            client_info = await self.get_client_info(pid)
            if client_info is None:
                continue
            results.append(DeterioratingClient(
                partner_id=pid,
                partner_name=trend.partner_name,
                previous_on_time_ratio=trend.previous_on_time_ratio,
                recent_on_time_ratio=trend.recent_on_time_ratio,
                change_on_time_ratio=trend.change_on_time_ratio,
                previous_avg_delay=trend.previous_avg_delay,
                recent_avg_delay=trend.recent_avg_delay,
                change_avg_delay=trend.change_avg_delay,
                current_overdue_count=client_info.overdue_invoices,
                current_overdue_eur=client_info.total_outstanding_eur
            ))

        results.sort(key=lambda x: x.change_on_time_ratio)
        return results[:limit]