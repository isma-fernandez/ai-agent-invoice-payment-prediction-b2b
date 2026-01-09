from fastmcp import FastMCP
from src.agents.store import MemoryStore
from src.data.models import Memory, MemoryType

mcp = FastMCP("memory-agent-mcp")

_memory_store = None

def get_ms():
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore()
    return _memory_store

@mcp.tool()
async def save_client_note(partner_id: int, partner_name: str, note: str):
    """Guarda una nota permanente sobre un cliente.

    Usar cuando el usuario diga "recuerda que...", "anota que...",
    o cuando detectes información importante.

    Args:
        partner_id: ID del cliente.
        partner_name: Nombre del cliente.
        note: Contenido de la nota.
    """
    ms = get_ms()
    memory = Memory(
        memory_type=MemoryType.CLIENT_NOTE,
        content=note,
        partner_id=partner_id,
        partner_name=partner_name
    )
    ms.save(memory)
    return f"Nota guardada para {partner_name}: {note}"

@mcp.tool()
async def get_client_notes(partner_id: int):
    """Recupera las notas guardadas de un cliente.

    Args:
        partner_id: ID del cliente.
    """
    ms = get_ms()
    memories = ms.get_by_partner(partner_id)
    return [
        {
            "id": m.id,
            "content": m.content,
            "created_at": m.created_at.isoformat()
        }
        for m in memories
    ]

@mcp.tool()
async def save_alert(content: str, partner_id: int = None, partner_name: str = None):
    """Guarda una alerta importante que requiere atención.

    Args:
        content: Descripción de la alerta.
        partner_id: ID del cliente si aplica (opcional).
        partner_name: Nombre del cliente si aplica (opcional).
    """
    ms = get_ms()
    memory = Memory(
        memory_type=MemoryType.ALERT,
        content=content,
        partner_id=partner_id,
        partner_name=partner_name
    )
    ms.save(memory)
    return f"Alerta guardada: {content}"

@mcp.tool()
async def get_active_alerts(limit: int = 10):
    """Recupera las alertas activas del sistema.

    Args:
        limit: Máximo de alertas a devolver.
    """
    ms = get_ms()
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

if __name__ == "__main__":
    mcp.run()