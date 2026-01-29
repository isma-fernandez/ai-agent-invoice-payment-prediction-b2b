import asyncio
from shared.clients.odoo_connector import OdooConnection
from .config import INVOICE_FIELDS, PARTNER_FIELDS, BATCH_SIZE
import pandas as pd


class DataRetriever:
    def __init__(self, odoo_connection: OdooConnection, cutoff_date: str = None):
        self.odoo_connection = odoo_connection
        self.cutoff_date = cutoff_date
        self.max_concurrent_requests = 5

    async def _fetch_batch(self, model: str, domain: list, fields: list,
                           limit: int, offset: int = 0) -> list:
        """Recupera un batch de registros con limit y offset."""
        return await self.odoo_connection.search_read(
            model, domain, fields, limit, offset
        )

    async def _fetch_all_parallel(self, model: str, domain: list, fields: list) -> list:
        """Recupera TODOS los registros.
        """
        first_batch = await self._fetch_batch(model, domain, fields, BATCH_SIZE, 0)

        if not first_batch or len(first_batch) < BATCH_SIZE:
            return first_batch or []

        all_records = list(first_batch)
        offset = BATCH_SIZE

        while True:
            tasks = []
            for i in range(self.max_concurrent_requests):
                current_offset = offset + (i * BATCH_SIZE)
                tasks.append(self._fetch_batch(model, domain, fields, BATCH_SIZE, current_offset))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            got_records = False
            for result in results:
                if isinstance(result, Exception):
                    print(f"Error en batch: {result}")
                    continue
                if result:
                    all_records.extend(result)
                    got_records = True

            if not got_records or any(
                    isinstance(r, list) and len(r) < BATCH_SIZE
                    for r in results if not isinstance(r, Exception)
            ):
                break

            offset += self.max_concurrent_requests * BATCH_SIZE
            print(f"Recuperados {len(all_records)} registros...")

        return all_records

    async def _fetch_with_optional_limit(self, model: str, domain: list,
                                         fields: list, limit: int = None) -> list:
        if limit is None or limit == 0:
            return await self._fetch_all_parallel(model, domain, fields)
        else:
            return await self._fetch_batch(model, domain, fields, limit, 0)

    # =========================================================================
    # MÉTODOS PARA RECUPERAR TODOS LOS REGISTROS DE UN MODELO
    # =========================================================================

    async def get_all_outbound_invoices(self) -> list:
        """Recupera TODAS las facturas de salida (outbound) de todas las empresas."""
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")

        domain = [
            ('move_type', '=', 'out_invoice'),
            ('invoice_date_due', '<=', self.cutoff_date)
        ]
        return await self._fetch_all_parallel('account.move', domain, INVOICE_FIELDS)

    async def get_all_customer_partners(self) -> list:
        """Recupera TODOS los partners (clientes)."""
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")

        domain = [('customer_rank', '>', '0')]
        return await self._fetch_all_parallel('res.partner', domain, PARTNER_FIELDS)

    async def get_all_unpaid_invoices(self, limit: int = None) -> list:
        """Recupera facturas pendientes de pago.

        Args:
            limit: Si es None o 0, recupera TODAS. Si > 0, recupera ese máximo.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")

        domain = [
            ('move_type', '=', 'out_invoice'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<=', self.cutoff_date)
        ]
        return await self._fetch_with_optional_limit('account.move', domain, INVOICE_FIELDS, limit)

    async def get_all_overdue_invoices(self, min_days_overdue: int = 1, limit: int = None) -> list:
        """Recupera facturas vencidas.

        Args:
            min_days_overdue: Mínimo de días vencidos para incluir.
            limit: Si es None o 0, recupera TODAS. Si > 0, recupera ese máximo.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")

        cutoff = pd.Timestamp(self.cutoff_date)
        max_due_date = (cutoff - pd.Timedelta(days=min_days_overdue)).strftime('%Y-%m-%d')

        domain = [
            ('move_type', '=', 'out_invoice'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<=', max_due_date)
        ]
        return await self._fetch_with_optional_limit('account.move', domain, INVOICE_FIELDS, limit)

    # =========================================================================
    # MÉTODOS DE BÚSQUEDA (normalmente devuelven pocos resultados)
    # =========================================================================

    async def search_client_by_name(self, name: str, limit: int = 5) -> list:
        """Busca clientes por nombre.

        Args:
            name: Nombre o parte del nombre del cliente a buscar.
            limit: Máximo número de resultados a devolver.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")

        domain = [('name', 'ilike', name), ('customer_rank', '>', '0')]
        return await self._fetch_batch('res.partner', domain, PARTNER_FIELDS, limit, 0)

    async def search_invoice_by_name(self, invoice_name: str) -> dict | None:
        """Busca una factura por su nombre.

        Args:
            invoice_name: Nombre de la factura a buscar.
        Returns:
            Registro de la factura si se encuentra, None en caso contrario.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")

        domain = [
            ('name', 'ilike', invoice_name),
            ('move_type', '=', 'out_invoice'),
            ('invoice_date_due', '<=', self.cutoff_date)
        ]
        records = await self._fetch_batch('account.move', domain, INVOICE_FIELDS, 1, 0)
        return records[0] if records else None

    # =========================================================================
    # MÉTODOS PARA RECUPERAR REGISTROS POR ID
    # =========================================================================

    async def get_invoice_by_id(self, invoice_id: int) -> dict | None:
        """Recupera una factura por su ID."""
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")

        domain = [
            ('id', '=', int(invoice_id)),
            ('invoice_date_due', '<=', self.cutoff_date)
        ]
        records = await self._fetch_batch('account.move', domain, INVOICE_FIELDS, 1, 0)
        return records[0] if records else None

    async def get_partner_by_id(self, partner_id: int) -> dict | None:
        """Recupera un partner por su ID."""
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")

        domain = [('id', '=', int(partner_id))]
        records = await self._fetch_batch('res.partner', domain, PARTNER_FIELDS, 1, 0)
        return records[0] if records else None

    # =========================================================================
    # MÉTODOS PARA RECUPERAR FACTURAS POR PARTNER (CRÍTICO: DEBE PAGINAR)
    # =========================================================================

    async def get_invoices_by_partner(self, partner_id: int) -> list:
        """Recupera TODAS las facturas asociadas a un partner.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")

        domain = [
            ('partner_id', '=', int(partner_id)),
            ('move_type', '=', 'out_invoice'),
            ('invoice_date_due', '<=', self.cutoff_date)
        ]
        return await self._fetch_all_parallel('account.move', domain, INVOICE_FIELDS)

    async def get_all_outbound_invoices_by_company(self, company_id: int) -> list:
        """Recupera TODAS las facturas de salida para una empresa dada."""
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")

        domain = [
            ('company_id', '=', int(company_id)),
            ('move_type', '=', 'out_invoice'),
            ('invoice_date_due', '<=', self.cutoff_date)
        ]
        return await self._fetch_all_parallel('account.move', domain, INVOICE_FIELDS)

    async def get_partners_with_overdue_invoices(self) -> list[int]:
        """Obtiene IDs de partners con facturas vencidas."""
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")

        domain = [
            ('move_type', '=', 'out_invoice'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<', self.cutoff_date)
        ]

        records = await self._fetch_all_parallel('account.move', domain, ['partner_id'])

        partner_ids = set()
        for r in records:
            pid = r['partner_id']
            if isinstance(pid, (list, tuple)):
                partner_ids.add(pid[0])
            elif pid:
                partner_ids.add(pid)

        return list(partner_ids)

    # =========================================================================
    # MÉTODOS DE CONSULTA POR FECHAS
    # =========================================================================

    async def get_invoices_by_date(self, start_date: str, end_date: str, company_id: int) -> list:
        """Recupera TODAS las facturas de una empresa dentro de un rango de fechas."""
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")

        domain = [
            ('invoice_date', '>=', start_date),
            ('invoice_date', '<=', end_date),
            ('company_id', '=', int(company_id)),
            ('move_type', '=', 'out_invoice'),
            ('invoice_date_due', '<=', self.cutoff_date)
        ]
        return await self._fetch_all_parallel('account.move', domain, INVOICE_FIELDS)

    async def get_invoices_due_between(self, start_date: str, end_date: str,
                                       only_unpaid: bool = True) -> list:
        """Recupera TODAS las facturas con vencimiento entre dos fechas."""
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")

        domain = [
            ('move_type', '=', 'out_invoice'),
            ('invoice_date_due', '>=', start_date),
            ('invoice_date_due', '<=', end_date),
        ]
        if only_unpaid:
            domain.append(('payment_state', 'in', ['not_paid', 'partial']))

        return await self._fetch_all_parallel('account.move', domain, INVOICE_FIELDS)

    async def get_invoices_by_period(self, start_date: str, end_date: str,
                                     partner_id: int = None, only_unpaid: bool = False) -> list:
        """Recupera TODAS las facturas emitidas en un período."""
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")

        domain = [
            ('move_type', '=', 'out_invoice'),
            ('invoice_date', '>=', start_date),
            ('invoice_date', '<=', end_date),
        ]
        if partner_id:
            domain.append(('partner_id', '=', partner_id))
        if only_unpaid:
            domain.append(('payment_state', 'in', ['not_paid', 'partial']))

        return await self._fetch_all_parallel('account.move', domain, INVOICE_FIELDS)
