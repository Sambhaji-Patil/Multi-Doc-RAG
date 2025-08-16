"""
Reranking Module for Advanced RAG
Handles result reranking using cross-encoder models.
"""

from typing import List, Dict
from sentence_transformers import CrossEncoder
from config.config import ENABLE_RERANKING, RERANKER_MODEL, RERANK_TOP_K


class RerankingManager:
    """Manages result reranking using cross-encoder models."""
    
    def __init__(self):
        """Initialize the reranking manager."""
        self.reranker_model = None
        if ENABLE_RERANKING:
            self._init_reranker_model()
        print("✅ Reranking Manager initialized")
    
    def _init_reranker_model(self):
        """Initialize the reranker model."""
        print(f"🔄 Loading reranker model: {RERANKER_MODEL}")
        self.reranker_model = CrossEncoder(RERANKER_MODEL)
        # self.reranker_model.save(RERANKER_MODEL)
        print(f"✅ Reranker model loaded successfully")
    
    async def rerank_results(self, query: str, search_results: List[Dict]) -> List[Dict]:
        """Rerank search results using cross-encoder."""
        if not ENABLE_RERANKING or not self.reranker_model or len(search_results) <= 1:
            return search_results
        
        try:
            # Prepare pairs for reranking
            query_doc_pairs = []
            for result in search_results:
                doc_text = result['payload'].get('text', '')[:512]  # Limit text length
                query_doc_pairs.append([query, doc_text])
            
            # Get reranking scores
            rerank_scores = self.reranker_model.predict(query_doc_pairs)
            
            # Combine with original scores
            for i, result in enumerate(search_results):
                original_score = result.get('score', 0)
                rerank_score = float(rerank_scores[i])
                
                # Weighted combination of original and rerank scores
                result['rerank_score'] = rerank_score
                result['final_score'] = 0.3 * original_score + 0.7 * rerank_score
            
            # Sort by final score
            reranked_results = sorted(
                search_results,
                key=lambda x: x['final_score'],
                reverse=True
            )
            
            print(f"🎯 Reranked {len(search_results)} results")
            return reranked_results[:RERANK_TOP_K]
            
        except Exception as e:
            print(f"⚠️ Reranking failed: {e}")
            return search_results[:RERANK_TOP_K]
