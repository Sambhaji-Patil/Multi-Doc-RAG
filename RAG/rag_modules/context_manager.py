"""
Context Management Module for Advanced RAG
Handles context creation and management for LLM generation.
"""

from typing import List, Dict
from collections import defaultdict
from config.config import MAX_CONTEXT_LENGTH


class ContextManager:
    """Manages context creation for LLM generation."""
    
    def __init__(self):
        """Initialize the context manager."""
        print("🟢-> Context Manager initialized")
    
    def create_enhanced_context(self, question: str, results: List[Dict], max_length: int = MAX_CONTEXT_LENGTH, extra_chunks: List[str] = []) -> str:
        """Create enhanced context ensuring each query contributes equally."""
        # Group results by expanded query index
        query_to_chunks = defaultdict(list)
        for i, result in enumerate(results):
            # Find the most relevant expanded query for this chunk
            if 'contributing_queries' in result and result['contributing_queries']:
                # Use the highest scoring contributing query
                best_contrib = max(result['contributing_queries'], key=lambda cq: cq.get('semantic_score', cq.get('bm25_score', 0)))
                query_idx = best_contrib['query_idx']
            else:
                query_idx = 0  # fallback to first query
            query_to_chunks[query_idx].append((i, result))

        # Sort chunks within each query by their relevance scores
        for q_idx in query_to_chunks:
            query_to_chunks[q_idx].sort(key=lambda x: x[1].get('rerank_score', x[1].get('final_score', x[1].get('score', 0))), reverse=True)

        num_queries = len(query_to_chunks)
        if num_queries == 0 and not extra_chunks:
             return ""
        
        context_parts = []
        current_length = 0
        added_chunks = set()
        
        chunks_per_query = len(results) // num_queries if num_queries > 0 else 0
        num_extra_chunks = len(results) % num_queries if num_queries > 0 else 0
        
        print(f"📊 Context Creation: {num_queries} queries, {chunks_per_query} chunks per query (+{num_extra_chunks} extra)")
        try:
            for q_idx in sorted(query_to_chunks.keys()):
                query_chunk_limit = chunks_per_query + (1 if q_idx < num_extra_chunks else 0)
                query_chunks_added = 0
                
                print(f"   Query {q_idx+1}: Adding up to {query_chunk_limit} chunks")
                
                for i, result in query_to_chunks[q_idx]:
                    if i not in added_chunks and query_chunks_added < query_chunk_limit:
                        text = result['payload'].get('text', '')
                        doc_id = result['payload'].get('doc_id', '')
                        doc_text = f"\n---\ndoc_id: {doc_id}\ncontent: {text}\n"
                        
                        if current_length + len(doc_text) > max_length:
                            print(f"   🔴-> Context length limit reached at {current_length} chars")
                            break 
                        context_parts.append(doc_text)
                        current_length += len(doc_text)
                        added_chunks.add(i)
                        query_chunks_added += 1
                
                
                print(f"   Query {q_idx+1}: Added {query_chunks_added} chunks")
        
        except Exception as e:
            print(e)
            raise
        
        if extra_chunks:
            print(f"   ➕ Adding {len(extra_chunks)} manually provided extra chunks.")
            for chunk in extra_chunks:
                extra_doc_text = f"\n---\ncontent: {chunk}\n"
                if current_length + len(extra_doc_text) > max_length:
                    print(f"   🔴-> Context length limit reached while adding extra chunks.")
                    break
                context_parts.append(extra_doc_text)
                current_length += len(extra_doc_text)

        print(f"📝 Final context: {len(added_chunks)} chunks, {current_length} chars")
        return "\n".join(context_parts)