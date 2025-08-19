from sentence_transformers import SentenceTransformer
from config.config import EMBEDDING_MODEL
from logger.custom_logger import CustomLogger

# module-level logger
logger = CustomLogger().get_logger(__file__)
"""
Shared Model Manager - Singleton Pattern
Ensures only one instance of embedding model is loaded in memory.
"""

import threading
from typing import Optional
from sentence_transformers import SentenceTransformer
from config.config import EMBEDDING_MODEL


class SharedModelManager:
    """Singleton manager for shared embedding model."""
    
    _instance: Optional['SharedModelManager'] = None
    _lock = threading.Lock()
    _model: Optional[SentenceTransformer] = None
    _model_lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def embedding_model(self) -> SentenceTransformer:
        """Get the shared embedding model instance."""
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    logger.info("Loading shared embedding model", filename=EMBEDDING_MODEL)
                    self._model = SentenceTransformer(
                        EMBEDDING_MODEL, 
                        cache_folder=".cache"
                    )
                    logger.info("Shared embedding model loaded successfully", status="loaded")
                    print("🟢 Shared embedding model loaded successfully")
        return self._model
    
    def get_embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return self.embedding_model.get_sentence_embedding_dimension()


# Global instance
shared_model_manager = SharedModelManager()
