"""
Advanced RAG Processor - Modular Version
Orchestrates all RAG components for document question answering.
Version: 3.1 - Updated for Enhanced LLM Handler with Provider Fallback
"""

import time
from typing import Dict, Tuple
from pathlib import Path

# Import all modular components
from .rag_modules.query_expansion import QueryExpansionManager
from .rag_modules.embedding_manager import EmbeddingManager
from .rag_modules.search_manager import SearchManager
from .rag_modules.reranking_manager import RerankingManager
from .rag_modules.context_manager import ContextManager
from .rag_modules.answer_generator import AnswerGenerator

from LLM.llm_handler import llm_handler
from config.config import OUTPUT_DIR, TOP_K


class AdvancedRAGProcessor:
    """
    Advanced RAG processor with modular architecture for better maintainability.
    Orchestrates query expansion, hybrid search, reranking, and answer generation.
    Now supports multi-provider LLM fallback system.
    """
    
    def __init__(self):
        """Initialize the advanced RAG processor with all modules."""
        self.base_db_path = Path(OUTPUT_DIR)
        
        # Initialize all managers
        print("🚀 Initializing Advanced RAG Processor (Modular v3.1)...")
        
        # Core components
        self.embedding_manager = EmbeddingManager()
        self.query_expansion_manager = QueryExpansionManager()
        self.search_manager = SearchManager(self.embedding_manager)
        self.reranking_manager = RerankingManager()
        self.context_manager = ContextManager()
        self.answer_generator = AnswerGenerator()
        
        # Keep reference to LLM handler for info
        self.llm_handler = llm_handler
        
        # Track LLM provider usage for monitoring
        self.provider_usage_stats = {}
        
        print("📦 All modules loaded successfully:")
        print("   🔄 Query Expansion Manager")
        print("   🧠 Embedding Manager")
        print("   🔍 Search Manager (Hybrid)")
        print("   🎯 Reranking Manager")
        print("   📝 Context Manager")
        print("   💬 Answer Generator")
    
    def _update_provider_stats(self, provider: str, stage: str):
        """Update provider usage statistics."""
        if provider not in self.provider_usage_stats:
            self.provider_usage_stats[provider] = {}
        if stage not in self.provider_usage_stats[provider]:
            self.provider_usage_stats[provider][stage] = 0
        self.provider_usage_stats[provider][stage] += 1
    
    async def answer_question(self, question: str, doc_id: str, logger=None, request_id: str = None) -> Tuple[str, Dict[str, float]]:
        """
        Answer a question using advanced RAG techniques with detailed timing.
        
        Args:
            question: The question to answer
            doc_id: Document ID to search in
            logger: Optional logger for tracking
            request_id: Optional request ID for logging
            
        Returns:
            Tuple of (answer, timing_breakdown)
        """
        timings = {}
        providers_used = []
        overall_start = time.time()
        
        try:
            # Check if collection exists
            collection_name = f"{doc_id}_collection"
            try:
                client = self.search_manager.get_qdrant_client(doc_id)
                collection_info = client.get_collection(collection_name)
            except Exception:
                return "I don't have information about this document. Please ensure the document has been processed.", timings
            
            print(f"🚀 Advanced RAG processing for: {question[:100]}...")
            
            # Step 1: Query Expansion
            step_start = time.time()
            try:
                expanded_queries_result = await self.query_expansion_manager.expand_query(question)
                
                # Handle both old and new response formats
                if isinstance(expanded_queries_result, dict) and 'text' in expanded_queries_result:
                    expanded_queries = expanded_queries_result['text']
                    expansion_provider = expanded_queries_result.get('provider', 'unknown')
                    providers_used.append(f"expansion:{expansion_provider}")
                    self._update_provider_stats(expansion_provider, 'query_expansion')
                else:
                    # Backward compatibility with old format
                    expanded_queries = expanded_queries_result
                    expansion_provider = 'legacy'
                
                expansion_time = time.time() - step_start
                timings['query_expansion'] = expansion_time
                if logger and request_id:
                    logger.log_pipeline_stage(request_id, "query_expansion", expansion_time)
                
                print(f"   🔄 Query expansion completed using {expansion_provider}")
                
            except Exception as e:
                print(f"❌ Query expansion failed: {e}")
                # Fallback to original query if expansion fails
                expanded_queries = [question]
                expansion_time = time.time() - step_start
                timings['query_expansion'] = expansion_time
            
            # Step 2: Hybrid Search with Fusion
            step_start = time.time()
            search_results = await self.search_manager.hybrid_search(expanded_queries, doc_id, TOP_K)
            search_time = time.time() - step_start
            timings['hybrid_search'] = search_time
            if logger and request_id:
                logger.log_pipeline_stage(request_id, "hybrid_search", search_time)
            
            if not search_results:
                return "I couldn't find relevant information to answer your question.", timings
            
            # Step 3: Reranking
            step_start = time.time()
            try:
                reranked_results_result = await self.reranking_manager.rerank_results(question, search_results)
                
                # Handle both old and new response formats
                if isinstance(reranked_results_result, dict) and 'text' in reranked_results_result:
                    reranked_results = reranked_results_result['text']
                    rerank_provider = reranked_results_result.get('provider', 'unknown')
                    providers_used.append(f"reranking:{rerank_provider}")
                    self._update_provider_stats(rerank_provider, 'reranking')
                else:
                    # Backward compatibility
                    reranked_results = reranked_results_result
                    rerank_provider = 'legacy'
                
                rerank_time = time.time() - step_start
                timings['reranking'] = rerank_time
                if logger and request_id:
                    logger.log_pipeline_stage(request_id, "reranking", rerank_time)
                
                print(f"   🎯 Reranking completed using {rerank_provider}")
                
            except Exception as e:
                print(f"❌ Reranking failed, using original search results: {e}")
                reranked_results = search_results
                rerank_time = time.time() - step_start
                timings['reranking'] = rerank_time
            
            # Step 4: Multi-perspective Context Creation
            step_start = time.time()
            context = self.context_manager.create_enhanced_context(question, reranked_results)
            context_time = time.time() - step_start
            timings['context_creation'] = context_time
            if logger and request_id:
                logger.log_pipeline_stage(request_id, "context_creation", context_time)

            # Step 5: Enhanced Answer Generation
            step_start = time.time()
            try:
                answer, generation_provider, instance = await self.answer_generator.generate_enhanced_answer(question, context, expanded_queries)
                
                providers_used.append(f"generation:{generation_provider}-{instance}")
                self._update_provider_stats(f"{generation_provider}-{instance}", 'answer_generation')
                
                generation_time = time.time() - step_start
                timings['llm_generation'] = generation_time
                if logger and request_id:
                    logger.log_pipeline_stage(request_id, "llm_generation", generation_time)
                
                print(f"💬 Answer generation completed using {generation_provider}-{instance}")
                
            except Exception as e:
                print(f"❌ Answer generation failed: {e}")
                answer = f"I encountered an error while generating the answer: {str(e)}"
                generation_time = time.time() - step_start
                timings['llm_generation'] = generation_time

            # Calculate total time
            total_time = time.time() - overall_start
            timings['total_pipeline'] = total_time

            print(f"\n✅ Advanced RAG processing completed in {total_time:.4f}s")
            print(f"   🔍 Query expansion: {expansion_time:.4f}s")
            print(f"   🔎 Hybrid search: {search_time:.4f}s") 
            print(f"   🎯 Reranking: {rerank_time:.4f}s")
            print(f"   📝 Context creation: {context_time:.4f}s")
            print(f"   💬 LLM generation: {generation_time:.4f}s")
            print(f"   🤖 Providers used: {', '.join(providers_used)}")

            return answer, timings
            
        except Exception as e:
            error_time = time.time() - overall_start
            timings['error_time'] = error_time
            timings['providers_used'] = providers_used
            print(f"❌ Error in advanced RAG processing: {str(e)}")
            return f"I encountered an error while processing your question: {str(e)}", timings
    
    def get_provider_usage_stats(self) -> Dict:
        """Get statistics about LLM provider usage across all stages."""
        return {
            "usage_by_provider": self.provider_usage_stats.copy(),
            "current_provider_status": self.llm_handler.get_provider_status(),
            "provider_info": self.llm_handler.get_provider_info()
        }
    
    def reset_provider_stats(self):
        """Reset provider usage statistics."""
        self.provider_usage_stats = {}
        print("📊 Provider usage statistics reset")
    
    def force_reset_llm_cooldowns(self):
        """Force reset all LLM provider cooldowns (emergency use)."""
        self.llm_handler.reset_cooldowns()
        print("🔄 LLM provider cooldowns forcefully reset")
    
    def cleanup(self):
        """Cleanup all manager resources."""
        print("🧹 Cleaning up Advanced RAG processor resources...")
        
        # Cleanup search manager (which has the most resources)
        self.search_manager.cleanup()
        
        print("✅ Advanced RAG cleanup completed")
    
    def get_system_info(self) -> Dict:
        """Get comprehensive information about the RAG system."""
        llm_info = self.llm_handler.get_provider_info()
        
        return {
            "version": "3.1 - Enhanced LLM Handler Support",
            "modules": [
                "QueryExpansionManager",
                "EmbeddingManager", 
                "SearchManager",
                "RerankingManager",
                "ContextManager",
                "AnswerGenerator"
            ],
            "base_db_path": str(self.base_db_path),
            "llm_system": {
                "available_providers": [p.name for p in llm_info.get("available_providers", [])],
                "provider_priority": llm_info.get("provider_priority", []),
                "cooldown_duration": llm_info.get("cooldown_duration_seconds", 0),
                "current_status": self.llm_handler.get_provider_status()
            },
            "provider_usage_stats": self.provider_usage_stats,
            "settings": {
                "max_tokens": llm_info.get("max_tokens", "unknown"),
                "temperature": llm_info.get("temperature", "unknown"),
                "top_k": TOP_K
            }
        }
    
    def get_health_status(self) -> Dict:
        """Get health status of all components."""
        try:
            provider_status = self.llm_handler.get_provider_status()
            available_providers = sum(1 for status in provider_status.values() if status.get('available', False))
            
            return {
                "status": "healthy" if available_providers > 0 else "degraded",
                "available_llm_providers": available_providers,
                "total_llm_providers": len(provider_status),
                "provider_details": provider_status,
                "modules_loaded": 6,  # Number of RAG modules
                "last_check": time.time()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "last_check": time.time()
            }