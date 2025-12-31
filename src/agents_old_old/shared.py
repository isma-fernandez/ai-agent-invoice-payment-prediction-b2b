"""Gestión de recursos compartidos entre sub-agentes."""
from src.data.manager import DataManager
from src.agents.store import MemoryStore

_data_manager: DataManager = None
_memory_store: MemoryStore = None


def set_data_manager(dm: DataManager):
    global _data_manager
    _data_manager = dm


def get_data_manager() -> DataManager:
    if _data_manager is None:
        raise RuntimeError("DataManager no inicializado.")
    return _data_manager


def set_memory_store(ms: MemoryStore):
    global _memory_store
    _memory_store = ms


def get_memory_store() -> MemoryStore:
    if _memory_store is None:
        raise RuntimeError("MemoryStore no inicializado.")
    return _memory_store
