"""
Metadata Manager Module

Handles document metadata storage and retrieval operations.
"""

import json
import asyncio
import hashlib
from typing import List, Dict, Any
from pathlib import Path
from config.config import EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP


class MetadataManager:
    """Handles document metadata operations."""
    
    def __init__(self, base_db_path: Path):
        """
        Initialize the metadata manager.
        
        Args:
            base_db_path: Base path for storing metadata files
        """
        self.base_db_path = base_db_path
        self.processed_docs_file = self.base_db_path / "processed_documents.json"
        self.processed_docs = self._load_processed_docs()
    
    def _load_processed_docs(self) -> Dict[str, Dict]:
        """Load the registry of processed documents."""
        if self.processed_docs_file.exists():
            try:
                with open(self.processed_docs_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Warning: Could not load processed docs registry: {e}")
        return {}
    
    def _save_processed_docs(self):
        """Save the registry of processed documents."""
        try:
            with open(self.processed_docs_file, 'w', encoding='utf-8') as f:
                json.dump(self.processed_docs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Warning: Could not save processed docs registry: {e}")
    
    def generate_doc_id(self, document_url: str) -> str:
        """
        Generate a unique document ID from the URL.
        
        Args:
            document_url: URL of the document
            
        Returns:
            str: Unique document ID
        """
        url_hash = hashlib.md5(document_url.encode()).hexdigest()[:12]
        return f"doc_{url_hash}"
    
    def is_document_processed(self, document_url: str) -> bool:
        """
        Check if a document has already been processed.
        
        Args:
            document_url: URL of the document
            
        Returns:
            bool: True if document is already processed
        """
        doc_id = self.generate_doc_id(document_url)
        return doc_id in self.processed_docs
    
    def get_document_info(self, document_url: str) -> Dict[str, Any]:
        """
        Get information about a processed document.
        
        Args:
            document_url: URL of the document
            
        Returns:
            Dict[str, Any]: Document information or empty dict if not found
        """
        doc_id = self.generate_doc_id(document_url)
        return self.processed_docs.get(doc_id, {})
    
    def save_document_metadata(self, chunks: List[str], doc_id: str, document_url: str):
        """
        Save document metadata to JSON file and update registry.
        
        Args:
            chunks: List of text chunks
            doc_id: Document identifier
            document_url: Original document URL
        """
        # Calculate statistics
        total_chars = sum(len(chunk) for chunk in chunks)
        total_words = sum(len(chunk.split()) for chunk in chunks)
        avg_chunk_size = total_chars / len(chunks) if chunks else 0
        
        # Create metadata object
        metadata = {
            "doc_id": doc_id,
            "document_url": document_url,
            "chunk_count": len(chunks),
            "total_chars": total_chars,
            "total_words": total_words,
            "avg_chunk_size": avg_chunk_size,
            "processed_at": asyncio.get_event_loop().time(),
            "embedding_model": EMBEDDING_MODEL,
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
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
            print(f"✅ Saved individual metadata for {doc_id}")
        except Exception as e:
            print(f"⚠️ Warning: Could not save individual metadata for {doc_id}: {e}")
        
        # Update processed documents registry
        self.processed_docs[doc_id] = {
            "document_url": document_url,
            "chunk_count": len(chunks),
            "processed_at": metadata["processed_at"],
            "collection_name": f"{doc_id}_collection",
            "total_chars": total_chars,
            "total_words": total_words
        }
        self._save_processed_docs()
        
        print(f"✅ Updated registry for document {doc_id}")
    
    def get_document_metadata(self, doc_id: str) -> Dict[str, Any]:
        """
        Load individual document metadata from file.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Dict[str, Any]: Document metadata or empty dict if not found
        """
        metadata_path = self.base_db_path / f"{doc_id}_metadata.json"
        
        if not metadata_path.exists():
            return {}
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Warning: Could not load metadata for {doc_id}: {e}")
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
        Get statistics about all collections.
        
        Returns:
            Dict[str, Any]: Collection statistics
        """
        stats = {
            "total_documents": len(self.processed_docs),
            "total_collections": 0,
            "total_chunks": 0,
            "total_characters": 0,
            "total_words": 0,
            "documents": []
        }
        
        for doc_id, info in self.processed_docs.items():
            collection_path = self.base_db_path / f"{info['collection_name']}.db"
            if collection_path.exists():
                stats["total_collections"] += 1
                stats["total_chunks"] += info.get("chunk_count", 0)
                stats["total_characters"] += info.get("total_chars", 0)
                stats["total_words"] += info.get("total_words", 0)
                
                stats["documents"].append({
                    "doc_id": doc_id,
                    "url": info["document_url"],
                    "chunk_count": info.get("chunk_count", 0),
                    "total_chars": info.get("total_chars", 0),
                    "total_words": info.get("total_words", 0),
                    "processed_at": info.get("processed_at", "unknown")
                })
        
        # Add averages
        if stats["total_documents"] > 0:
            stats["avg_chunks_per_doc"] = stats["total_chunks"] / stats["total_documents"]
            stats["avg_chars_per_doc"] = stats["total_characters"] / stats["total_documents"]
            stats["avg_words_per_doc"] = stats["total_words"] / stats["total_documents"]
        
        return stats
    
    def remove_document_metadata(self, doc_id: str) -> bool:
        """
        Remove document metadata and registry entry.
        
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
                print(f"🗑️ Removed metadata file for {doc_id}")
            
            # Remove from registry
            if doc_id in self.processed_docs:
                del self.processed_docs[doc_id]
                self._save_processed_docs()
                print(f"🗑️ Removed registry entry for {doc_id}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error removing metadata for {doc_id}: {e}")
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
            print(f"✅ Updated status for document {doc_id}")
    
    def get_registry_path(self) -> str:
        """
        Get the path to the processed documents registry.
        
        Returns:
            str: Path to registry file
        """
        return str(self.processed_docs_file)
