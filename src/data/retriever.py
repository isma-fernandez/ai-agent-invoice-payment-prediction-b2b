from src.utils.odoo_connector import OdooConnection
from .config import INVOICE_FIELDS, PARTNER_FIELDS, BATCH_SIZE
import pandas as pd

class DataRetriever:
    def __init__(self, odoo_connection: OdooConnection, cutoff_date: str = None):
        self.odoo_connection = odoo_connection
        self.cutoff_date = cutoff_date


    """  MÉTODOS PARA RECUPERAR TODOS LOS REGISTROS DE UN MODELO """


    async def get_all_outbound_invoices(self):
        """
        Recupera todas las facturas de salida (outbound) de todas las empresas.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        all_records = []
        offset = 0
        while True:
            records = await self.odoo_connection.search_read('account.move', 
                                                             [
                                                                 ('move_type', '=', 'out_invoice'),
                                                                 ('invoice_date_due', '<=', self.cutoff_date)
                                                             ], INVOICE_FIELDS, BATCH_SIZE, offset)
            if not records:
                break
            all_records.extend(records)
            if (offset // BATCH_SIZE) % 5 == 0:
                print(f"Recuperadas {len(records)} facturas, total: {len(all_records)}")
            offset += BATCH_SIZE
        return all_records


    async def search_client_by_name(self, name: str, limit: int = 5):
        """
        Busca clientes por nombre.

        Args:
            name (str): Nombre o parte del nombre del cliente a buscar.
            limit (int): Máximo número de resultados a devolver.
        Returns:
            list: Lista de registros de clientes que coinciden con el nombre dado.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        
        domain = [('name', 'ilike', name), ('customer_rank', '>', '0')]
        records = await self.odoo_connection.search_read(
            model='res.partner', 
            domain=domain, 
            fields=PARTNER_FIELDS, 
            limit=limit
        )
        return records


    async def search_invoice_by_name(self, invoice_name: str):
        """
        Busca una factura por su nombre.

        Args:
            invoice_name (str): Nombre de la factura a buscar.
        Returns:
            dict | None: Registro de la factura si se encuentra, None en caso contrario.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        
        domain = [('name', 'ilike', invoice_name), ('move_type', '=', 'out_invoice'), ('invoice_date_due', '<=', self.cutoff_date)]
        records = await self.odoo_connection.search_read(
            model='account.move', 
            domain=domain, 
            fields=INVOICE_FIELDS, 
            limit=1
        )
        if records:
            return records[0]
        return None


    async def get_all_outbound_invoices_by_company(self, company_id: int):
        """
        Recupera todas las facturas de salida para una empresa dada.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        domain = [('company_id', '=', int(company_id)),
                  ('move_type', '=', 'out_invoice'),
                  ('invoice_date_due', '<=', self.cutoff_date)]
        all_records = []
        offset = 0
        while True:
            records = await self.odoo_connection.search_read('account.move', domain, INVOICE_FIELDS, BATCH_SIZE, offset)
            if not records:
                break
            all_records.extend(records)
            if (offset // BATCH_SIZE) % 5 == 0:
                print(f"Recuperadas {len(records)} facturas, total: {len(all_records)}")
            offset += BATCH_SIZE
        return all_records


    async def get_all_unpaid_invoices(self, limit: int = 0) -> list:
        """Recupera todas las facturas pendientes de pago."""
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")

        domain = [
            ('move_type', '=', 'out_invoice'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<=', self.cutoff_date)
        ]

        return await self.odoo_connection.search_read('account.move', domain, INVOICE_FIELDS, limit=limit)


    async def get_all_customer_partners(self):
        """
        Recupera todos los partners (clientes/proveedores).
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        all_records = []
        offset = 0
        while True:
            records = await self.odoo_connection.search_read('res.partner', [('customer_rank', '>', '0')], PARTNER_FIELDS, BATCH_SIZE, offset)
            if not records:
                break
            all_records.extend(records)
            if (offset // BATCH_SIZE) % 5 == 0:
                print(f"Recuperadas {len(records)} facturas, total: {len(all_records)}")
            offset += BATCH_SIZE
        return all_records


    async def get_all_overdue_invoices(self, min_days_overdue: int = 1, limit: int = 50):
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")

        cutoff = pd.Timestamp(self.cutoff_date)
        max_due_date = (cutoff - pd.Timedelta(days=min_days_overdue)).strftime('%Y-%m-%d')

        domain = [
            ('move_type', '=', 'out_invoice'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<=', max_due_date)
        ]

        return await self.odoo_connection.search_read('account.move', domain, INVOICE_FIELDS, limit=limit)


    """ MÉTODOS PARA RECUPERAR REGISTROS ESPECÍFICOS POR ID """


    async def get_partners_with_overdue_invoices(self) -> list[int]:
        """Obtiene IDs de partners con facturas vencidas."""
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")

        domain = [
            ('move_type', '=', 'out_invoice'),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('invoice_date_due', '<', self.cutoff_date)
        ]

        records = await self.odoo_connection.search_read('account.move', domain, ['partner_id'], limit=0)

        partner_ids = set()
        for r in records:
            pid = r['partner_id']
            if isinstance(pid, (list, tuple)):
                partner_ids.add(pid[0])
            elif pid:
                partner_ids.add(pid)

        return list(partner_ids)


    async def get_invoice_by_id(self, invoice_id: int):
        """
        Recupera una factura por su ID.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        domain = [('id', '=', int(invoice_id)),
                  ('invoice_date_due', '<=', self.cutoff_date)]
        invoice = await self.odoo_connection.search_read('account.move', domain, INVOICE_FIELDS)
        if invoice:
            return invoice[0]
        return None


    async def get_partner_by_id(self, partner_id: int):
        """
        Recupera un partner por su ID.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        domain = [('id', '=', int(partner_id))]
        partner = await self.odoo_connection.search_read('res.partner', domain, PARTNER_FIELDS)
        if partner:
            return partner[0]
        return None
    

    """ MÉTODOS ADICIONALES SEGÚN NECESIDAD """


    async def get_invoices_by_partner(self, partner_id: int):
        """
        Recupera todas las facturas asociadas a un partner (cliente/proveedor).
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        domain = [('partner_id', '=', int(partner_id)), ('move_type', '=', 'out_invoice'), ('invoice_date_due', '<=', self.cutoff_date)]
        records = await self.odoo_connection.search_read('account.move', domain, INVOICE_FIELDS, 0)
        return records


    async def get_invoices_by_date(self, start_date: str, end_date: str, company_id: int):
        """
        Recupera todas las facturas de una empresa dentro de un rango de fechas.
        """
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")
        domain = [('invoice_date', '>=', start_date), ('invoice_date', '<=', end_date),
                  ('company_id', '=', int(company_id)), ('move_type', '=', 'out_invoice'),
                  ('invoice_date_due', '<=', self.cutoff_date)]
        records = await self.odoo_connection.search_read('account.move', domain, INVOICE_FIELDS, 0)
        return records


    async def get_invoices_due_between(self, start_date: str, end_date: str, only_unpaid: bool = True) -> list:
        """Recupera facturas con vencimiento entre dos fechas."""
        if self.odoo_connection.client is None:
            raise Exception("El cliente no está conectado a Odoo.")

        domain = [
            ('move_type', '=', 'out_invoice'),
            ('invoice_date_due', '>=', start_date),
            ('invoice_date_due', '<=', end_date),
        ]
        if only_unpaid:
            domain.append(('payment_state', 'in', ['not_paid', 'partial']))

        return await self.odoo_connection.search_read('account.move', domain, INVOICE_FIELDS, limit=0)


    async def get_invoices_by_period(self, start_date: str, end_date: str,
                                     partner_id: int = None, only_unpaid: bool = False) -> list:
        """Recupera facturas emitidas en un período."""
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

        return await self.odoo_connection.search_read('account.move', domain, INVOICE_FIELDS, limit=0)
