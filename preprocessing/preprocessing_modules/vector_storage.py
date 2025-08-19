"""
Vector Storage Module - Modified for Unified Collection using LanceDB

Handles storing chunks and embeddings in a single LanceDB table
with document-based filtering for multi-document retrieval.
"""

import lancedb
import numpy as np
import pandas as pd
from typing import List, Optional
from pathlib import Path
import shutil
from logger.custom_logger import CustomLogger

# module logger
logger = CustomLogger().get_logger(__file__)

class VectorStorage:
    """Handles vector storage operations with a unified LanceDB table."""
    
    def __init__(self, base_db_path: Path, collection_name: str = "unified_documents"):
        """
        Initialize the vector storage with a unified collection name.
        
        Args:
            base_db_path: Base path for storing the LanceDB database.
            collection_name: Name of the unified table.
        """
        self.base_db_path = base_db_path
        self.collection_name = collection_name
        # LanceDB stores data in a directory, so the .db extension is conventional but not required.
        self.db_path = base_db_path / f"{collection_name}.lance"
        self._db = None
    
    def _get_db(self) -> lancedb.LanceDBConnection:
        """Get or create LanceDB connection."""
        if self._db is None:
            self._db = lancedb.connect(self.db_path)
        return self._db
    
    async def store(self, chunks: List[str], embeddings: np.ndarray, doc_id: str):
        """
        Store chunks and embeddings in the unified LanceDB table.
        
        Args:
            chunks: List of text chunks.
            embeddings: Corresponding embeddings array.
            doc_id: Document identifier.
        """
        if len(chunks) != embeddings.shape[0]:
            raise ValueError(f"Chunk count ({len(chunks)}) doesn't match embedding count ({embeddings.shape[0]})")
        
        db = self._get_db()

        logger.info("Storing vectors for document", doc_id=doc_id, count=len(chunks))
        
        try:
            # Prepare data in a format LanceDB understands (list of dicts or DataFrame)
            data = []
            for i, chunk in enumerate(chunks):
                data.append({
                    "vector": embeddings[i].tolist(),
                    "text": chunk,
                    "chunk_id": i,  # Chunk ID within the document
                    "doc_id": doc_id,  # Document identifier for filtering
                    "char_count": len(chunk),
                    "word_count": len(chunk.split())
                })
            
            if self.collection_name in db.table_names():
                # Table exists, add data to it
                tbl = db.open_table(self.collection_name)
                tbl.add(data)
                logger.info("Added new records to existing table", collection=self.collection_name, added=len(data))
            else:
                # Table does not exist, create it with the first batch of data
                db.create_table(self.collection_name, data=data)
                logger.info("Created new unified table", collection=self.collection_name)
            
            logger.info("Successfully stored all vectors for document", doc_id=doc_id)
            print("🟢 Vectors stored successfully")
            
        except Exception as e:
            logger.error("Error storing vectors for document", doc_id=doc_id, error=str(e))
            raise
            
    def collection_exists(self, doc_id: Optional[str] = None) -> bool:
        """Check if the LanceDB database directory exists."""
        return self.db_path.exists() and len(self._get_db().table_names()) > 0

    def get_collection_info(self, doc_id: Optional[str] = None) -> dict:
        """Get information about the unified table or a specific document within it."""
        if not self.collection_exists():
            return {"collection_name": self.collection_name, "exists": False, "path": str(self.db_path)}
        
        try:
            db = self._get_db()
            tbl = db.open_table(self.collection_name)
            
            base_info = {
                "collection_name": self.collection_name,
                "exists": True,
                "path": str(self.db_path),
                "total_vectors_count": len(tbl),
            }
            
            if doc_id:
                where_clause = f"doc_id = '{doc_id}'"
                doc_df = tbl.to_pandas(where=where_clause)
                doc_vectors_count = len(doc_df)
                
                base_info.update({
                    "doc_id": doc_id,
                    "doc_vectors_count": doc_vectors_count,
                    "sample_chunks": [text[:100] + "..." for text in doc_df['text'].head(3).tolist()]
                })
            
            return base_info
            
        except Exception as e:
            return {"collection_name": self.collection_name, "exists": True, "path": str(self.db_path), "error": str(e)}

    def delete_document(self, doc_id: str) -> bool:
        """Delete all records for a specific document from the unified table."""
        try:
            if not self.collection_exists():
                logger.info("Database doesn't exist, nothing to delete")
                return True
            
            db = self._get_db()
            tbl = db.open_table(self.collection_name)
            
            where_clause = f"doc_id = '{doc_id}'"
            tbl.delete(where_clause)
            
            logger.info("Deleted all vectors for document", doc_id=doc_id)
            return True
            
        except Exception as e:
            logger.error("Error deleting document", doc_id=doc_id, error=str(e))
            return False

    def delete_collection(self, doc_id: Optional[str] = None) -> bool:
        """Delete the entire unified collection (database directory)."""
        try:
            if self.db_path.exists():
                shutil.rmtree(self.db_path)
                logger.info("Deleted unified collection directory", path=str(self.db_path))
                # Reset connection object
                self._db = None
                return True
        except Exception as e:
            logger.error("Error deleting collection", collection=self.collection_name, error=str(e))
            return False
        return True

    def list_documents(self) -> List[str]:
        """List all unique document IDs in the unified table."""
        try:
            if not self.collection_exists():
                return []
            
            db = self._get_db()
            tbl = db.open_table(self.collection_name)
            
            # Efficiently get unique doc_ids
            df = tbl.to_pandas(columns=["doc_id"])
            if df.empty:
                return []
            
            unique_doc_ids = df["doc_id"].unique().tolist()
            return sorted(unique_doc_ids)
            
        except Exception as e:
            logger.error("Error listing documents", error=str(e))
            return []

    def close(self):
        """LanceDB connection doesn't need explicit closing."""
        self._db = None
        pass