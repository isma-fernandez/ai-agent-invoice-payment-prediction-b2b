from langchain_core.tools import tool
from src.data.manager import DataManager
from src.data.models import *
from src.agent.memory.store import MemoryStore
from src.agent.memory.models import Memory, MemoryType

data_manager: DataManager = None
memory_store: MemoryStore = None


async def initialize_data_manager(model_path: str = None):
    """Inicializa el DataManager. Llamar antes de usar las tools."""
    global data_manager, memory_store
    data_manager = DataManager(cutoff_date="2025-01-01")
    await data_manager.connect()
    #TODO: reactivar
    #if model_path:
        #data_manager.load_model(model_path)
    memory_store = MemoryStore()



#
# ======================= MEMORY TOOLS ===============================
#


tools = [
    search_client,
    get_client_info,
    get_client_invoices,
    get_invoice_by_name,
    predict_invoice_risk,
    predict_hypothetical_invoice,
    check_connection,
    get_overdue_invoices,
    get_high_risk_clients,
    compare_clients,
    get_upcoming_due_invoices,
    get_aging_report,
    get_portfolio_summary,
    get_client_trend,
    get_deteriorating_clients,
    get_invoices_by_period,
    save_client_note,
    get_client_notes,
    save_alert,
    get_active_alerts,
]
