FROM python:3.12-slim

WORKDIR /app

# Install git (required by git tools)
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install CPU-only torch first to avoid pulling 3GB+ of CUDA GPU libraries.
# The --index-url flag tells pip to fetch torch from the lightweight CPU wheel repo.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies (sentence-transformers, mcp, etc.)
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Allow git to operate on /app regardless of file ownership (safe.directory)
RUN git config --system --add safe.directory /app

# Pre-download the embedding model so the container doesn't fetch it at runtime
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

ENV PORT=8000
ENV TRANSPORT=sse
ENV HOST=0.0.0.0

EXPOSE ${PORT}

CMD ["python", "server.py"]
