FROM python:3.13-slim

WORKDIR /app

RUN pip install fastmcp joblib pandas numpy xgboost scikit-learn

# Modelo de predicción
COPY models/late_invoice_payment_classification.pkl models/

# Copiar código del servicio MCP de predicción
COPY services/prediction_mcp/ services/prediction_mcp/

ENV PYTHONPATH=/app

EXPOSE 8200

CMD ["fastmcp", "run", "services/prediction_mcp/server.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8200"]
