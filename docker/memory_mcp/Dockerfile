FROM python:3.12-slim

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
COPY src/agents/__init__.py src/agents/
COPY src/data/models.py src/data/
COPY src/data/__init__.py src/data/
COPY src/__init__.py src/

# Puerto servidor MCP
EXPOSE 8100

CMD ["python", "-m", "fastmcp", "run", "src/mcp/memory_agent_server.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8100"]
