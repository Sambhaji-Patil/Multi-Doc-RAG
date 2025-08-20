"""
Query Expansion Module for Advanced RAG
Handles breaking down complex queries into focused sub-queries for better information retrieval.
"""

import re
import time
from typing import List
from LLM.lite_llm import generate_lite
from config.config import ENABLE_QUERY_EXPANSION, QUERY_EXPANSION_COUNT
from logger.custom_logger import CustomLogger
from prompt.prompt import query_exp

# module-level logger
logger = CustomLogger().get_logger(__file__)

class QueryExpansionManager:
    """Manages query expansion for better information retrieval."""
    
    def __init__(self):
        self.answer_count = 0
        logger.info("Query Expansion Manager initialized", status="initialized")
    
    async def expand_query(self, original_query: str) -> List[str]:
        """Break complex queries into focused parts for better information retrieval."""
        if not ENABLE_QUERY_EXPANSION:
            return [original_query]
        
        try:
            expansion_prompt = query_exp(original_query,QUERY_EXPANSION_COUNT)

            response = generate_lite(
                expansion_prompt,
                temperature=0.3, 
                max_tokens=300   
            )
            
            expanded_queries = []
            
            if response:
                sub_queries = response.strip().split('\n')
                for query in sub_queries:
                    if len(expanded_queries) >= QUERY_EXPANSION_COUNT + 1:  # Stop when we have enough
                        break
                    query = query.strip()
                    # Remove any numbering or bullet points that might be added
                    query = re.sub(r'^[\d\.\-\*\s]+', '', query).strip()
                    if query and len(query) > 10:
                        expanded_queries.append(query)


            if len(expanded_queries) > 1:
                expanded_queries.pop(0)
        

            # If we don't have enough sub-queries, fall back to using the original
            if len(expanded_queries) < 1:
                expanded_queries = [original_query]
            
            # Ensure we have exactly {QUERY_EXPANSION_COUNT} no. of queries only
            expanded_queries.reverse()
            final_queries = expanded_queries[:QUERY_EXPANSION_COUNT]
            
            logger.info("Query expanded", original_query=original_query, sub_queries=len(final_queries))
            self.answer_count += 1
            print(f"🟢 Query {self.answer_count} Expansion successful")
            for i, q in enumerate(final_queries):
                logger.info("Expanded sub-query", index=i+1, query=q[:200])
            
            return final_queries
            
        except Exception as e:
            logger.error("Query expansion failed", error=str(e))
            print("🔴 Query Expansion Failed!!")
            return [original_query]
