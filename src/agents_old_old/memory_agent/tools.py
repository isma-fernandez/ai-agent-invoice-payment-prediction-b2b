from langchain_core.tools import tool
from src.data.models import Memory, MemoryType
from src.agents.shared import get_memory_store


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
    ms = get_memory_store()
    memory = Memory(
        memory_type=MemoryType.CLIENT_NOTE,
        content=note,
        partner_id=partner_id,
        partner_name=partner_name
    )
    ms.save(memory)
    return f"Nota guardada para {partner_name}: {note}"


@tool
async def get_client_notes(partner_id: int) -> list[dict]:
    """Recupera las notas guardadas de un cliente.

    Args:
        partner_id: ID del cliente.
    """
    ms = get_memory_store()
    memories = ms.get_by_partner(partner_id)
    return [
        {
            "id": m.id,
            "content": m.content,
            "created_at": m.created_at.isoformat()
        }
        for m in memories
    ]


@tool
async def save_alert(content: str, partner_id: int = None, partner_name: str = None) -> str:
    """Guarda una alerta importante que requiere atención.

    Args:
        content: Descripción de la alerta.
        partner_id: ID del cliente si aplica (opcional).
        partner_name: Nombre del cliente si aplica (opcional).
    """
    ms = get_memory_store()
    memory = Memory(
        memory_type=MemoryType.ALERT,
        content=content,
        partner_id=partner_id,
        partner_name=partner_name
    )
    ms.save(memory)
    return f"Alerta guardada: {content}"


@tool
async def get_active_alerts(limit: int = 10) -> list[dict]:
    """Recupera las alertas activas del sistema.

    Args:
        limit: Máximo de alertas a devolver.
    """
    ms = get_memory_store()
    alerts = ms.get_by_type(MemoryType.ALERT, limit)
    return [
        {
            "id": a.id,
            "content": a.content,
            "partner_id": a.partner_id,
            "partner_name": a.partner_name,
            "created_at": a.created_at.isoformat()
        }
        for a in alerts
    ]


MEMORY_TOOLS = [
    save_client_note,
    get_client_notes,
    save_alert,
    get_active_alerts,
]