"""
Context Management Module for Advanced RAG
Handles context creation and management for LLM generation.
"""

from typing import List, Dict
from collections import defaultdict
from config.config import MAX_CONTEXT_LENGTH
from logger.custom_logger import CustomLogger

# module-level logger
logger = CustomLogger().get_logger(__file__)


class ContextManager:
    """Manages context creation for LLM generation."""
    
    def __init__(self):
        """Initialize the context manager."""
        logger.info("Context Manager initialized", status="initialized")
    
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
        
        logger.info("Context creation start", queries=num_queries, chunks_per_query=chunks_per_query, extra=num_extra_chunks)
        try:
            for q_idx in sorted(query_to_chunks.keys()):
                query_chunk_limit = chunks_per_query + (1 if q_idx < num_extra_chunks else 0)
                query_chunks_added = 0

                logger.info("Adding chunks for query", query_index=q_idx+1, limit=query_chunk_limit)

                for i, result in query_to_chunks[q_idx]:
                    if i not in added_chunks and query_chunks_added < query_chunk_limit:
                        text = result['payload'].get('text', '')
                        doc_id = result['payload'].get('doc_id', '')
                        doc_text = f"\n---\n{text}\n"

                        if current_length + len(doc_text) > max_length:
                            logger.warning("Context length limit reached", current_length=current_length)
                            break 
                        context_parts.append(doc_text)
                        current_length += len(doc_text)
                        added_chunks.add(i)
                        query_chunks_added += 1

                logger.info("Query chunks added", query_index=q_idx+1, added=query_chunks_added)

        except Exception as e:
            logger.error("Error during context creation", error=str(e))

        if extra_chunks:
            logger.info("Adding extra chunks", extra_chunks=len(extra_chunks))
            print("🟢 Adding Extra Chunks...")
            for chunk in extra_chunks:
                extra_doc_text = f"\n---\ncontent: {chunk}\n"
                if current_length + len(extra_doc_text) > max_length:
                    logger.warning("Context length limit reached while adding extra chunks.")
                    break
                context_parts.append(extra_doc_text)
                current_length += len(extra_doc_text)

        logger.info("Final context built", chunks=len(added_chunks), chars=current_length)
        return "\n".join(context_parts)