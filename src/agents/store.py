import psycopg2
from datetime import datetime
from src.data.models import Memory, MemoryType
from src.config.memory_mcp_settings import memory_settings


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
    """Almacén de memoria en PostgreSQL."""

    def __init__(self):
        """Inicializa la conexión a PostgreSQL"""
        self.conn = psycopg2.connect(
            host=memory_settings.POSTGRES_HOST,
            port=memory_settings.POSTGRES_PORT,
            user=memory_settings.POSTGRES_USER,
            password=memory_settings.POSTGRES_PASSWORD,
            dbname=memory_settings.POSTGRES_DB
        )
        self.conn.autocommit = False

    def save(self, memory: Memory) -> int:
        """Guarda una memoria y devuelve su ID."""
        with self.conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO memories (memory_type, content, partner_id, partner_name, created_at, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id""",
                (
                    memory.memory_type.value,
                    memory.content,
                    memory.partner_id,
                    memory.partner_name,
                    memory.created_at,
                    memory.expires_at
                )
            )
            memory_id = cursor.fetchone()[0]
            self.conn.commit()
            return memory_id

    def get_by_partner(self, partner_id: int, limit: int = 10) -> list[Memory]:
        """Obtiene memorias de un cliente específico."""
        with self.conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, memory_type, content, partner_id, partner_name, created_at, expires_at
                FROM memories
                WHERE partner_id = %s
                AND (expires_at IS NULL OR expires_at > %s)
                ORDER BY created_at DESC
                LIMIT %s""",
                (partner_id, datetime.now(), limit)
            )
            return [_row_to_memory(row) for row in cursor.fetchall()]

    def get_by_type(self, memory_type: MemoryType, limit: int = 10) -> list[Memory]:
        """Obtiene memorias por tipo."""
        with self.conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, memory_type, content, partner_id, partner_name, created_at, expires_at
                FROM memories
                WHERE memory_type = %s
                AND (expires_at IS NULL OR expires_at > %s)
                ORDER BY created_at DESC
                LIMIT %s""",
                (memory_type.value, datetime.now(), limit)
            )
            return [_row_to_memory(row) for row in cursor.fetchall()]

    def get_recent(self, limit: int = 20) -> list[Memory]:
        """Obtiene las memorias más recientes."""
        with self.conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, memory_type, content, partner_id, partner_name, created_at, expires_at
                FROM memories
                WHERE expires_at IS NULL OR expires_at > %s
                ORDER BY created_at DESC
                LIMIT %s""",
                (datetime.now(), limit)
            )
            return [_row_to_memory(row) for row in cursor.fetchall()]

    def search(self, query: str, limit: int = 10) -> list[Memory]:
        """Búsqueda simple por contenido."""
        with self.conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, memory_type, content, partner_id, partner_name, created_at, expires_at
                FROM memories
                WHERE content ILIKE %s
                AND (expires_at IS NULL OR expires_at > %s)
                ORDER BY created_at DESC
                LIMIT %s""",
                (f"%{query}%", datetime.now(), limit)
            )
            return [_row_to_memory(row) for row in cursor.fetchall()]

    def delete(self, memory_id: int) -> bool:
        """Elimina una memoria por ID."""
        with self.conn.cursor() as cursor:
            cursor.execute("DELETE FROM memories WHERE id = %s", (memory_id,))
            deleted = cursor.rowcount > 0
            self.conn.commit()
            return deleted

    def close(self):
        """Cierra la conexión a la base de datos."""
        if self.conn:
            self.conn.close()
