"""
Search Module for Advanced RAG - Modified for Multi-Document Support
Handles hybrid search combining BM25 and semantic search with score fusion
across multiple documents in a unified collection.
"""

import re
import time
import numpy as np
from typing import List, Dict, Any, Union
from pathlib import Path
from rank_bm25 import BM25Okapi
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny

from config.config import (
    OUTPUT_DIR, TOP_K, SCORE_THRESHOLD, ENABLE_HYBRID_SEARCH,
    BM25_WEIGHT, SEMANTIC_WEIGHT, USE_TOTAL_BUDGET_APPROACH
)


class SearchManager:
    """Manages hybrid search operations across multiple documents in unified collection."""
    
    def __init__(self, embedding_manager, collection_name: str = "unified_documents"):
        """Initialize the search manager."""
        self.embedding_manager = embedding_manager
        self.collection_name = collection_name
        self.base_db_path = Path(OUTPUT_DIR)
        self.db_path = self.base_db_path / f"{collection_name}.db"
        self._client = None
        self.bm25_indexes = {}  # Cache BM25 indexes per document set
        self.document_chunks = {}  # Cache chunks for BM25 per document set
        print("🟢-> Multi-Document Search Manager initialized")
    
    def _get_client(self) -> QdrantClient:
        """Get or create Qdrant client for unified collection."""
        if self._client is None:
            if not self.db_path.exists():
                raise FileNotFoundError(f"Unified database not found at {self.db_path}")
            self._client = QdrantClient(path=str(self.db_path))
        return self._client
    
    def _get_document_filter(self, doc_ids: List[str]) -> Filter:
        """Create Qdrant filter for specific documents."""
        if len(doc_ids) == 1:
            return Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match=MatchValue(value=doc_ids[0])
                    )
                ]
            )
        else:
            return Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match=MatchAny(any=doc_ids)
                    )
                ]
            )
    
    def _load_bm25_index(self, doc_ids: List[str]):
        """Load or create BM25 index for a set of documents."""
        # Create a cache key for this document set
        doc_set_key = "_".join(sorted(doc_ids))
        
        if doc_set_key not in self.bm25_indexes:
            print(f"📄 Loading BM25 index for documents: {doc_ids}")
            
            client = self._get_client()
            
            try:
                # Get all chunks from specified documents
                document_filter = self._get_document_filter(doc_ids)
                
                result = client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=document_filter,
                    limit=10000,  # Adjust based on your total chunk count
                    with_payload=True,
                    with_vectors=False
                )
                
                chunks = []
                chunk_ids = []
                doc_sources = []  # Track which document each chunk belongs to
                
                for point in result[0]:
                    chunk_text = point.payload.get('text', '')
                    chunks.append(chunk_text)
                    chunk_ids.append(point.id)
                    doc_sources.append(point.payload.get('doc_id', 'unknown'))
                
                # Tokenize chunks for BM25
                tokenized_chunks = [self._tokenize_text(chunk) for chunk in chunks]
                
                # Create BM25 index
                self.bm25_indexes[doc_set_key] = BM25Okapi(tokenized_chunks)
                self.document_chunks[doc_set_key] = {
                    'chunks': chunks,
                    'chunk_ids': chunk_ids,
                    'doc_sources': doc_sources,
                    'tokenized_chunks': tokenized_chunks
                }
                
                # Log document distribution
                doc_distribution = {}
                for doc_id in doc_sources:
                    doc_distribution[doc_id] = doc_distribution.get(doc_id, 0) + 1
                
                print(f"🟢-> BM25 index loaded for {len(chunks)} total chunks:")
                for doc_id, count in doc_distribution.items():
                    print(f"   📄 {doc_id}: {count} chunks")
                
            except Exception as e:
                print(f"🔴-> Error loading BM25 index for {doc_ids}: {e}")
                # Fallback: empty index
                self.bm25_indexes[doc_set_key] = BM25Okapi([[]])
                self.document_chunks[doc_set_key] = {
                    'chunks': [], 'chunk_ids': [], 'doc_sources': [], 'tokenized_chunks': []
                }
    
    def _tokenize_text(self, text: str) -> List[str]:
        """Simple tokenization for BM25."""
        # Remove special characters and convert to lowercase
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        # Split and filter empty tokens
        tokens = [token for token in text.split() if len(token) > 2]
        return tokens
    
    async def hybrid_search(self, queries: List[str], doc_ids: Union[str, List[str]], 
                          top_k: int = TOP_K) -> List[Dict]:
        """
        Perform hybrid search across multiple documents combining BM25 and semantic search.
        
        Args:
            queries: List of search queries (focused sub-queries from query breakdown)
            doc_ids: Single document ID (str) or list of document IDs to search in
            top_k: Number of top results to return
            
        Returns:
            List of search results with enhanced metadata
        """
        # Normalize doc_ids to list
        if isinstance(doc_ids, str):
            doc_ids = [doc_ids]
        
        print(f"🟢-> Starting multi-document hybrid search:")
        print(f"   📄 Documents: {doc_ids}")
        print(f"   🔍 Queries: {len(queries)} focused queries")
        print(f"   🎯 Target results: {top_k}")
        
        client = self._get_client()
        document_filter = self._get_document_filter(doc_ids)
        
        # Ensure BM25 index is loaded for this document set
        doc_set_key = "_".join(sorted(doc_ids))
        if doc_set_key not in self.bm25_indexes:
            self._load_bm25_index(doc_ids)
        
        # Calculate per-query budget based on approach
        if USE_TOTAL_BUDGET_APPROACH and len(queries) > 1:
            per_query_budget = max(1, top_k // len(queries))
            extra_budget = top_k % len(queries)  # Distribute remaining budget
            print(f"🟢-> Total Budget Approach: Distributing {top_k} candidates across {len(queries)} queries")
            print(f"Base budget per query: {per_query_budget}")
            if extra_budget > 0:
                print(f"Extra budget for first {extra_budget} queries: +1 each")
        else:
            per_query_budget = top_k
            extra_budget = 0
            print(f"!!🟢-> Per-Query Approach: Each query gets {per_query_budget} candidates")
        
        all_candidates = {}  # point_id -> {'score': float, 'payload': dict, 'source': str}
        query_performance = {}  # Track performance of each sub-query
        
        print(f"🟢-> Running hybrid search with {len(queries)} focused queries...")
        
        for query_idx, query in enumerate(queries):
            query_candidates = 0
            query_start = time.time()
            
            # Calculate this query's budget
            if USE_TOTAL_BUDGET_APPROACH and len(queries) > 1:
                query_budget = per_query_budget + (1 if query_idx < extra_budget else 0)
                search_limit = query_budget * 2  # Get extra for better selection
            else:
                query_budget = per_query_budget
                search_limit = query_budget * 2
            
            print(f"   Q{query_idx+1} Budget: {query_budget} candidates (searching {search_limit})")
            
            # 1. Semantic Search with Document Filter
            if ENABLE_HYBRID_SEARCH or not ENABLE_HYBRID_SEARCH:  # Always do semantic
                try:
                    query_vector = await self.embedding_manager.encode_query(query)
                    semantic_results = client.search(
                        collection_name=self.collection_name,
                        query_vector=query_vector,
                        query_filter=document_filter,  # Filter by documents
                        limit=search_limit,
                        score_threshold=SCORE_THRESHOLD
                    )
                    
                    # Process semantic results with budget limit
                    semantic_count = 0
                    for result in semantic_results:
                        if USE_TOTAL_BUDGET_APPROACH and semantic_count >= query_budget:
                            break  # Respect budget limit
                            
                        point_id = str(result.id)
                        semantic_score = float(result.score)
                        
                        if point_id not in all_candidates:
                            all_candidates[point_id] = {
                                'semantic_score': 0,
                                'bm25_score': 0,
                                'payload': result.payload,
                                'fusion_score': 0,
                                'contributing_queries': [],
                                'source_doc_id': result.payload.get('doc_id', 'unknown')
                            }
                        
                        # Use max score across queries for semantic
                        if semantic_score > all_candidates[point_id]['semantic_score']:
                            all_candidates[point_id]['semantic_score'] = semantic_score
                        
                        all_candidates[point_id]['contributing_queries'].append({
                            'query_idx': query_idx,
                            'query_text': query[:50] + '...' if len(query) > 50 else query,
                            'semantic_score': semantic_score,
                            'type': 'semantic'
                        })
                        query_candidates += 1
                        semantic_count += 1
                
                except Exception as e:
                    print(f"🔴-> Semantic search failed for query '{query[:50]}...': {e}")
            
            # 2. BM25 Search (if enabled) with Document Filtering
            if ENABLE_HYBRID_SEARCH and doc_set_key in self.bm25_indexes:
                try:
                    tokenized_query = self._tokenize_text(query)
                    bm25_scores = self.bm25_indexes[doc_set_key].get_scores(tokenized_query)
                    
                    # Get top BM25 results with budget consideration
                    chunk_data = self.document_chunks[doc_set_key]
                    bm25_top_indices = np.argsort(bm25_scores)[::-1][:search_limit]
                    
                    # Process BM25 results with budget limit
                    bm25_count = 0
                    for idx in bm25_top_indices:
                        if USE_TOTAL_BUDGET_APPROACH and bm25_count >= query_budget:
                            break  # Respect budget limit
                            
                        if idx < len(chunk_data['chunk_ids']) and bm25_scores[idx] > 0:
                            point_id = str(chunk_data['chunk_ids'][idx])
                            bm25_score = float(bm25_scores[idx])
                            doc_source = chunk_data['doc_sources'][idx]
                            
                            # Verify this chunk is from one of our target documents
                            if doc_source not in doc_ids:
                                continue
                            
                            if point_id not in all_candidates:
                                all_candidates[point_id] = {
                                    'semantic_score': 0,
                                    'bm25_score': 0,
                                    'payload': {
                                        'text': chunk_data['chunks'][idx],
                                        'doc_id': doc_source
                                    },
                                    'fusion_score': 0,
                                    'contributing_queries': [],
                                    'source_doc_id': doc_source
                                }
                            
                            # Use max score across queries for BM25
                            if bm25_score > all_candidates[point_id]['bm25_score']:
                                all_candidates[point_id]['bm25_score'] = bm25_score
                            
                            all_candidates[point_id]['contributing_queries'].append({
                                'query_idx': query_idx,
                                'query_text': query[:50] + '...' if len(query) > 50 else query,
                                'bm25_score': bm25_score,
                                'type': 'bm25'
                            })
                            query_candidates += 1
                            bm25_count += 1
                
                except Exception as e:
                    print(f"🔴-> BM25 search failed for query '{query[:50]}...': {e}")
            
            # Track query performance with budget info
            query_time = time.time() - query_start
            query_performance[query_idx] = {
                'query': query[:80] + '...' if len(query) > 80 else query,
                'candidates_found': query_candidates,
                'budget_allocated': query_budget if USE_TOTAL_BUDGET_APPROACH else 'unlimited',
                'time': query_time
            }
        
        # 3. Score Fusion (Reciprocal Rank Fusion + Weighted Combination)
        self._apply_score_fusion(all_candidates)
        
        # 4. Sort by fusion score and return top results
        sorted_candidates = sorted(
            all_candidates.items(),
            key=lambda x: x[1]['fusion_score'],
            reverse=True
        )
        
        # Convert to result format with enhanced metadata
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
        
        # Log performance summary with document distribution
        approach_name = "Total Budget" if USE_TOTAL_BUDGET_APPROACH else "Per-Query"
        print("")
        print(f"🟢-> Multi-document hybrid search completed ({approach_name} Approach):")
        print(f"   📄 Searched documents: {doc_ids}")
        print(f"   📊 {len(all_candidates)} total candidates from {len(queries)} focused queries")
        print(f"   🎯 Top {len(hybrid_results)} results selected")
        
        # Log document distribution in results
        doc_distribution = {}
        for result in hybrid_results:
            doc_id = result['source_doc_id']
            doc_distribution[doc_id] = doc_distribution.get(doc_id, 0) + 1
        
        print(f"   📈 Result distribution by document:")
        for doc_id, count in doc_distribution.items():
            print(f"      📄 {doc_id}: {count} results")
        
        # Log per-query performance with budget info
        total_budget_used = 0
        for idx, perf in query_performance.items():
            budget_info = f" (budget: {perf['budget_allocated']})" if USE_TOTAL_BUDGET_APPROACH else ""
            print(f"   Q{idx+1}: {perf['candidates_found']} candidates{budget_info} in {perf['time']:.3f}s")
            print(f"        Query: {perf['query']}")
            if USE_TOTAL_BUDGET_APPROACH and isinstance(perf['budget_allocated'], int):
                total_budget_used += perf['candidates_found']
        
        if USE_TOTAL_BUDGET_APPROACH:
            print(f"   🟢-> Total budget efficiency: {total_budget_used}/{top_k} candidates used")
        
        return hybrid_results
    
    def _apply_score_fusion(self, candidates: Dict):
        """Apply advanced score fusion techniques."""
        if not candidates:
            return
        
        # Normalize scores
        semantic_scores = [data['semantic_score'] for data in candidates.values() if data['semantic_score'] > 0]
        bm25_scores = [data['bm25_score'] for data in candidates.values() if data['bm25_score'] > 0]
        
        # Min-Max normalization
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
        
        # Calculate fusion scores
        for point_id, data in candidates.items():
            # Normalize scores
            norm_semantic = (data['semantic_score'] - sem_min) / sem_range if data['semantic_score'] > 0 else 0
            norm_bm25 = (data['bm25_score'] - bm25_min) / bm25_range if data['bm25_score'] > 0 else 0
            
            # Weighted combination
            if ENABLE_HYBRID_SEARCH:
                fusion_score = (SEMANTIC_WEIGHT * norm_semantic) + (BM25_WEIGHT * norm_bm25)
            else:
                fusion_score = norm_semantic
            
            # Add reciprocal rank fusion bonus (helps with ranking diversity)
            rank_bonus = 1.0 / (1.0 + max(norm_semantic, norm_bm25) * 10)
            fusion_score += rank_bonus * 0.1
            
            data['fusion_score'] = fusion_score
    
    def list_available_documents(self) -> List[str]:
        """
        List all available document IDs in the unified collection.
        
        Returns:
            List[str]: List of document IDs
        """
        try:
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
            print(f"🔴-> Error listing documents: {e}")
            return []
    
    def get_document_stats(self, doc_ids: Union[str, List[str]] = None) -> Dict:
        """
        Get statistics about documents in the collection.
        
        Args:
            doc_ids: Specific document IDs to get stats for, or None for all documents
            
        Returns:
            Dict: Document statistics
        """
        try:
            client = self._get_client()
            
            # Normalize doc_ids to list
            if isinstance(doc_ids, str):
                doc_ids = [doc_ids]
            
            # Create filter if specific documents requested
            if doc_ids:
                document_filter = self._get_document_filter(doc_ids)
                result = client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=document_filter,
                    limit=10000,
                    with_payload=True,
                    with_vectors=False
                )
            else:
                result = client.scroll(
                    collection_name=self.collection_name,
                    limit=10000,
                    with_payload=True,
                    with_vectors=False
                )
            
            # Analyze results
            doc_stats = {}
            total_chunks = 0
            
            for point in result[0]:
                doc_id = point.payload.get("doc_id", "unknown")
                if doc_id not in doc_stats:
                    doc_stats[doc_id] = {
                        "chunk_count": 0,
                        "total_chars": 0,
                        "total_words": 0,
                        "avg_chunk_length": 0
                    }
                
                doc_stats[doc_id]["chunk_count"] += 1
                doc_stats[doc_id]["total_chars"] += point.payload.get("char_count", 0)
                doc_stats[doc_id]["total_words"] += point.payload.get("word_count", 0)
                total_chunks += 1
            
            # Calculate averages
            for doc_id, stats in doc_stats.items():
                if stats["chunk_count"] > 0:
                    stats["avg_chunk_length"] = stats["total_chars"] / stats["chunk_count"]
            
            return {
                "total_documents": len(doc_stats),
                "total_chunks": total_chunks,
                "document_stats": doc_stats,
                "queried_documents": doc_ids if doc_ids else "all"
            }
            
        except Exception as e:
            print(f"🔴-> Error getting document stats: {e}")
            return {"error": str(e)}
    
    def cleanup(self):
        """Cleanup search manager resources."""
        print("🧹 Cleaning up Multi-Document Search Manager resources...")
        
        # Close Qdrant client
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
        
        self.bm25_indexes.clear()
        self.document_chunks.clear()
        print("🟢-> Multi-Document Search Manager cleanup completed")