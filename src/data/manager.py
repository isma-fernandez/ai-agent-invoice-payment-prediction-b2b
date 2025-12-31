import pandas as pd
from typing import Optional, Dict, List, Any
import joblib

from src.utils.odoo_connector import OdooConnection
from .retriever import DataRetriever
from .cleaner import DataCleaner
from .feature_engineering import FeatureEngineering
from .models import (
    ClientSearchResult, ClientInfo, InvoiceSummary, 
    PredictionResult, RiskCategory, PaymentState,
    AgingReport, PortfolioSummary, ClientTrend,
    DeterioratingClient, AgingBucket
)

class DataManager:
    """
    Centraliza la gestión de datos para el proyecto de predicción de pagos de facturas.
    Gestiona la extracción, limpieza y preparación de los datos.
    Tanto datos del agente como datos para el modelo de IA.

    """
    
    LABEL_MAPPING = {0: 'Grave', 1: 'Leve', 2: 'Puntual'}

    def __init__(self, cutoff_date: str = None):
        """Inicializa el DataManager.
        Args:
            cutoff_date: Fecha de corte para cálculos de features (YYYY-MM-DD).
        Attributes:
            cutoff_date: Fecha de corte para cálculos de features.
            _odoo_connection: Conexión a Odoo.
            _data_retriever: Objeto de extracción de datos.
            _cleaner: Objeto de limpieza de datos.
            _feature_engineering: Objeto de ingeniería de características.
            _models: Diccionario de modelos cargados.
            _model: Modelo principal para predicción.
            _transformations: Transformaciones aplicadas a los datos.
        """
        self.cutoff = cutoff_date or pd.Timestamp.now().strftime('%Y-%m-%d')

        # Conexión a Odoo
        self.odoo_connection: Optional[OdooConnection] = None
        self.data_retriever: Optional[DataRetriever] = None
        # Limpieza y procesamiento de datos
        self._cleaner: DataCleaner = DataCleaner()
        self._feature_engineering: FeatureEngineering = FeatureEngineering(cutoff_date=cutoff_date)
        # Modelos y transformaciones
        self._models: Dict[str, Any] = {} # Soporte para múltiples modelos (futura regresión)
        self._model: Optional[Any] = None # Modelo principal
        self._transformations: Dict[str, Any] = {}


    async def connect(self) -> None:
        """Establece la conexión con Odoo e inicializa el DataRetriever.
        """
        self.odoo_connection = OdooConnection()
        await self.odoo_connection.connect()
        self.data_retriever = DataRetriever(odoo_connection=self.odoo_connection, cutoff_date=self.cutoff)


    def load_model(self, model_path: str) -> None:
        """Carga un modelo de predicción desde el disco.
        
        Args:
            model_path: Ruta al archivo del modelo (joblib).
        """
        # TODO: Añadir ruta y nombre a la configuración
        # TODO: Soporte para múltiples modelos
        model = joblib.load(model_path)
        self._models['invoice_risk_model'] = model
        self._model = model


    async def _get_client_invoices_df(self, partner_id: int) -> pd.DataFrame:
        """Obtiene todas las facturas de un cliente y calcula las características
        derivadas."""

        raw_data = await self.data_retriever.get_invoices_by_partner(partner_id) 
        if not raw_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(raw_data)
        clean_data, _ = self._cleaner.clean_raw_data(df)

        if clean_data is None or clean_data.empty:
            return pd.DataFrame()
        
        dataset = self._feature_engineering.generate_full_client_data(clean_data)
        return dataset


    async def _get_invoice_df(self, invoice_id: int) -> Optional[pd.DataFrame]:
        """
        Obtiene una factura específica."""
        raw_data = await self.data_retriever.get_invoice_by_id(invoice_id)  
        if not raw_data:
            return None
        
        df = pd.DataFrame([raw_data])
        clean_data, _ = self._cleaner.clean_raw_data(df)
        
        if clean_data is None or clean_data.empty:
            return None
            
        return clean_data


    # NOTA: Se utiliza para encontrar el ID de un cliente a partir de su nombre
    async def search_clients(self, name: str, limit: int = 5) -> List[ClientSearchResult]:
        """
        Busca clientes por nombre.
        
        Args:
            name: Nombre de la empresa a buscar.
            limit: Máximo de resultados.
            
        Returns:
            Lista de ClientSearchResult con los clientes encontrados.
        """
        raw_data = await self.data_retriever.search_client_by_name(name, limit)
        if not raw_data:
            return []
        results = [ClientSearchResult(id=record['id'], name=record['name']) for record in raw_data]
        
        return results

    # NOTA: Una vez tenemos el ID del cliente, obtenemos su info
    async def get_client_info(self, partner_id: int) -> Optional[ClientInfo]:
        """
        Obtiene información y estadísticas agregadas de un cliente.
        
        Args:
            partner_id: ID del cliente en Odoo.
            
        Returns:
            ClientInfo con estadísticas del cliente o None si no existe.
        """
        df = await self._get_client_invoices_df(partner_id)
        
        if df.empty:
            return None
        
        stats = self._feature_engineering.calculate_client_stats(df)
        
        client_info = ClientInfo(
            id=partner_id,
            name=df['partner_name'].iloc[0],
            country_name=df.get('country_name', pd.Series([None])).iloc[0],
            **stats
        )

        client_info.risk_score = self._calculate_risk_score(client_info)

        return client_info

    # NOTA: Realmente solo sirve para entrenar nuevos modelos
    async def get_all_partners(self) -> pd.DataFrame:
        """
        Obtiene todos los clientes.
        Útil para entrenar nuevos modelos.
        
        Returns:
            DataFrame con todos los partners y sus campos.
        """
        raw_data = await self.data_retriever.get_all_customer_partners()
        
        return pd.DataFrame(raw_data) if raw_data else pd.DataFrame()
    

    # TODO: El raise puede traer problemas
    async def predict(self, invoice_id: int) -> PredictionResult:
        """
        Predice el riesgo de impago de una factura.
        Devuelve también información para explicabilidad.
        
        Args:
            invoice_id: id de la factura a predecir.
            
        Returns:
            PredictionResult con:
            - invoice_id, invoice_name, partner_id, partner_name, amount_eur
            - prediction: clase predicha Puntual, Leve, Grave
            - probabilities: dict con probabilidad por clase
            
        Raises:
            ValueError: Si la factura no existe.
        """  
        invoice_df = await self._get_invoice_df(invoice_id)
        if invoice_df is None:
            raise ValueError(f"La factura con ID {invoice_id} no existe.")
        
        invoice = invoice_df.iloc[0]
        
        partner_id = invoice['partner_id']
        if isinstance(partner_id, (list, tuple)):
            partner_id = partner_id[0]  
        client_invoices = await self._get_client_invoices_df(partner_id)
        history = client_invoices[client_invoices['id'] != invoice_id]
        
        X = self._feature_engineering.process_invoice_for_prediction(
            new_invoice=invoice,
            client_invoices_df=history
        )
        
        prediction_idx = int(self._model.predict(X)[0])
        prediction = self.LABEL_MAPPING[prediction_idx]
        probabilities = self._model.predict_proba(X)[0]
        classes = self._model.classes_
        prob_dict = {
            str(clase): round(float(prob), 4)
            for clase, prob in zip(classes, probabilities)
        }
        
        return PredictionResult(
            partner_id=int(partner_id),
            partner_name=invoice['partner_name'],
            is_hypothetical=False,
            invoice_id=invoice_id,
            invoice_name=invoice['name'],
            amount_eur=round(float(invoice['amount_total_eur']), 2),
            due_date=invoice['invoice_date_due'].date() if pd.notna(invoice['invoice_date_due']) else None,
            prediction=RiskCategory(prediction),
            probabilities=prob_dict
        )


    async def predict_hypothetical(
            self, partner_id: int, amount_eur: float, invoice_date: str = None,
            due_date: str = None, payment_term_days: int = 30) -> PredictionResult:
        """
        Predice riesgo para una factura que aún no se ha creado.
        
        Útil si se pide al agente: "Si le hago una factura con importe X, cuál sería el riesgo?"
        
        Args:
            partner_id: ID del cliente.
            amount_eur: Importe de la factura.
            invoice_date: Fecha de factura (valor por defecto: hoy).
            due_date: Fecha de vencimiento (valor por defecto: calculada con payment_term_days).
            payment_term_days: Días de plazo de pago (valor por defecto: 30).
            
        Returns:
            PredictionResult con la predicción o None si el cliente no tiene historial de facturas.
        """
        # TODO: No soporta diferentes monedas aún
        # TODO: No tiene sentido si el cliente no tiene historial de facturas,
        # hay que tratar ese caso aparte.
        
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
        
        hypothetic_invoice = pd.Series({
            'id': -1,
            'name': 'hypothetic_invoice',
            'partner_id': partner_id,
            'partner_name': partner_name,
            'company_name': company_name,
            'currency_name': 'EUR',
            'amount_total_eur': amount_eur,
            'amount_residual_eur': amount_eur,
            'invoice_date': invoice_date_ts,
            'invoice_date_due': due_date_ts,
            'payment_dates': pd.NaT,
            'payment_state': 'not_paid',
        })
        
        X = self._feature_engineering.process_invoice_for_prediction(
            new_invoice=hypothetic_invoice,
            client_invoices_df=history
        )
        
        prediction_idx = int(self._model.predict(X)[0])
        prediction = self.LABEL_MAPPING[prediction_idx]
        probabilities = self._model.predict_proba(X)[0]   
        classes = self._model.classes_
        prob_dict = {
            str(clase): round(float(prob), 4) 
            for clase, prob in zip(classes, probabilities)
        }
        
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


    async def get_invoice_by_name(self, invoice_name: str) -> Optional[InvoiceSummary]:
        """Recupera una factura por su nombre.
        
        Args:
            invoice_name: Nombre de la factura a buscar.
            
        Returns:
            InvoiceSummary si se encuentra, None en caso contrario.
        """
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
        days_overdue = None
        if row['payment_state'] == 'not_paid' and pd.notna(row['invoice_date_due']):
            cutoff = pd.Timestamp(self.cutoff)
            if row['invoice_date_due'] < cutoff:
                days_overdue = (cutoff - row['invoice_date_due']).days

        return InvoiceSummary(
            id=int(row['id']),
            name=row['name'],
            amount_eur=round(float(row['amount_total_eur']), 2),
            invoice_date=row['invoice_date'].date() if pd.notna(row['invoice_date']) else None,
            due_date=row['invoice_date_due'].date() if pd.notna(row['invoice_date_due']) else None,
            payment_state=PaymentState(row['payment_state']),
            payment_date=row['payment_dates'].date() if pd.notna(row.get('payment_dates')) else None,
            paid_late=bool(row['paid_late']) if pd.notna(row.get('paid_late')) else None,
            delay_days=int(row['payment_overdue_days']) if pd.notna(row.get('payment_overdue_days')) else None,
            days_overdue=days_overdue,
            partner_id=partner_id,
        )


    async def get_client_invoices(self, partner_id: int, limit: int = 20, 
                                   only_unpaid: bool = False,
                                   paid_only: bool = False) -> List[InvoiceSummary]:
        """Obtiene las facturas de un cliente para el agente.
        
        Args:
            partner_id: ID del cliente en Odoo.
            limit: Máximo de facturas a devolver.
            only_unpaid: Si True, solo devuelve facturas pendientes de pago.
            
        Returns:
            Lista de InvoiceSummary ordenada por fecha (más recientes primero).
        """
        df = await self._get_client_invoices_df(partner_id)
        
        if df.empty:
            return []
        
        if only_unpaid:
            df = df[df['payment_state'] == 'not_paid']
        if paid_only:
            df = df[df['payment_state'] == 'paid']
        df = df.head(limit)
        
        cutoff = pd.Timestamp(self.cutoff)
        invoices = []
        for _, row in df.iterrows():
            days_overdue = None
            if row['payment_state'] == 'not_paid' and pd.notna(row['invoice_date_due']):
                if row['invoice_date_due'] < cutoff:
                    days_overdue = (cutoff - row['invoice_date_due']).days
            
            invoices.append(InvoiceSummary(
                id=int(row['id']),
                name=row['name'],
                amount_eur=round(float(row['amount_total_eur']), 2),
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


    def _calculate_risk_score(self, client: ClientInfo) -> float:
        """Calcula una puntuación de riesgo 0-100 para un cliente."""
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


    async def get_overdue_invoices(self, limit: int = 10, min_days_overdue: int = 1) -> List[InvoiceSummary]:
        """Obtiene facturas vencidas de todos los clientes."""
        raw_invoices = await self.data_retriever.get_all_overdue_invoices(
            min_days_overdue=min_days_overdue,
            limit=limit * 2
        )
        if not raw_invoices:
            return []

        cutoff = pd.Timestamp(self.cutoff)
        results = []

        for inv in raw_invoices:
            partner_id = inv['partner_id']
            partner_name = None

            if isinstance(partner_id, (list, tuple)):
                partner_name = partner_id[1]
                partner_id = partner_id[0]

            due_date = pd.Timestamp(inv['invoice_date_due'])
            invoice_date = pd.Timestamp(inv['invoice_date'])
            days_overdue = (cutoff - due_date).days
            if days_overdue < min_days_overdue:
                continue

            results.append(InvoiceSummary(
                id=inv['id'],
                name=inv['name'],
                amount_eur=round(float(inv.get('amount_residual', inv['amount_total'])), 2),
                invoice_date=invoice_date.date(),
                due_date=due_date.date(),
                payment_state=PaymentState.NOT_PAID,
                days_overdue=days_overdue,
                partner_id=partner_id,
                partner_name=partner_name
            ))

        results.sort(key=lambda x: x.days_overdue, reverse=True)
        return results[:limit]


    async def get_high_risk_clients(self, limit: int = 10) -> List[ClientInfo]:
        """Obtiene los clientes con mayor riesgo, ordenados por risk_score."""
        partner_ids = await self.data_retriever.get_partners_with_overdue_invoices()
        if not partner_ids:
            return []
        results = []

        for partner_id in partner_ids:
            client_info = await self.get_client_info(partner_id)
            if client_info is None:
                continue
            results.append(client_info)

        # Ordenar por riesgo
        results.sort(key=lambda x: x.risk_score, reverse=True)
        return results[:limit]


    async def compare_clients(self, partner_ids: List[int]) -> List[ClientInfo]:
        """Compara clientes añadiendo risk_score a cada uno."""
        if len(partner_ids) < 2:
            return []

        results = []
        for partner_id in partner_ids:
            client_info = await self.get_client_info(partner_id)
            if client_info is None:
                continue
            results.append(client_info)

        # Ordenar por riesgo
        results.sort(key=lambda x: x.risk_score)
        return results


    async def get_upcoming_due_invoices(self, days_ahead: int = 7, limit: int = 20) -> List[InvoiceSummary]:
        """Obtiene facturas que vencen en los próximos X días."""
        cutoff = pd.Timestamp(self.cutoff)
        end_date = (cutoff + pd.Timedelta(days=days_ahead)).strftime('%Y-%m-%d')

        raw_invoices = await self.data_retriever.get_invoices_due_between(
            start_date=self.cutoff,
            end_date=end_date,
            only_unpaid=True
        )

        if not raw_invoices:
            return []

        results = []
        for inv in raw_invoices:
            partner_id = inv['partner_id']
            partner_name = None
            if isinstance(partner_id, (list, tuple)):
                partner_name = partner_id[1]
                partner_id = partner_id[0]

            due_date = pd.Timestamp(inv['invoice_date_due'])
            days_until_due = (due_date - cutoff).days

            results.append(InvoiceSummary(
                id=inv['id'],
                name=inv['name'],
                amount_eur=round(float(inv.get('amount_residual', inv['amount_total'])), 2),
                invoice_date=pd.Timestamp(inv['invoice_date']).date(),
                due_date=due_date.date(),
                payment_state=PaymentState.NOT_PAID,
                days_overdue=-days_until_due,  # Negativo = días hasta vencimiento
                partner_id=partner_id,
                partner_name=partner_name
            ))

        results.sort(key=lambda x: x.due_date)
        return results[:limit]

    async def get_aging_report(self, partner_id: int = None) -> AgingReport:
        """Genera informe de antigüedad de deuda (aging report)."""

        cutoff = pd.Timestamp(self.cutoff)

        if partner_id:
            # Aging de un cliente específico
            raw_invoices = await self.data_retriever.get_invoices_by_partner(partner_id)
            # Filtrar solo vencidas no pagadas
            raw_invoices = [
                inv for inv in raw_invoices
                if inv.get('payment_state') in ['not_paid', 'partial', False]
                   and pd.Timestamp(inv['invoice_date_due']) < cutoff
            ]
        else:
            # Aging global
            raw_invoices = await self.data_retriever.get_all_overdue_invoices(min_days_overdue=1, limit=0)

        if not raw_invoices:
            return AgingReport(
                total_overdue_eur=0,
                total_overdue_count=0,
                buckets=[],
                generated_at=cutoff.date()
            )

        buckets_data = {
            '0-30': {'count': 0, 'amount': 0.0},
            '31-60': {'count': 0, 'amount': 0.0},
            '61-90': {'count': 0, 'amount': 0.0},
            '>90': {'count': 0, 'amount': 0.0},
        }

        total_amount = 0.0

        for inv in raw_invoices:
            due_date = pd.Timestamp(inv['invoice_date_due'])
            days_overdue = (cutoff - due_date).days
            amount = float(inv.get('amount_residual', inv['amount_total']))

            if days_overdue <= 0:
                continue

            total_amount += amount

            if days_overdue <= 30:
                buckets_data['0-30']['count'] += 1
                buckets_data['0-30']['amount'] += amount
            elif days_overdue <= 60:
                buckets_data['31-60']['count'] += 1
                buckets_data['31-60']['amount'] += amount
            elif days_overdue <= 90:
                buckets_data['61-90']['count'] += 1
                buckets_data['61-90']['amount'] += amount
            else:
                buckets_data['>90']['count'] += 1
                buckets_data['>90']['amount'] += amount

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
            total_overdue_eur=round(total_amount, 2),
            total_overdue_count=sum(b.invoice_count for b in buckets),
            buckets=buckets,
            generated_at=cutoff.date()
        )


    async def get_portfolio_summary(self) -> PortfolioSummary:
        """Genera resumen de cartera."""
        raw_invoices = await self.data_retriever.get_all_unpaid_invoices(limit=0)

        cutoff = pd.Timestamp(self.cutoff)

        total_outstanding = 0.0
        total_overdue = 0.0
        total_not_due = 0.0
        overdue_count = 0
        not_due_count = 0
        total_delay_days = 0.0
        paid_count = 0

        all_invoices = await self.data_retriever.get_all_outbound_invoices()
        df = pd.DataFrame(all_invoices)
        if not df.empty:
            clean_df, _ = self._cleaner.clean_raw_data(df)
            if not clean_df.empty:
                paid_df = clean_df[clean_df['payment_state'] == 'paid']
                if len(paid_df) > 0:
                    paid_df = self._feature_engineering._add_payment_features(paid_df)
                    total_delay_days = paid_df['payment_overdue_days'].sum()
                    paid_count = len(paid_df)

        for inv in raw_invoices:
            amount = float(inv.get('amount_residual', inv['amount_total']))
            due_date = pd.Timestamp(inv['invoice_date_due'])
            total_outstanding += amount
            if due_date < cutoff:
                total_overdue += amount
                overdue_count += 1
            else:
                total_not_due += amount
                not_due_count += 1

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
            generated_at=pd.Timestamp(self.cutoff).date()
        )


    async def get_client_trend(self, partner_id: int, recent_months: int = 6) -> Optional[ClientTrend]:
        """Analiza la tendencia de comportamiento de pago de un cliente."""
        df = await self._get_client_invoices_df(partner_id)
        print("1")
        print(partner_id)
        print("Recent months ", recent_months)
        if df.empty:
            return None
        print(len(df))
        print("2")
        paid_df = df[df['payment_state'] == 'paid'].copy()
        if len(paid_df) < 4:  # Mínimo para calcular tendencia
            return None
        print("3")
        cutoff = pd.Timestamp(self.cutoff)
        recent_start = cutoff - pd.DateOffset(months=recent_months)
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

        # También incluir partners con historial aunque no tengan vencidas
        all_invoices = await self.data_retriever.get_all_outbound_invoices()
        df = pd.DataFrame(all_invoices)
        if not df.empty:
            clean_df, _ = self._cleaner.clean_raw_data(df)
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


    async def get_invoices_by_period(self, start_date: str, end_date: str,
                                     partner_id: int = None, only_unpaid: bool = False) -> List[InvoiceSummary]:
        """Obtiene facturas emitidas en un período específico."""
        raw_invoices = await self.data_retriever.get_invoices_by_period(
            start_date=start_date,
            end_date=end_date,
            partner_id=partner_id,
            only_unpaid=only_unpaid
        )

        if not raw_invoices:
            return []

        cutoff = pd.Timestamp(self.cutoff)
        results = []

        for inv in raw_invoices:
            pid = inv['partner_id']
            partner_name = None
            if isinstance(pid, (list, tuple)):
                partner_name = pid[1]
                pid = pid[0]

            due_date = pd.Timestamp(inv['invoice_date_due'])
            invoice_date = pd.Timestamp(inv['invoice_date'])

            days_overdue = None
            payment_state = inv['payment_state']
            if payment_state in ['not_paid', 'partial'] and due_date < cutoff:
                days_overdue = (cutoff - due_date).days

            results.append(InvoiceSummary(
                id=inv['id'],
                name=inv['name'],
                amount_eur=round(float(inv.get('amount_residual', inv['amount_total'])), 2),
                invoice_date=invoice_date.date(),
                due_date=due_date.date(),
                payment_state=PaymentState(payment_state) if payment_state in ['paid',
                                                                               'not_paid'] else PaymentState.NOT_PAID,
                days_overdue=days_overdue,
                partner_id=pid,
                partner_name=partner_name
            ))

        results.sort(key=lambda x: x.invoice_date, reverse=True)
        return results