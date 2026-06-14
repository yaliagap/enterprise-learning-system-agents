FROM python:3.12-slim

WORKDIR /app

# Copy project manifest and source
COPY pyproject.toml ./
COPY backend/ ./backend/

# Install dependencies — omits [local] extras (chromadb, sentence-transformers)
# because USE_REAL_IQ=true in the container uses Azure AI Search, not local ChromaDB.
RUN pip install --no-cache-dir --pre -e .

# Agent source lives under backend/ — add it to the Python path
ENV PYTHONPATH=/app/backend

EXPOSE 8000

CMD ["python", "backend/main.py"]
