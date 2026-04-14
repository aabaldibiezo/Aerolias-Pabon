# =============================================
# AEROLÍNEAS RAFAEL PABON — Dockerfile del nodo
# Mismo imagen para nodo1 (SQLServer), nodo2 (SQLServer)
# y nodo3 (MongoDB). El motor se selecciona por variable
# de entorno DB_ENGINE al arrancar.
# =============================================

FROM python:3.11-slim

WORKDIR /app

# pymssql requiere FreeTDS para conectarse a SQL Server
RUN apt-get update && apt-get install -y \
    freetds-dev \
    freetds-bin \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias primero (capa cacheada)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del nodo
COPY . .

# Exponer el puerto de la API
EXPOSE 8000

# Arrancar con uvicorn — el puerto real lo controla APP_PORT via docker-compose
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${APP_PORT:-8000} --reload"]
