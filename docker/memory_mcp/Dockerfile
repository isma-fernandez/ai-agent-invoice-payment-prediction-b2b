FROM python:3.13-slim

WORKDIR /app

# Dependenciaks de psycopg2 y para el servidor MCP
RUN apt-get update && apt-get install -y libpq-dev gcc
RUN pip install --no-cache-dir \
    fastmcp \
    psycopg2-binary \
    pydantic \
    pydantic-settings

# Archivos necesarios para el servidor MCP
COPY src/mcp/memory_agent_server.py src/mcp/
COPY src/agents/store.py src/agents/
COPY src/data/models.py src/data/
COPY src/config/memory_mcp_settings.py src/config/

# __init__.py vacíos, los de src tienen dependencias que no usa el servidor
RUN touch src/__init__.py src/agents/__init__.py src/data/__init__.py src/config/__init__.py src/mcp/__init__.py

ENV PYTHONPATH=/app

EXPOSE 8100

CMD ["fastmcp", "run", "src/mcp/memory_agent_server.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8100"]
