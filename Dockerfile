FROM python:3.12-slim

WORKDIR /app

# Install git (required by git tools)
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cache — only re-runs if requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Pre-download the embedding model so the container doesn't fetch it at runtime
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Railway injects PORT; default to 8000 locally
ENV PORT=8000
ENV TRANSPORT=sse
ENV HOST=0.0.0.0

EXPOSE ${PORT}

CMD ["python", "server.py"]
