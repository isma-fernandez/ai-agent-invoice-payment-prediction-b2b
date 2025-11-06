from src.data.data_retriever_old import DataRetriever
from src.data.odoo_connector import OdooConnection
import asyncio


def main():
    odoo_connection = OdooConnection()
    asyncio.run(odoo_connection.connect())
    data_retriever = DataRetriever(odoo_connection=odoo_connection)
    company_id = 5
    invoices = asyncio.run(data_retriever.get_all_outbound_invoices(company_id))
    for invoice in invoices:
        print(f"id: {invoice.id} , date: {invoice.invoice_date}")
        print("\n")

if __name__ == "__main__":
    main()