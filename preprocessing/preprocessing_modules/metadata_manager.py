"""
Metadata Manager Module - Modified for Unified Collection

Handles document metadata storage and retrieval operations
for unified collection architecture.
"""

import json
import asyncio
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path
from config.config import EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP
from logger.custom_logger import CustomLogger

# module logger
logger = CustomLogger().get_logger(__file__)


class MetadataManager:
    """Handles document metadata operations for unified collection."""
    
    def __init__(self, base_db_path: Path, collection_name: str = "unified_documents"):
        """
        Initialize the metadata manager.
        
        Args:
            base_db_path: Base path for storing metadata files
            collection_name: Name of the unified collection
        """
        self.base_db_path = base_db_path
        self.collection_name = collection_name
        self.processed_docs_file = self.base_db_path / "processed_documents.json"
        self.unified_collection_info_file = self.base_db_path / f"{collection_name}_info.json"
        self.processed_docs = self._load_processed_docs()
        self.collection_info = self._load_collection_info()
    
    def _load_processed_docs(self) -> Dict[str, Dict]:
        """Load the registry of processed documents."""
        if self.processed_docs_file.exists():
            try:
                with open(self.processed_docs_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Could not load processed docs registry", error=str(e))
        return {}
    
    def _save_processed_docs(self):
        """Save the registry of processed documents."""
        try:
            with open(self.processed_docs_file, 'w', encoding='utf-8') as f:
                json.dump(self.processed_docs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning("Could not save processed docs registry", error=str(e))
    
    def _load_collection_info(self) -> Dict[str, Any]:
        """Load unified collection information."""
        if self.unified_collection_info_file.exists():
            try:
                with open(self.unified_collection_info_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Could not load collection info", error=str(e))
        
        # Return default collection info structure
        return {
            "collection_name": self.collection_name,
            "created_at": asyncio.get_event_loop().time(),
            "total_documents": 0,
            "total_chunks": 0,
            "last_updated": asyncio.get_event_loop().time(),
            "embedding_model": EMBEDDING_MODEL,
            "processing_config": {
                "chunk_size": CHUNK_SIZE,
                "chunk_overlap": CHUNK_OVERLAP,
                "embedding_model": EMBEDDING_MODEL
            }
        }
    
    def _save_collection_info(self):
        """Save unified collection information."""
        try:
            with open(self.unified_collection_info_file, 'w', encoding='utf-8') as f:
                json.dump(self.collection_info, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning("Could not save collection info", error=str(e))
    
    def generate_doc_id(self, document_url: str) -> str:
        """
        Generate a unique document ID from the URL.
        """
        url_hash = hashlib.md5(document_url.encode()).hexdigest()[:12]
        return f"doc_{url_hash}"
    
    def is_document_processed(self, document_url: str) -> bool:
        """
        Check if a document has already been processed.
        """
        doc_id = self.generate_doc_id(document_url)
        return doc_id in self.processed_docs
    
    def get_document_info(self, document_url: str) -> Dict[str, Any]:
        """
        Get information about a processed document.
        """
        doc_id = self.generate_doc_id(document_url)
        return self.processed_docs.get(doc_id, {})
    
    def save_document_metadata(self, chunks: List[str], doc_id: str, document_url: str):
        """
        Save document metadata to JSON file and update registries.
        
        Args:
            chunks: List of text chunks
            doc_id: Document identifier
            document_url: Original document URL
        """
        # Calculate statistics
        total_chars = sum(len(chunk) for chunk in chunks)
        total_words = sum(len(chunk.split()) for chunk in chunks)
        avg_chunk_size = total_chars / len(chunks) if chunks else 0
        current_time = asyncio.get_event_loop().time()
        
        # Create metadata object
        metadata = {
            "doc_id": doc_id,
            "document_url": document_url,
            "chunk_count": len(chunks),
            "total_chars": total_chars,
            "total_words": total_words,
            "avg_chunk_size": avg_chunk_size,
            "processed_at": current_time,
            "embedding_model": EMBEDDING_MODEL,
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
            "collection_name": self.collection_name,  # Updated: unified collection
            "processing_config": {
                "chunk_size": CHUNK_SIZE,
                "chunk_overlap": CHUNK_OVERLAP,
                "embedding_model": EMBEDDING_MODEL
            }
        }
        
        # Save individual document metadata
        metadata_path = self.base_db_path / f"{doc_id}_metadata.json"
        try:
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            logger.info("Saved individual metadata", doc_id=doc_id)
        except Exception as e:
            logger.warning("Could not save individual metadata", doc_id=doc_id, error=str(e))
        
        # Check if this is a new document or update
        is_new_document = doc_id not in self.processed_docs
        
        # Update processed documents registry
        self.processed_docs[doc_id] = {
            "document_url": document_url,
            "chunk_count": len(chunks),
            "processed_at": current_time,
            "collection_name": self.collection_name,  # Updated: unified collection
            "total_chars": total_chars,
            "total_words": total_words,
            "status": "processed"
        }
        self._save_processed_docs()
        
        # Update unified collection info
        if is_new_document:
            self.collection_info["total_documents"] += 1
        
        # Recalculate total chunks (in case of reprocessing)
        self.collection_info["total_chunks"] = sum(
            doc_info.get("chunk_count", 0) for doc_info in self.processed_docs.values()
        )
        self.collection_info["last_updated"] = current_time
        self._save_collection_info()
        
        logger.info("Updated registry for document in unified collection", doc_id=doc_id)
    
    def get_document_metadata(self, doc_id: str) -> Dict[str, Any]:
        """
        Load individual document metadata from file.
        """
        metadata_path = self.base_db_path / f"{doc_id}_metadata.json"
        
        if not metadata_path.exists():
            return {}
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Could not load metadata", doc_id=doc_id, error=str(e))
            return {}
    
    def list_processed_documents(self) -> Dict[str, Dict]:
        """
        List all processed documents.
        Returns:
            Dict[str, Dict]: Copy of processed documents registry
        """
        return self.processed_docs.copy()
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the unified collection.
        
        Returns:
            Dict[str, Any]: Collection statistics
        """
        # Check if unified collection database exists
        unified_db_path = self.base_db_path / f"{self.collection_name}.db"
        collection_exists = unified_db_path.exists()
        
        stats = {
            "collection_name": self.collection_name,
            "collection_exists": collection_exists,
            "collection_path": str(unified_db_path),
            "total_documents": len(self.processed_docs),
            "total_chunks": 0,
            "total_characters": 0,
            "total_words": 0,
            "documents": [],
            "last_updated": self.collection_info.get("last_updated", "unknown"),
            "embedding_model": self.collection_info.get("embedding_model", EMBEDDING_MODEL)
        }
        
        # Calculate totals from processed documents
        for doc_id, info in self.processed_docs.items():
            stats["total_chunks"] += info.get("chunk_count", 0)
            stats["total_characters"] += info.get("total_chars", 0)
            stats["total_words"] += info.get("total_words", 0)
            
            stats["documents"].append({
                "doc_id": doc_id,
                "url": info["document_url"],
                "chunk_count": info.get("chunk_count", 0),
                "total_chars": info.get("total_chars", 0),
                "total_words": info.get("total_words", 0),
                "processed_at": info.get("processed_at", "unknown"),
                "status": info.get("status", "unknown")
            })
        
        # Add averages
        if stats["total_documents"] > 0:
            stats["avg_chunks_per_doc"] = stats["total_chunks"] / stats["total_documents"]
            stats["avg_chars_per_doc"] = stats["total_characters"] / stats["total_documents"]
            stats["avg_words_per_doc"] = stats["total_words"] / stats["total_documents"]
        
        # Add collection configuration
        stats["processing_config"] = self.collection_info.get("processing_config", {})
        
        return stats
    
    def remove_document_metadata(self, doc_id: str) -> bool:
        """
        Remove document metadata and registry entry.
        Note: This only removes metadata. The actual vector data should be 
        removed using VectorStorage.delete_document().
        
        Args:
            doc_id: Document identifier
            
        Returns:
            bool: True if successfully removed, False otherwise
        """
        try:
            # Remove individual metadata file
            metadata_path = self.base_db_path / f"{doc_id}_metadata.json"
            if metadata_path.exists():
                metadata_path.unlink()
                logger.info("Removed metadata file", doc_id=doc_id)
            
            # Remove from registry and update collection info
            if doc_id in self.processed_docs:
                # Update collection totals
                doc_info = self.processed_docs[doc_id]
                self.collection_info["total_documents"] = max(0, self.collection_info.get("total_documents", 1) - 1)
                
                # Remove from registry
                del self.processed_docs[doc_id]
                self._save_processed_docs()
                
                # Recalculate total chunks
                self.collection_info["total_chunks"] = sum(
                    doc_info.get("chunk_count", 0) for doc_info in self.processed_docs.values()
                )
                self.collection_info["last_updated"] = asyncio.get_event_loop().time()
                self._save_collection_info()
                
                logger.info("Removed registry entry", doc_id=doc_id)
            
            return True
            
        except Exception as e:
            logger.error("Error removing metadata", doc_id=doc_id, error=str(e))
            return False
    
    def update_document_status(self, doc_id: str, status_info: Dict[str, Any]):
        """
        Update status information for a document.
        
        Args:
            doc_id: Document identifier
            status_info: Status information to update
        """
        if doc_id in self.processed_docs:
            self.processed_docs[doc_id].update(status_info)
            self._save_processed_docs()
            
            # Update collection last modified time
            self.collection_info["last_updated"] = asyncio.get_event_loop().time()
            self._save_collection_info()
            
            logger.info("Updated status for document", doc_id=doc_id)
    
    def get_registry_path(self) -> str:
        """
        Get the path to the processed documents registry.
        
        Returns:
            str: Path to registry file
        """
        return str(self.processed_docs_file)
    
    def get_collection_info_path(self) -> str:
        """
        Get the path to the unified collection info file.
        
        Returns:
            str: Path to collection info file
        """
        return str(self.unified_collection_info_file)
    
    def get_unified_collection_info(self) -> Dict[str, Any]:
        """
        Get unified collection information.
        
        Returns:
            Dict[str, Any]: Collection information
        """
        return self.collection_info.copy()
    
    def document_exists_in_collection(self, doc_id: str) -> bool:
        """
        Check if a document exists in the unified collection metadata.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            bool: True if document exists in metadata
        """
        return doc_id in self.processed_docs
    
    def get_documents_by_status(self, status: str) -> List[str]:
        """
        Get document IDs filtered by status.
        
        Args:
            status: Status to filter by (e.g., "processed", "failed", "processing")
            
        Returns:
            List[str]: List of document IDs with the specified status
        """
        return [
            doc_id for doc_id, info in self.processed_docs.items()
            if info.get("status") == status
        ]
    
    def cleanup_orphaned_metadata(self) -> List[str]:
        """
        Clean up metadata files for documents that are no longer in the registry.
        
        Returns:
            List[str]: List of cleaned up metadata files
        """
        cleaned_files = []
        
        try:
            # Find all metadata files
            metadata_files = list(self.base_db_path.glob("doc_*_metadata.json"))
            
            for metadata_file in metadata_files:
                # Extract doc_id from filename
                doc_id = metadata_file.stem.replace("_metadata", "")
                
                # If not in registry, remove it
                if doc_id not in self.processed_docs:
                    metadata_file.unlink()
                    cleaned_files.append(str(metadata_file))
                    logger.info("Cleaned up orphaned metadata", filename=metadata_file.name)
            
        except Exception as e:
            logger.warning("Error during metadata cleanup", error=str(e))
        
        return cleaned_files