#!/bin/bash

echo "=== RAG System Startup ==="

# Check if RAG/rag_embeddings directory exists
if [ -d "RAG/rag_embeddings" ]; then
    echo "✅ RAG/rag_embeddings directory found"
    
    # Copy database files to writable /tmp directory
    echo "📁 Copying databases to writable location..."
    mkdir -p /tmp/rag_embeddings
    cp -r RAG/rag_embeddings/* /tmp/rag_embeddings/
    
    # Remove any lock files from the copied databases
    find /tmp/rag_embeddings -name "*.lock" -delete 2>/dev/null || true
    find /tmp/rag_embeddings -name "*.db-shm" -delete 2>/dev/null || true
    find /tmp/rag_embeddings -name "*.db-wal" -delete 2>/dev/null || true
    
    # Set environment variable to use writable location
    export RAG_EMBEDDINGS_PATH="/tmp/rag_embeddings"
    
    echo "✅ Databases copied to writable location: /tmp/rag_embeddings"
else
    echo "❌ RAG/rag_embeddings directory not found"
fi

echo "✅ Database directories ready"


# Start the application
echo "🚀 Starting RAG API..."
python app.py
