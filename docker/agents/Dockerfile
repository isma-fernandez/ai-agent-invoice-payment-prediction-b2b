FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y libpq-dev gcc

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

ENV PYTHONPATH=/app
ENV AGENT_TYPE=orchestrator

EXPOSE 8004

# Dependiendo del agente se ejecuta un servicio API diferente
CMD ["sh", "-c", "\
    if [ \"$AGENT_TYPE\" = 'orchestrator' ]; then \
        python -m src.api.main; \
    elif [ \"$AGENT_TYPE\" = 'data_agent' ]; then \
        python -m src.a2a.services.data_agent_service; \
    elif [ \"$AGENT_TYPE\" = 'analysis_agent' ]; then \
        python -m src.a2a.services.analysis_agent_service; \
    elif [ \"$AGENT_TYPE\" = 'memory_agent' ]; then \
        python -m src.a2a.services.memory_agent_service; \
    else \
        echo 'Unknown AGENT_TYPE: $AGENT_TYPE' && exit 1; \
    fi \
"]
