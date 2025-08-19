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
            expansion_prompt = f"""Analyze this question and break it down into exactly {QUERY_EXPANSION_COUNT} specific, focused sub-questions that can be searched independently in a document. Each sub-question should target a distinct piece of information or process.

For complex questions with multiple parts, identify:
1. Different processes or procedures mentioned
2. Specific information requests (emails, contact details, forms, etc.)
3. Different entities or subjects involved
4. Sequential steps that might be documented separately
5. Don't Include any extra messages or comments.

Original question: {original_query}

Break this into exactly {QUERY_EXPANSION_COUNT} focused search queries that target different aspects:

Examples of good breakdown:
- "What is the dental claim submission process?"
- "How to update surname/name in policy records?"
- "What are the company contact details and grievance email?"


Provide only {QUERY_EXPANSION_COUNT} focused sub-questions, one per line, without numbering or additional formatting:
Example Reponse:
Here are the focused sub queries
subquery1
subquery2 (if exists)
...

"""

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
