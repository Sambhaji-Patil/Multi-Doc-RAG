"""
Embedding Management Module for Advanced RAG
Handles text encoding and embedding operations.
Uses shared model instance to reduce memory usage.
"""

import asyncio
from typing import List
from sentence_transformers import SentenceTransformer
from config.config import EMBEDDING_MODEL
from shared.model_manager import shared_model_manager
from logger.custom_logger import CustomLogger

# module logger
logger = CustomLogger().get_logger(__file__)


class EmbeddingManager:
    """Manages text embeddings for RAG operations."""
    
    def __init__(self):
        """Initialize the embedding manager with shared model."""
        self.embedding_model = None
    logger.info("RAG Embedding Manager initialized (using shared model)")
    
    @property
    def model(self) -> SentenceTransformer:
        """Get the shared embedding model."""
        return shared_model_manager.embedding_model
    
    async def encode_query(self, query: str) -> List[float]:
        """Encode a query into embeddings."""
        def encode_sync():
            embedding = self.model.encode([query], normalize_embeddings=True)
            return embedding[0].astype("float32").tolist()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, encode_sync)
    
    async def encode_texts(self, texts: List[str]) -> List[List[float]]:
        """Encode multiple texts into embeddings."""
        def encode_sync():
            embeddings = self.model.encode(texts, normalize_embeddings=True)
            return [emb.astype("float32").tolist() for emb in embeddings]
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, encode_sync)
