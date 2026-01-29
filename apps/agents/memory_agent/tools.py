from langchain_core.tools import tool
from shared.clients.memory_client import get_memory_client


@tool
async def save_client_note(partner_id: int, partner_name: str, note: str) -> str:
    """Guarda una nota permanente sobre un cliente.

    Usar cuando el usuario diga "recuerda que...", "anota que...",
    o cuando detectes información importante.

    Args:
        partner_id: ID del cliente.
        partner_name: Nombre del cliente.
        note: Contenido de la nota.
    """
    client = get_memory_client()
    return await client.save_client_note(partner_id, partner_name, note)


@tool
async def get_client_notes(partner_id: int) -> list[dict]:
    """Recupera las notas guardadas de un cliente.

    Args:
        partner_id: ID del cliente.
    """
    client = get_memory_client()
    return await client.get_client_notes(partner_id)


@tool
async def save_alert(content: str, partner_id: int = None, partner_name: str = None) -> str:
    """Guarda una alerta importante que requiere atención.

    Args:
        content: Descripción de la alerta.
        partner_id: ID del cliente si aplica (opcional).
        partner_name: Nombre del cliente si aplica (opcional).
    """
    client = get_memory_client()
    return await client.save_alert(content, partner_id, partner_name)


@tool
async def get_active_alerts(limit: int = 10) -> list[dict]:
    """Recupera las alertas activas del sistema.

    Args:
        limit: Máximo de alertas a devolver.
    """
    client = get_memory_client()
    return await client.get_active_alerts(limit)


@tool
async def delete_note(note_id: int) -> str:
    """Elimina una nota o alerta por su ID.

    Primero usa get_client_notes para obtener los IDs de las notas.

    Args:
        note_id: ID de la nota a eliminar.
    """
    client = get_memory_client()
    return await client.delete_note(note_id)


MEMORY_TOOLS = [
    save_client_note,
    get_client_notes,
    save_alert,
    get_active_alerts,
    delete_note,
]
