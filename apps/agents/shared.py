"""Gestión de recursos compartidos entre sub-agentes."""
from shared.data.manager import DataManager

_data_manager: DataManager = None


def set_data_manager(dm: DataManager):
    global _data_manager
    _data_manager = dm


def get_data_manager() -> DataManager:
    if _data_manager is None:
        raise RuntimeError("DataManager no inicializado.")
    return _data_manager
