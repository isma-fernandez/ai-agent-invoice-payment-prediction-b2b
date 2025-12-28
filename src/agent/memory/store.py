import sqlite3
from datetime import datetime
from pathlib import Path
from .models import Memory, MemoryType
from .definitions import CREATE_TABLE_SQL


def _row_to_memory(row) -> Memory:
    """Convierte los datos obtenidos de la bsae de datos a
    objeto Memory"""
    return Memory(
        id=row[0],
        memory_type=MemoryType(row[1]),
        content=row[2],
        partner_id=row[3],
        partner_name=row[4],
        created_at=datetime.fromisoformat(row[5]),
        expires_at=datetime.fromisoformat(row[6]) if row[6] else None
    )


class MemoryStore:
    """Almacén de memoria semántica y episódica."""
    def __init__(self, db_path: str = "data/agent_memory.db"):
        """Inicializa la memoria."""
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_tables()


    def _init_tables(self):
        """Inicializa la tabla de memoria del agente"""
        self.conn.execute(CREATE_TABLE_SQL)
        self.conn.execute("""CREATE INDEX IF NOT EXISTS idx_partner ON memories(partner_id)""")
        self.conn.execute("""CREATE INDEX IF NOT EXISTS idx_type ON memories(memory_type)""")
        self.conn.commit()


    def save(self, memory: Memory) -> int:
        """Guarda una memoria y devuelve su ID."""
        cursor = self.conn.execute("""
            INSERT INTO memories (memory_type, content, partner_id, partner_name, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
    (
                memory.memory_type.value,
                memory.content,
                memory.partner_id,
                memory.partner_name,
                memory.created_at.isoformat(),
                memory.expires_at.isoformat() if memory.expires_at else None
            ))
        self.conn.commit()
        return cursor.lastrowid


    def get_by_partner(self, partner_id: int, limit: int = 10) -> list[Memory]:
        """Obtiene memorias de un cliente específico."""
        cursor = self.conn.execute("""
            SELECT id, memory_type, content, partner_id, partner_name, created_at, expires_at
            FROM memories
            WHERE partner_id = ?
            AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY created_at DESC LIMIT ?""",
        (partner_id, datetime.now().isoformat(), limit))
        return [_row_to_memory(row) for row in cursor.fetchall()]


    def get_by_type(self, memory_type: MemoryType, limit: int = 10) -> list[Memory]:
        """Obtiene memorias por tipo."""
        cursor = self.conn.execute("""
            SELECT id, memory_type, content, partner_id, partner_name, created_at, expires_at
            FROM memories
            WHERE memory_type = ?
            AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY created_at DESC LIMIT ?""",
            (memory_type.value, datetime.now().isoformat(), limit))
        return [_row_to_memory(row) for row in cursor.fetchall()]


    def get_recent(self, limit: int = 20) -> list[Memory]:
        """Obtiene las memorias más recientes."""
        cursor = self.conn.execute("""
            SELECT id, memory_type, content, partner_id, partner_name, created_at, expires_at
            FROM memories
            WHERE expires_at IS NULL
            OR expires_at > ?
            ORDER BY created_at DESC LIMIT ?
        """, (datetime.now().isoformat(), limit))
        return [_row_to_memory(row) for row in cursor.fetchall()]


    def search(self, query: str, limit: int = 10) -> list[Memory]:
        """Búsqueda simple por contenido."""
        cursor = self.conn.execute("""
            SELECT id, memory_type, content, partner_id, partner_name, created_at, expires_at
            FROM memories
            WHERE content LIKE ?
            AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY created_at DESC LIMIT ?
        """, (f"%{query}%", datetime.now().isoformat(), limit))
        return [_row_to_memory(row) for row in cursor.fetchall()]


    def delete(self, memory_id: int) -> bool:
        """Elimina una memoria por ID."""
        cursor = self.conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.conn.commit()
        return cursor.rowcount > 0
