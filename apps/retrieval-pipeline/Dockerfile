FROM python:3.11-slim

WORKDIR /app/apps/retrieval-pipeline

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Gesamtes Repo kopieren (.dockerignore schließt node_modules/dist/.venv aus)
COPY . /app

# Runtime-Deps + Fach-Pakete (editable, wie install-all.sh)
RUN pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "uvicorn>=0.32.0" \
    "python-dotenv>=1.0.0" \
    -e /app/packages/python-common \
    -e /app/packages/python-vectordb

EXPOSE 8002

CMD ["python", "main.py"]
