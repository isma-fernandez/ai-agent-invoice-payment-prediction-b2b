FROM python:3.12-slim

WORKDIR /app

RUN pip install fastmcp joblib pandas xgboost scikit-learn \
    pydantic pydantic-settings

# Modelo de predicción
COPY models/late_invoice_payment_classification.pkl models/

# MCP del modelo
COPY src/mcp/prediction_server.py src/mcp/
COPY src/config/prediction_mcp_settings.py src/config/

# Crear __init__.py para evitar dependencias de los de src
RUN touch src/__init__.py src/mcp/__init__.py src/config/__init__.py

ENV PYTHONPATH=/app

EXPOSE 8200

CMD ["fastmcp", "run", "src/mcp/prediction_server.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8200"]
