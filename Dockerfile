FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* 

# Create cache directories with proper permissions before copying files
RUN mkdir -p /app/.cache/huggingface && \
    mkdir -p /app/.cache/sentence_transformers && \
    chmod -R 777 /app/.cache

# Set environment variables for HuggingFace cache (before installing packages)
ENV HF_HOME=/app/.cache/huggingface
ENV TRANSFORMERS_CACHE=/app/.cache/huggingface
ENV SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence_transformers
ENV HF_HUB_CACHE=/app/.cache/huggingface

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files AND folder structure
COPY *.py ./
COPY *.sh ./
COPY requirements.txt ./
COPY *.md ./
COPY api/ ./api/
COPY config/ ./config/
COPY LLM/ ./LLM/
COPY RAG/ ./RAG/
COPY logger/ ./logger/
COPY preprocessing/ ./preprocessing/

# Set up directories and permissions during build (when we have root access)
RUN mkdir -p /app/.cache/huggingface && \
    mkdir -p /app/.cache/sentence_transformers && \
    chmod -R 777 /app/.cache && \
    chmod +x startup.sh && \
    if [ -d "RAG/rag_embeddings" ]; then \
        find RAG/rag_embeddings -name "*.lock" -delete 2>/dev/null || true; \
        find RAG/rag_embeddings -name "*.db-shm" -delete 2>/dev/null || true; \
        find RAG/rag_embeddings -name "*.db-wal" -delete 2>/dev/null || true; \
        chmod -R 755 RAG/rag_embeddings; \
    fi

# Expose port
EXPOSE 7860

# Set environment variables
ENV HOST=0.0.0.0
ENV PORT=7860

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Run the application
CMD ["bash", "startup.sh"]
