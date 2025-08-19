# --- START OF FILE search_manager.py ---

"""
Search Module for Advanced RAG - Modified for Multi-Document Support using LanceDB
Handles hybrid search combining BM25 and semantic search with score fusion
across multiple documents in a unified collection.
"""

import re
import time
import lancedb
import numpy as np
import pandas as pd
from typing import List, Dict, Union
from pathlib import Path
from rank_bm25 import BM25Okapi

from config.config import (
    OUTPUT_DIR, TOP_K, SCORE_THRESHOLD, ENABLE_HYBRID_SEARCH,
    BM25_WEIGHT, SEMANTIC_WEIGHT, USE_TOTAL_BUDGET_APPROACH
)
from logger.custom_logger import CustomLogger

# module-level logger
logger = CustomLogger().get_logger(__file__)

class SearchManager:
    """Manages hybrid search operations across multiple documents in a unified LanceDB table."""
    
    def __init__(self, embedding_manager, collection_name: str = "unified_documents"):
        """Initialize the search manager."""
        self.answer_count = 0
        self.embedding_manager = embedding_manager
        self.collection_name = collection_name
        self.base_db_path = Path(OUTPUT_DIR)
        self.db_path = self.base_db_path / f"{collection_name}.lance"
        self._db = None
        self.bm25_indexes = {}  # Cache BM25 indexes per document set
        self.document_chunks = {}  # Cache chunks for BM25 per document set
    logger.info("Multi-Document Search Manager initialized with LanceDB", status="initialized")
    
    def _get_db(self) -> lancedb.LanceDBConnection:
        """Get or create LanceDB connection."""
        if self._db is None:
            if not self.db_path.exists():
                raise FileNotFoundError(f"Unified database not found at {self.db_path}")
            self._db = lancedb.connect(self.db_path)
        return self._db
    
    def _get_document_filter(self, doc_ids: List[str]) -> str:
        """Create a SQL WHERE clause for specific documents."""
        if len(doc_ids) == 1:
            return f"doc_id = '{doc_ids[0]}'"
        else:
            # Create a tuple string for SQL IN clause, e.g., "('doc1', 'doc2')"
            doc_id_tuple = tuple(doc_ids)
            return f"doc_id IN {doc_id_tuple}"
    
    def _load_bm25_index(self, doc_ids: List[str]):
        """Load or create BM25 index for a set of documents from LanceDB."""
        doc_set_key = "_".join(sorted(doc_ids))
        
        if doc_set_key not in self.bm25_indexes:
            logger.info("Loading BM25 index for documents", doc_ids=doc_ids)
            
            db = self._get_db()
            
            try:
                tbl = db.open_table(self.collection_name)
                document_filter = self._get_document_filter(doc_ids)
                
                # Fetch all relevant chunks using a filter
                df = tbl.search().where(document_filter).to_pandas()
                
                if df.empty:
                    raise ValueError("No chunks found for the specified document IDs.")

                # We need a unique, persistent ID for each chunk. Let's create one if not present.
                # Assuming chunk_id + doc_id is unique. A global ID is better.
                # Let's create a temporary unique ID for BM25 lookup.
                df['point_id'] = df['doc_id'] + '_' + df['chunk_id'].astype(str)
                
                chunks = df['text'].tolist()
                chunk_ids = df['point_id'].tolist()
                doc_sources = df['doc_id'].tolist()
                
                tokenized_chunks = [self._tokenize_text(chunk) for chunk in chunks]
                
                self.bm25_indexes[doc_set_key] = BM25Okapi(tokenized_chunks)
                self.document_chunks[doc_set_key] = {
                    'chunks': chunks,
                    'chunk_ids': chunk_ids,
                    'doc_sources': doc_sources,
                    'tokenized_chunks': tokenized_chunks
                }
                
                doc_distribution = df['doc_id'].value_counts().to_dict()
                
                logger.info("BM25 index loaded", chunks=len(chunks), distribution=doc_distribution)
                for doc_id, count in doc_distribution.items():
                    logger.info("Document chunk distribution", doc_id=doc_id, count=count)
                
            except Exception as e:
                logger.error("Error loading BM25 index for documents", doc_ids=doc_ids, error=str(e))
                self.bm25_indexes[doc_set_key] = BM25Okapi([[]])
                self.document_chunks[doc_set_key] = {
                    'chunks': [], 'chunk_ids': [], 'doc_sources': [], 'tokenized_chunks': []
                }
    
    def _tokenize_text(self, text: str) -> List[str]:
        """Simple tokenization for BM25."""
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        tokens = [token for token in text.split() if len(token) > 2]
        return tokens

    async def hybrid_search(self, queries: List[str], doc_ids: Union[str, List[str]], 
                          top_k: int = TOP_K) -> List[Dict]:
        if isinstance(doc_ids, str):
            doc_ids = [doc_ids]
        
        logger.info("Starting multi-document hybrid search", documents=doc_ids, queries=len(queries), target=top_k)
        
        db = self._get_db()
        tbl = db.open_table(self.collection_name)
        document_filter = self._get_document_filter(doc_ids)
        
        doc_set_key = "_".join(sorted(doc_ids))
        if doc_set_key not in self.bm25_indexes:
            self._load_bm25_index(doc_ids)
        
        # ... (Budget calculation logic remains the same) ...
        if USE_TOTAL_BUDGET_APPROACH and len(queries) > 1:
            per_query_budget = max(1, top_k // len(queries))
            extra_budget = top_k % len(queries)
        else:
            per_query_budget = top_k
            extra_budget = 0
        
        all_candidates = {}
        query_performance = {}
        
        logger.info("Running hybrid search", queries=len(queries))
        
        for query_idx, query in enumerate(queries):
            query_candidates = 0
            query_start = time.time()
            
            if USE_TOTAL_BUDGET_APPROACH and len(queries) > 1:
                query_budget = per_query_budget + (1 if query_idx < extra_budget else 0)
                search_limit = query_budget * 2
            else:
                query_budget = per_query_budget
                search_limit = query_budget * 2
            
            logger.info("Query budget allocated", query_index=query_idx+1, budget=query_budget, search_limit=search_limit)
            
            # 1. Semantic Search with Document Filter
            if True: # Always do semantic
                try:
                    query_vector = await self.embedding_manager.encode_query(query)
                    
                    # LanceDB returns distance (lower is better), Qdrant returns similarity (higher is better)
                    # We'll convert distance to similarity: score = 1 - distance
                    semantic_results = tbl.search(query_vector)\
                                          .where(document_filter)\
                                          .limit(search_limit)\
                                          .to_list()
                    
                    semantic_count = 0
                    for result in semantic_results:
                        if USE_TOTAL_BUDGET_APPROACH and semantic_count >= query_budget:
                            break
                            
                        # Assuming cosine distance, similarity = 1 - distance
                        semantic_score = 1 - result['_distance']
                        if SCORE_THRESHOLD and semantic_score < SCORE_THRESHOLD:
                            continue

                        # Create a consistent point ID
                        point_id = f"{result['doc_id']}_{result['chunk_id']}"
                        
                        if point_id not in all_candidates:
                            # Create payload from result, excluding vector and distance
                            payload = {k: v for k, v in result.items() if k not in ['vector', '_distance']}
                            all_candidates[point_id] = {
                                'semantic_score': 0, 'bm25_score': 0,
                                'payload': payload, 'fusion_score': 0,
                                'contributing_queries': [],
                                'source_doc_id': result.get('doc_id', 'unknown')
                            }
                        
                        if semantic_score > all_candidates[point_id]['semantic_score']:
                            all_candidates[point_id]['semantic_score'] = semantic_score
                        
                        all_candidates[point_id]['contributing_queries'].append({
                            'query_idx': query_idx, 'query_text': query[:50] + '...',
                            'semantic_score': semantic_score, 'type': 'semantic'
                        })
                        query_candidates += 1
                        semantic_count += 1
                
                except Exception as e:
                    logger.error("Semantic search failed for query", query=query[:50], error=str(e))

            # 2. BM25 Search (if enabled)
            if ENABLE_HYBRID_SEARCH and doc_set_key in self.bm25_indexes:
                # ... (BM25 logic remains largely the same, but uses the new point_id format) ...
                try:
                    tokenized_query = self._tokenize_text(query)
                    bm25_scores = self.bm25_indexes[doc_set_key].get_scores(tokenized_query)
                    
                    chunk_data = self.document_chunks[doc_set_key]
                    bm25_top_indices = np.argsort(bm25_scores)[::-1][:search_limit]
                    
                    bm25_count = 0
                    for idx in bm25_top_indices:
                        if USE_TOTAL_BUDGET_APPROACH and bm25_count >= query_budget:
                            break
                            
                        if idx < len(chunk_data['chunk_ids']) and bm25_scores[idx] > 0:
                            point_id = str(chunk_data['chunk_ids'][idx]) # This is our doc_id + chunk_id
                            bm25_score = float(bm25_scores[idx])
                            doc_source = chunk_data['doc_sources'][idx]
                            
                            if doc_source not in doc_ids:
                                continue
                            
                            if point_id not in all_candidates:
                                # Reconstruct a basic payload for BM25-only finds
                                payload = {
                                    'text': chunk_data['chunks'][idx],
                                    'doc_id': doc_source,
                                    'chunk_id': int(point_id.split('_')[-1])
                                }
                                all_candidates[point_id] = {
                                    'semantic_score': 0, 'bm25_score': 0,
                                    'payload': payload, 'fusion_score': 0,
                                    'contributing_queries': [],
                                    'source_doc_id': doc_source
                                }
                            
                            if bm25_score > all_candidates[point_id]['bm25_score']:
                                all_candidates[point_id]['bm25_score'] = bm25_score
                            
                            all_candidates[point_id]['contributing_queries'].append({
                                'query_idx': query_idx, 'query_text': query[:50] + '...',
                                'bm25_score': bm25_score, 'type': 'bm25'
                            })
                            query_candidates += 1
                            bm25_count += 1
                
                except Exception as e:
                    logger.error("BM25 search failed for query", query=query[:50], error=str(e))
            
            query_time = time.time() - query_start
            query_performance[query_idx] = {
                'query': query[:80] + '...' if len(query) > 80 else query,
                'candidates_found': query_candidates,
                'budget_allocated': query_budget if USE_TOTAL_BUDGET_APPROACH else 'unlimited',
                'time': query_time
            }

        self._apply_score_fusion(all_candidates)
        
        sorted_candidates = sorted(all_candidates.items(), key=lambda x: x[1]['fusion_score'], reverse=True)
        
        hybrid_results = []
        for point_id, data in sorted_candidates[:top_k]:
            hybrid_results.append({
                'id': point_id,
                'score': data['fusion_score'],
                'payload': data['payload'],
                'semantic_score': data['semantic_score'],
                'bm25_score': data['bm25_score'],
                'source_doc_id': data['source_doc_id'],
                'contributing_queries': data['contributing_queries']
            })
        
        # ... (Logging logic remains the same) ...
        logger.info("Multi-document hybrid search completed", results=len(hybrid_results))
        self.answer_count += 1
        print(f"🟢 Multi-doc Q{self.answer_count} Hybrid search successful")

        return hybrid_results
    
    def _apply_score_fusion(self, candidates: Dict):
        """Apply advanced score fusion techniques."""
        # ... (This function remains unchanged as it's vector-store agnostic) ...
        if not candidates:
            return
        
        semantic_scores = [data['semantic_score'] for data in candidates.values() if data['semantic_score'] > 0]
        bm25_scores = [data['bm25_score'] for data in candidates.values() if data['bm25_score'] > 0]
        
        if semantic_scores:
            sem_min, sem_max = min(semantic_scores), max(semantic_scores)
            sem_range = sem_max - sem_min if sem_max > sem_min else 1
        else:
            sem_min, sem_range = 0, 1
            
        if bm25_scores:
            bm25_min, bm25_max = min(bm25_scores), max(bm25_scores)
            bm25_range = bm25_max - bm25_min if bm25_max > bm25_min else 1
        else:
            bm25_min, bm25_range = 0, 1
        
        for point_id, data in candidates.items():
            norm_semantic = (data['semantic_score'] - sem_min) / sem_range if data['semantic_score'] > 0 else 0
            norm_bm25 = (data['bm25_score'] - bm25_min) / bm25_range if data['bm25_score'] > 0 else 0
            
            if ENABLE_HYBRID_SEARCH:
                fusion_score = (SEMANTIC_WEIGHT * norm_semantic) + (BM25_WEIGHT * norm_bm25)
            else:
                fusion_score = norm_semantic
            
            rank_bonus = 1.0 / (1.0 + max(norm_semantic, norm_bm25) * 10)
            fusion_score += rank_bonus * 0.1
            
            data['fusion_score'] = fusion_score
    

    def list_available_documents(self) -> List[str]:
        """
        List all available document IDs in the unified LanceDB table.
        
        Returns:
            List[str]: A sorted list of unique document IDs.
        """
        try:
            db = self._get_db()
            if self.collection_name not in db.table_names():
                logger.info("Collection does not exist yet", collection=self.collection_name)
                return []
            
            tbl = db.open_table(self.collection_name)
            
            # Use to_pandas for efficient retrieval of a single column
            df = tbl.to_pandas(columns=["doc_id"])
            
            if df.empty:
                return []
            
            # Get unique doc_ids from the DataFrame, convert to list, and sort
            doc_ids = sorted(df["doc_id"].unique().tolist())
            return doc_ids
            
        except Exception as e:
            logger.error("Error listing documents", error=str(e))
            return []
    
    def get_document_stats(self, doc_ids: Union[str, List[str]] = None) -> Dict:
        """
        Get statistics about documents in the collection using efficient aggregation.
        
        Args:
            doc_ids: Specific document IDs to get stats for, or None for all documents.
            
        Returns:
            Dict: A dictionary containing document statistics.
        """
        try:
            db = self._get_db()
            if self.collection_name not in db.table_names():
                return {"error": "Collection does not exist."}
            
            tbl = db.open_table(self.collection_name)
            
            # Normalize doc_ids to a list if a single string is provided
            if isinstance(doc_ids, str):
                doc_ids = [doc_ids]
            
            # Build the WHERE clause if specific documents are requested
            where_clause = None
            if doc_ids:
                where_clause = self._get_document_filter(doc_ids)
            
            # Load the necessary data into a pandas DataFrame for efficient aggregation
            # This is much faster than iterating through all records in Python
            df = tbl.to_pandas(where=where_clause)
            
            if df.empty:
                return {
                    "total_documents": 0,
                    "total_chunks": 0,
                    "document_stats": {},
                    "queried_documents": doc_ids if doc_ids else "all"
                }

            # Use pandas groupby for extremely fast and clean statistics calculation
            stats_df = df.groupby('doc_id').agg(
                chunk_count=('doc_id', 'size'),
                total_chars=('char_count', 'sum'),
                total_words=('word_count', 'sum')
            )

            # Calculate averages after aggregation
            stats_df['avg_chunk_length'] = (stats_df['total_chars'] / stats_df['chunk_count']).round(2)

            # Convert the aggregated DataFrame to the desired dictionary format
            doc_stats_dict = stats_df.to_dict('index')

            return {
                "total_documents": len(doc_stats_dict),
                "total_chunks": int(df.shape[0]),
                "document_stats": doc_stats_dict,
                "queried_documents": doc_ids if doc_ids else "all"
            }
            
        except Exception as e:
            logger.error("Error getting document stats", error=str(e))
            return {"error": str(e)}

    def cleanup(self):
        """Cleanup search manager resources."""
        logger.info("Cleaning up Multi-Document Search Manager resources", status="cleanup_start")
        self._db = None
        self.bm25_indexes.clear()
        self.document_chunks.clear()
        logger.info("Multi-Document Search Manager cleanup completed", status="cleanup_done")