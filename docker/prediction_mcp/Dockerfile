FROM python:3.13-slim

WORKDIR /app

RUN pip install fastmcp joblib pandas numpy xgboost scikit-learn

# Modelo de predicción
COPY models/late_invoice_payment_classification.pkl models/


COPY docker/prediction_mcp/app/ app/

ENV PYTHONPATH=/app

EXPOSE 8200

CMD ["fastmcp", "run", "app/server.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8200"]
