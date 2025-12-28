from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class MemoryType(str, Enum):
    # Usuario dice "recuerda que X siempre paga tarde"
    CLIENT_NOTE = "client_note"
    # Preferencia del usuario (Respuestas breves)
    USER_PREFERENCE = "user_pref"
    # Situaciones graves que requieren atención (3 facturas > 30 días impagadas)
    ALERT = "alert"
    # Patrones que el LLM detecta automáticamente (Este cliente empeora sus pagos en Q3)
    INSIGHT = "insight"
    CONVERSATION_SUMMARY = "summary"  # Resumen de conversación


class Memory(BaseModel):
    """Entrada de memoria persistente."""
    id: Optional[int] = None
    memory_type: MemoryType
    content: str
    partner_id: Optional[int] = None
    partner_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None


class MemorySearchResult(BaseModel):
    """Resultado de búsqueda de memorias."""
    memories: list[Memory]
    total: int