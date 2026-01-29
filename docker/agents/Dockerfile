FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y libpq-dev gcc

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código compartido y aplicaciones
COPY shared/ shared/
COPY apps/ apps/

ENV PYTHONPATH=/app
ENV AGENT_TYPE=orchestrator

EXPOSE 8004

# Dependiendo del agente se ejecuta un servicio API diferente
CMD ["sh", "-c", "\
    if [ \"$AGENT_TYPE\" = 'orchestrator' ]; then \
        python -m apps.orchestrator.main; \
    elif [ \"$AGENT_TYPE\" = 'data_agent' ]; then \
        python -m apps.agents.data_agent.service; \
    elif [ \"$AGENT_TYPE\" = 'analysis_agent' ]; then \
        python -m apps.agents.analysis_agent.service; \
    elif [ \"$AGENT_TYPE\" = 'memory_agent' ]; then \
        python -m apps.agents.memory_agent.service; \
    else \
        echo 'Unknown AGENT_TYPE: $AGENT_TYPE' && exit 1; \
    fi \
"]
