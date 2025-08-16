"""
Vector Storage Module

Handles storing chunks and embeddings in Qdrant vector database.
"""

import numpy as np
from typing import List
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


class VectorStorage:
    """Handles vector storage operations with Qdrant."""
    
    def __init__(self, base_db_path: Path):
        """
        Initialize the vector storage.
        
        Args:
            base_db_path: Base path for storing Qdrant databases
        """
        self.base_db_path = base_db_path
    
    async def store_in_qdrant(self, chunks: List[str], embeddings: np.ndarray, doc_id: str):
        """
        Store chunks and embeddings in Qdrant.
        
        Args:
            chunks: List of text chunks
            embeddings: Corresponding embeddings array
            doc_id: Document identifier
        """
        if len(chunks) != embeddings.shape[0]:
            raise ValueError(f"Chunk count ({len(chunks)}) doesn't match embedding count ({embeddings.shape[0]})")
        
        collection_name = f"{doc_id}_collection"
        db_path = self.base_db_path / f"{collection_name}.db"
        client = QdrantClient(path=str(db_path))
        
        print(f"💾 Storing {len(chunks)} vectors in collection: {collection_name}")
        
        try:
            # Create or recreate collection
            await self._setup_collection(client, collection_name, embeddings.shape[1])
            
            # Prepare and upload points
            await self._upload_points(client, collection_name, chunks, embeddings, doc_id)
            
            print(f"✅ Successfully stored all vectors in Qdrant")
            
        finally:
            client.close()
    
    async def _setup_collection(self, client: QdrantClient, collection_name: str, embedding_dim: int):
        """
        Set up Qdrant collection, recreating if it exists.
        
        Args:
            client: Qdrant client
            collection_name: Name of the collection
            embedding_dim: Dimension of embeddings
        """
        # Delete existing collection if it exists
        try:
            client.delete_collection(collection_name)
            print(f"🗑️ Deleted existing collection: {collection_name}")
        except Exception:
            pass  # Collection might not exist
        
        # Create new collection
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=embedding_dim,
                distance=Distance.COSINE
            )
        )
        print(f"✅ Created new collection: {collection_name}")
    
    async def _upload_points(self, client: QdrantClient, collection_name: str, 
                           chunks: List[str], embeddings: np.ndarray, doc_id: str):
        """
        Upload points to Qdrant collection in batches.
        
        Args:
            client: Qdrant client
            collection_name: Name of the collection
            chunks: Text chunks
            embeddings: Embedding vectors
            doc_id: Document identifier
        """
        # Prepare points
        points = []
        for i in range(len(chunks)):
            points.append(
                PointStruct(
                    id=i,
                    vector=embeddings[i].tolist(),
                    payload={
                        "text": chunks[i],
                        "chunk_id": i,
                        "doc_id": doc_id,
                        "char_count": len(chunks[i]),
                        "word_count": len(chunks[i].split())
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
            client.upsert(collection_name=collection_name, points=batch)
        
        print(f"✅ Uploaded {len(points)} points in {total_batches} batches")
    
    def collection_exists(self, doc_id: str) -> bool:
        """
        Check if a collection exists for the given document ID.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            bool: True if collection exists, False otherwise
        """
        collection_name = f"{doc_id}_collection"
        db_path = self.base_db_path / f"{collection_name}.db"
        return db_path.exists()
    
    def get_collection_info(self, doc_id: str) -> dict:
        """
        Get information about a collection.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            dict: Collection information
        """
        collection_name = f"{doc_id}_collection"
        db_path = self.base_db_path / f"{collection_name}.db"
        
        if not db_path.exists():
            return {
                "collection_name": collection_name,
                "exists": False,
                "path": str(db_path)
            }
        
        try:
            client = QdrantClient(path=str(db_path))
            try:
                collection_info = client.get_collection(collection_name)
                return {
                    "collection_name": collection_name,
                    "exists": True,
                    "path": str(db_path),
                    "vectors_count": collection_info.vectors_count,
                    "status": collection_info.status
                }
            finally:
                client.close()
        except Exception as e:
            return {
                "collection_name": collection_name,
                "exists": True,
                "path": str(db_path),
                "error": str(e)
            }
    
    def delete_collection(self, doc_id: str) -> bool:
        """
        Delete a collection and its database file.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            bool: True if successfully deleted, False otherwise
        """
        collection_name = f"{doc_id}_collection"
        db_path = self.base_db_path / f"{collection_name}.db"
        
        try:
            if db_path.exists():
                # Try to delete collection properly first
                try:
                    client = QdrantClient(path=str(db_path))
                    client.delete_collection(collection_name)
                    client.close()
                except Exception:
                    pass  # Collection might not exist or be corrupted
                
                # Remove database directory
                import shutil
                shutil.rmtree(db_path, ignore_errors=True)
                print(f"🗑️ Deleted collection: {collection_name}")
                return True
            
        except Exception as e:
            print(f"❌ Error deleting collection {collection_name}: {e}")
            return False
        
        return True  # Nothing to delete
