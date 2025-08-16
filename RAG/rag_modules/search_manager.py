"""
Search Module for Advanced RAG
Handles hybrid search combining BM25 and semantic search with score fusion.
"""

import re
import time
import numpy as np
from typing import List, Dict, Any
from pathlib import Path
from rank_bm25 import BM25Okapi
from qdrant_client import QdrantClient

from config.config import (
    OUTPUT_DIR, TOP_K, SCORE_THRESHOLD, ENABLE_HYBRID_SEARCH,
    BM25_WEIGHT, SEMANTIC_WEIGHT, USE_TOTAL_BUDGET_APPROACH
)


class SearchManager:
    """Manages hybrid search operations combining BM25 and semantic search."""
    
    def __init__(self, embedding_manager):
        """Initialize the search manager."""
        self.embedding_manager = embedding_manager
        self.base_db_path = Path(OUTPUT_DIR)
        self.qdrant_clients = {}
        self.bm25_indexes = {}  # Cache BM25 indexes per document
        self.document_chunks = {}  # Cache chunks for BM25
        print("✅ Search Manager initialized")
    
    def get_qdrant_client(self, doc_id: str) -> QdrantClient:
        """Get or create Qdrant client for a specific document."""
        if doc_id not in self.qdrant_clients:
            db_path = self.base_db_path / f"{doc_id}_collection.db"
            if not db_path.exists():
                raise FileNotFoundError(f"Database not found for document {doc_id}")
            self.qdrant_clients[doc_id] = QdrantClient(path=str(db_path))
        return self.qdrant_clients[doc_id]
    
    def _load_bm25_index(self, doc_id: str):
        """Load or create BM25 index for a document."""
        if doc_id not in self.bm25_indexes:
            print(f"🔄 Loading BM25 index for {doc_id}")
            
            # Get all chunks from Qdrant
            client = self.get_qdrant_client(doc_id)
            collection_name = f"{doc_id}_collection"
            
            try:
                # Get all points from collection
                result = client.scroll(
                    collection_name=collection_name,
                    limit=10000,  # Adjust based on your chunk count
                    with_payload=True,
                    with_vectors=False
                )
                
                chunks = []
                chunk_ids = []
                
                for point in result[0]:
                    chunk_text = point.payload.get('text', '')
                    chunks.append(chunk_text)
                    chunk_ids.append(point.id)
                
                # Tokenize chunks for BM25
                tokenized_chunks = [self._tokenize_text(chunk) for chunk in chunks]
                
                # Create BM25 index
                self.bm25_indexes[doc_id] = BM25Okapi(tokenized_chunks)
                self.document_chunks[doc_id] = {
                    'chunks': chunks,
                    'chunk_ids': chunk_ids,
                    'tokenized_chunks': tokenized_chunks
                }
                
                print(f"✅ BM25 index loaded for {doc_id} with {len(chunks)} chunks")
                
            except Exception as e:
                print(f"❌ Error loading BM25 index for {doc_id}: {e}")
                # Fallback: empty index
                self.bm25_indexes[doc_id] = BM25Okapi([[]])
                self.document_chunks[doc_id] = {'chunks': [], 'chunk_ids': [], 'tokenized_chunks': []}
    
    def _tokenize_text(self, text: str) -> List[str]:
        """Simple tokenization for BM25."""
        # Remove special characters and convert to lowercase
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        # Split and filter empty tokens
        tokens = [token for token in text.split() if len(token) > 2]
        return tokens
    
    async def hybrid_search(self, queries: List[str], doc_id: str, top_k: int = TOP_K) -> List[Dict]:
        """
        Perform hybrid search combining BM25 and semantic search.
        Optimized for focused sub-queries from query breakdown.
        Uses total budget approach to distribute retrieval across queries.
        """
        collection_name = f"{doc_id}_collection"
        client = self.get_qdrant_client(doc_id)
        
        # Ensure BM25 index is loaded
        if doc_id not in self.bm25_indexes:
            self._load_bm25_index(doc_id)
        
        # Calculate per-query budget based on approach
        if USE_TOTAL_BUDGET_APPROACH and len(queries) > 1:
            per_query_budget = max(1, top_k // len(queries))
            extra_budget = top_k % len(queries)  # Distribute remaining budget
            print(f"🎯 Total Budget Approach: Distributing {top_k} candidates across {len(queries)} queries")
            print(f"   📊 Base budget per query: {per_query_budget}")
            if extra_budget > 0:
                print(f"   ➕ Extra budget for first {extra_budget} queries: +1 each")
        else:
            per_query_budget = top_k
            extra_budget = 0
            print(f"🔍 Per-Query Approach: Each query gets {per_query_budget} candidates")
        
        all_candidates = {}  # point_id -> {'score': float, 'payload': dict, 'source': str}
        query_performance = {}  # Track performance of each sub-query
        
        print(f"🔍 Running hybrid search with {len(queries)} focused queries...")
        
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
            
            # 1. Semantic Search
            if ENABLE_HYBRID_SEARCH or not ENABLE_HYBRID_SEARCH:  # Always do semantic
                try:
                    query_vector = await self.embedding_manager.encode_query(query)
                    semantic_results = client.search(
                        collection_name=collection_name,
                        query_vector=query_vector,
                        limit=search_limit,  # Use query-specific limit
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
                                'contributing_queries': []
                            }
                        
                        # Use max score across queries for semantic, but track which queries contributed
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
                    print(f"⚠️ Semantic search failed for query '{query[:50]}...': {e}")
            
            # 2. BM25 Search (if enabled)
            if ENABLE_HYBRID_SEARCH and doc_id in self.bm25_indexes:
                try:
                    tokenized_query = self._tokenize_text(query)
                    bm25_scores = self.bm25_indexes[doc_id].get_scores(tokenized_query)
                    
                    # Get top BM25 results with budget consideration
                    chunk_data = self.document_chunks[doc_id]
                    bm25_top_indices = np.argsort(bm25_scores)[::-1][:search_limit]
                    
                    # Process BM25 results with budget limit
                    bm25_count = 0
                    for idx in bm25_top_indices:
                        if USE_TOTAL_BUDGET_APPROACH and bm25_count >= query_budget:
                            break  # Respect budget limit
                            
                        if idx < len(chunk_data['chunk_ids']) and bm25_scores[idx] > 0:
                            point_id = str(chunk_data['chunk_ids'][idx])
                            bm25_score = float(bm25_scores[idx])
                            
                            if point_id not in all_candidates:
                                all_candidates[point_id] = {
                                    'semantic_score': 0,
                                    'bm25_score': 0,
                                    'payload': {'text': chunk_data['chunks'][idx]},
                                    'fusion_score': 0,
                                    'contributing_queries': []
                                }
                            
                            # Use max score across queries for BM25, but track which queries contributed
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
                    print(f"⚠️ BM25 search failed for query '{query[:50]}...': {e}")
            
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
                'contributing_queries': data['contributing_queries']
            })
        
        # Log performance summary
        approach_name = "Total Budget" if USE_TOTAL_BUDGET_APPROACH else "Per-Query"
        print(f"🔍 Hybrid search completed ({approach_name} Approach):")
        print(f"   📊 {len(all_candidates)} total candidates from {len(queries)} focused queries")
        print(f"   🎯 Top {len(hybrid_results)} results selected")
        
        # Log per-query performance with budget info
        total_budget_used = 0
        for idx, perf in query_performance.items():
            budget_info = f" (budget: {perf['budget_allocated']})" if USE_TOTAL_BUDGET_APPROACH else ""
            print(f"   Q{idx+1}: {perf['candidates_found']} candidates{budget_info} in {perf['time']:.3f}s")
            print(f"        Query: {perf['query']}")
            if USE_TOTAL_BUDGET_APPROACH and isinstance(perf['budget_allocated'], int):
                total_budget_used += perf['candidates_found']
        
        if USE_TOTAL_BUDGET_APPROACH:
            print(f"   💰 Total budget efficiency: {total_budget_used}/{top_k} candidates used")
        
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
    
    def cleanup(self):
        """Cleanup search manager resources."""
        print("🧹 Cleaning up Search Manager resources...")
        
        # Close all Qdrant clients
        for client in self.qdrant_clients.values():
            try:
                client.close()
            except Exception:
                pass
        
        self.qdrant_clients.clear()
        self.bm25_indexes.clear()
        self.document_chunks.clear()
        print("✅ Search Manager cleanup completed")
