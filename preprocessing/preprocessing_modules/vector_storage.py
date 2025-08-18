"""
Vector Storage Module - Modified for Unified Collection

Handles storing chunks and embeddings in a single Qdrant collection 
with document-based filtering for multi-document retrieval.
"""

import numpy as np
from typing import List, Optional
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue


class VectorStorage:
    """Handles vector storage operations with unified Qdrant collection."""
    
    def __init__(self, base_db_path: Path, collection_name: str = "unified_documents"):
        """
        Initialize the vector storage with unified collection.
        
        Args:
            base_db_path: Base path for storing Qdrant database
            collection_name: Name of the unified collection
        """
        self.base_db_path = base_db_path
        self.collection_name = collection_name
        self.db_path = base_db_path / f"{collection_name}.db"
        self._client = None
        self._next_point_id = 0  # Track next available point ID
    
    def _get_client(self) -> QdrantClient:
        """Get or create Qdrant client."""
        if self._client is None:
            self._client = QdrantClient(path=str(self.db_path))
        return self._client
    
    def _get_next_point_id(self) -> int:
        """Get the next available point ID."""
        client = self._get_client()
        try:
            # Get collection info to find current max ID
            collection_info = client.get_collection(self.collection_name)
            if collection_info.vectors_count > 0:
                # Scroll through all points to find max ID
                result = client.scroll(
                    collection_name=self.collection_name,
                    limit=10000,  # Adjust if you have more points
                    with_payload=False,
                    with_vectors=False
                )
                if result[0]:
                    max_id = max(point.id for point in result[0])
                    return max_id + 1
            return 0
        except Exception:
            return 0
    
    async def store_in_qdrant(self, chunks: List[str], embeddings: np.ndarray, doc_id: str):
        """
        Store chunks and embeddings in unified Qdrant collection.
        
        Args:
            chunks: List of text chunks
            embeddings: Corresponding embeddings array
            doc_id: Document identifier
        """
        if len(chunks) != embeddings.shape[0]:
            raise ValueError(f"Chunk count ({len(chunks)}) doesn't match embedding count ({embeddings.shape[0]})")
        
        client = self._get_client()
        
        print(f"💾 Storing {len(chunks)} vectors for document: {doc_id}")
        
        try:
            # Ensure collection exists
            await self._ensure_collection_exists(client, embeddings.shape[1])
            
            # Get starting point ID
            start_point_id = self._get_next_point_id()
            
            # Prepare and upload points
            await self._upload_points(client, chunks, embeddings, doc_id, start_point_id)
            
            print(f"✅ Successfully stored all vectors for {doc_id}")
            
        except Exception as e:
            print(f"❌ Error storing vectors for {doc_id}: {e}")
            raise
    
    async def _ensure_collection_exists(self, client: QdrantClient, embedding_dim: int):
        """
        Ensure unified collection exists, create if it doesn't.
        
        Args:
            client: Qdrant client
            embedding_dim: Dimension of embeddings
        """
        try:
            # Try to get collection info
            client.get_collection(self.collection_name)
            print(f"📚 Using existing collection: {self.collection_name}")
        except Exception:
            # Collection doesn't exist, create it
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=embedding_dim,
                    distance=Distance.COSINE
                )
            )
            print(f"✅ Created new unified collection: {self.collection_name}")
    
    async def _upload_points(self, client: QdrantClient, chunks: List[str], 
                           embeddings: np.ndarray, doc_id: str, start_point_id: int):
        """
        Upload points to unified Qdrant collection in batches.
        
        Args:
            client: Qdrant client
            chunks: Text chunks
            embeddings: Embedding vectors
            doc_id: Document identifier
            start_point_id: Starting point ID for this document
        """
        # Prepare points with unique IDs across all documents
        points = []
        for i in range(len(chunks)):
            point_id = start_point_id + i
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embeddings[i].tolist(),
                    payload={
                        "text": chunks[i],
                        "chunk_id": i,  # Chunk ID within document
                        "doc_id": doc_id,  # Document identifier for filtering
                        "char_count": len(chunks[i]),
                        "word_count": len(chunks[i].split()),
                        "global_point_id": point_id  # Global unique ID
                    }
                )
            )
        
        # Upload in batches to handle large documents
        batch_size = 100
        total_batches = (len(points) + batch_size - 1) // batch_size
        
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            
            print(f"   Uploading batch {batch_num}/{total_batches} ({len(batch)} points)")
            client.upsert(collection_name=self.collection_name, points=batch)
        
        print(f"✅ Uploaded {len(points)} points in {total_batches} batches")
        
        # Update next point ID tracker
        self._next_point_id = start_point_id + len(points)
    
    def collection_exists(self, doc_id: Optional[str] = None) -> bool:
        """
        Check if the unified collection exists.
        
        Args:
            doc_id: Document identifier (kept for compatibility, but checks unified collection)
            
        Returns:
            bool: True if unified collection exists, False otherwise
        """
        return self.db_path.exists()
    
    def get_collection_info(self, doc_id: Optional[str] = None) -> dict:
        """
        Get information about the unified collection or specific document.
        
        Args:
            doc_id: Document identifier (if provided, returns document-specific info)
            
        Returns:
            dict: Collection/document information
        """
        if not self.db_path.exists():
            return {
                "collection_name": self.collection_name,
                "exists": False,
                "path": str(self.db_path)
            }
        
        try:
            client = self._get_client()
            collection_info = client.get_collection(self.collection_name)
            
            base_info = {
                "collection_name": self.collection_name,
                "exists": True,
                "path": str(self.db_path),
                "total_vectors_count": collection_info.vectors_count,
                "status": collection_info.status
            }
            
            # If doc_id specified, get document-specific info
            if doc_id:
                try:
                    # Count vectors for this specific document
                    result = client.scroll(
                        collection_name=self.collection_name,
                        scroll_filter=Filter(
                            must=[
                                FieldCondition(
                                    key="doc_id",
                                    match=MatchValue(value=doc_id)
                                )
                            ]
                        ),
                        limit=10000,
                        with_payload=True,
                        with_vectors=False
                    )
                    
                    doc_vectors_count = len(result[0])
                    base_info.update({
                        "doc_id": doc_id,
                        "doc_vectors_count": doc_vectors_count,
                        "sample_chunks": [point.payload.get("text", "")[:100] + "..." 
                                        for point in result[0][:3]]  # First 3 chunks as sample
                    })
                    
                except Exception as e:
                    base_info.update({
                        "doc_id": doc_id,
                        "doc_error": str(e)
                    })
            
            return base_info
            
        except Exception as e:
            return {
                "collection_name": self.collection_name,
                "exists": True,
                "path": str(self.db_path),
                "error": str(e)
            }
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete all points for a specific document from unified collection.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            bool: True if successfully deleted, False otherwise
        """
        try:
            if not self.db_path.exists():
                print(f"📁 Database doesn't exist")
                return True
            
            client = self._get_client()
            
            # Delete all points with matching doc_id
            client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="doc_id",
                            match=MatchValue(value=doc_id)
                        )
                    ]
                )
            )
            
            print(f"🗑️ Deleted all vectors for document: {doc_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting document {doc_id}: {e}")
            return False
    
    def delete_collection(self, doc_id: Optional[str] = None) -> bool:
        """
        Delete the entire unified collection and database file.
        
        Args:
            doc_id: Ignored (kept for compatibility)
            
        Returns:
            bool: True if successfully deleted, False otherwise
        """
        try:
            if self.db_path.exists():
                # Close client connection first
                if self._client:
                    self._client.close()
                    self._client = None
                
                # Remove database directory
                import shutil
                shutil.rmtree(self.db_path, ignore_errors=True)
                print(f"🗑️ Deleted unified collection: {self.collection_name}")
                return True
            
        except Exception as e:
            print(f"❌ Error deleting collection {self.collection_name}: {e}")
            return False
        
        return True  # Nothing to delete
    
    def list_documents(self) -> List[str]:
        """
        List all document IDs in the unified collection.
        
        Returns:
            List[str]: List of document IDs
        """
        try:
            if not self.db_path.exists():
                return []
            
            client = self._get_client()
            
            # Get all unique doc_ids
            result = client.scroll(
                collection_name=self.collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=False
            )
            
            doc_ids = set()
            for point in result[0]:
                doc_id = point.payload.get("doc_id")
                if doc_id:
                    doc_ids.add(doc_id)
            
            return sorted(list(doc_ids))
            
        except Exception as e:
            print(f"❌ Error listing documents: {e}")
            return []
    
    def close(self):
        """Close the client connection."""
        if self._client:
            self._client.close()
            self._client = None