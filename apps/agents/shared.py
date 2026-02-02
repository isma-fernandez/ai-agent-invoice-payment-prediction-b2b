from shared.data.manager import DataManager

_data_manager: DataManager = None


def set_data_manager(dm: DataManager):
    """Establece el DataManager compartido entre agentes."""
    global _data_manager
    _data_manager = dm


def get_data_manager() -> DataManager:
    """Obtiene el DataManager compartido entre agentes.
    
    Returns:
        DataManager inicializado.

    Raises:
        RuntimeError: Si el DataManager no ha sido inicializado.
    """
    if _data_manager is None:
        raise RuntimeError("DataManager no inicializado.")
    return _data_manager
