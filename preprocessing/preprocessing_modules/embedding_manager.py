"""
Embedding Manager Module

Handles creation of embeddings for text chunks using sentence transformers.
Uses shared model instance to reduce memory usage.
"""

import asyncio
import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer
from config.config import EMBEDDING_MODEL, BATCH_SIZE
from shared.model_manager import shared_model_manager


class EmbeddingManager:
    """Handles embedding creation for text chunks."""
    
    def __init__(self):
        """Initialize the embedding manager with shared model."""
        self.embedding_model = None
        print("🔗 Preprocessing Embedding Manager initialized (using shared model)")
    
    @property
    def model(self) -> SentenceTransformer:
        """Get the shared embedding model."""
        return shared_model_manager.embedding_model
    
    async def create_embeddings(self, chunks: List[str]) -> np.ndarray:
        """
        Create embeddings for text chunks.
        
        Args:
            chunks: List of text chunks to embed
            
        Returns:
            np.ndarray: Array of embeddings with shape (num_chunks, embedding_dim)
        """
        print(f"🧠 Creating embeddings for {len(chunks)} chunks")
        
        if not chunks:
            raise ValueError("No chunks provided for embedding creation")
        
        def create_embeddings_sync():
            """Synchronous embedding creation to run in thread pool."""
            embeddings = self.model.encode(
                chunks,
                batch_size=BATCH_SIZE,
                show_progress_bar=True,
                normalize_embeddings=True
            )
            return np.array(embeddings).astype("float32")
        
        # Run in thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, create_embeddings_sync)
        
        print(f"🟢-> Created embeddings with shape: {embeddings.shape}")
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by the model.
        
        Returns:
            int: Embedding dimension
        """
        return shared_model_manager.get_embedding_dimension()
    
    def validate_embeddings(self, embeddings: np.ndarray, expected_count: int) -> bool:
        """
        Validate that embeddings have the expected shape and properties.
        
        Args:
            embeddings: The embeddings array to validate
            expected_count: Expected number of embeddings
            
        Returns:
            bool: True if embeddings are valid, False otherwise
        """
        if embeddings is None:
            return False
        
        if embeddings.shape[0] != expected_count:
            print(f"❌ Embedding count mismatch: expected {expected_count}, got {embeddings.shape[0]}")
            return False
        
        if embeddings.dtype != np.float32:
            print(f"❌ Embedding dtype mismatch: expected float32, got {embeddings.dtype}")
            return False
        
        # Check for NaN or infinite values
        if np.any(np.isnan(embeddings)) or np.any(np.isinf(embeddings)):
            print("❌ Embeddings contain NaN or infinite values")
            return False
        
        print(f"🟢-> Embeddings validation passed: {embeddings.shape}")
        return True
    
    def get_model_info(self) -> dict:
        """
        Get information about the embedding model.
        
        Returns:
            dict: Model information
        """
        return {
            "model_name": EMBEDDING_MODEL,
            "embedding_dimension": shared_model_manager.get_embedding_dimension(),
            "max_sequence_length": getattr(shared_model_manager.embedding_model, 'max_seq_length', 'unknown'),
            "status": "loaded_shared"
        }
