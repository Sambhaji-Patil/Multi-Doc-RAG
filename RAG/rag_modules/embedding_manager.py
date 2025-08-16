"""
Embedding Management Module for Advanced RAG
Handles text encoding and embedding operations.
"""

import asyncio
from typing import List
from sentence_transformers import SentenceTransformer
from config.config import EMBEDDING_MODEL


class EmbeddingManager:
    """Manages text embeddings for RAG operations."""
    
    def __init__(self):
        """Initialize the embedding manager."""
        self.embedding_model = None
        self._init_embedding_model()
    
    def _init_embedding_model(self):
        """Initialize the embedding model."""
        print(f"🔄 Loading embedding model: {EMBEDDING_MODEL}")
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL , cache_folder=".cache")
        print(f"✅ Embedding model loaded successfully")
    
    async def encode_query(self, query: str) -> List[float]:
        """Encode a query into embeddings."""
        def encode_sync():
            embedding = self.embedding_model.encode([query], normalize_embeddings=True)
            return embedding[0].astype("float32").tolist()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, encode_sync)
    
    async def encode_texts(self, texts: List[str]) -> List[List[float]]:
        """Encode multiple texts into embeddings."""
        def encode_sync():
            embeddings = self.embedding_model.encode(texts, normalize_embeddings=True)
            return [emb.astype("float32").tolist() for emb in embeddings]
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, encode_sync)
