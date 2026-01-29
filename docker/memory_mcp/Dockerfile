FROM python:3.13-slim

WORKDIR /app

# Dependencias de psycopg2 y para el servidor MCP
RUN apt-get update && apt-get install -y libpq-dev gcc
RUN pip install --no-cache-dir \
    fastmcp \
    psycopg2-binary \
    pydantic \
    pydantic-settings

# Copiar código compartido necesario
COPY shared/models/domain.py shared/models/domain.py
COPY shared/config/memory_mcp_settings.py shared/config/memory_mcp_settings.py

# Copiar código del servicio MCP de memoria
COPY services/memory_mcp/ services/memory_mcp/

# __init__.py vacíos para los módulos
RUN touch shared/__init__.py shared/models/__init__.py shared/config/__init__.py services/__init__.py

ENV PYTHONPATH=/app

EXPOSE 8100

CMD ["fastmcp", "run", "services/memory_mcp/server.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8100"]
