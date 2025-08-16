"""
Query Expansion Module for Advanced RAG
Handles breaking down complex queries into focused sub-queries for better information retrieval.
"""

import re
import time
from typing import List
from LLM.lite_llm import generate_lite
from config.config import ENABLE_QUERY_EXPANSION, QUERY_EXPANSION_COUNT

class QueryExpansionManager:
    """Manages query expansion for better information retrieval."""
    
    def __init__(self):
        print("✅ Query Expansion Manager initialized")
    
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
            
            # Ensure we have exactly QUERY_EXPANSION_COUNT queries
            expanded_queries.reverse()
            final_queries = expanded_queries[:QUERY_EXPANSION_COUNT]
            
            print(f"🔄 Query broken down from 1 complex question to {len(final_queries)} focused sub-queries")
            print(f"📌 Original query will be used for final LLM generation only")
            for i, q in enumerate(final_queries):
                print(f"   Sub-query {i+1}: {q[:80]}...")
            
            return final_queries
            
        except Exception as e:
            print(f"⚠️ Query expansion failed: {e}")
            return [original_query]
    
    def _identify_query_components(self, query: str) -> dict:
        """Identify different components in a complex query for better breakdown."""
        components = {
            'processes': [],
            'documents': [],
            'contacts': [],
            'eligibility': [],
            'timelines': [],
            'benefits': []
        }
        
        # Define keywords for different component types
        process_keywords = ['process', 'procedure', 'steps', 'how to', 'submit', 'apply', 'claim', 'update', 'change', 'enroll']
        document_keywords = ['documents', 'forms', 'papers', 'certificate', 'proof', 'evidence', 'requirements']
        contact_keywords = ['email', 'phone', 'contact', 'grievance', 'customer service', 'support', 'helpline']
        eligibility_keywords = ['eligibility', 'criteria', 'qualify', 'eligible', 'conditions', 'requirements']
        timeline_keywords = ['timeline', 'period', 'duration', 'time', 'days', 'months', 'waiting', 'grace']
        benefit_keywords = ['benefits', 'coverage', 'limits', 'amount', 'reimbursement', 'claim amount']
        
        query_lower = query.lower()
        
        # Check for process-related content
        if any(keyword in query_lower for keyword in process_keywords):
            components['processes'].append('process identification')
        
        # Check for document-related content
        if any(keyword in query_lower for keyword in document_keywords):
            components['documents'].append('document requirements')
        
        # Check for contact-related content
        if any(keyword in query_lower for keyword in contact_keywords):
            components['contacts'].append('contact information')
        
        # Check for eligibility-related content
        if any(keyword in query_lower for keyword in eligibility_keywords):
            components['eligibility'].append('eligibility criteria')
        
        # Check for timeline-related content
        if any(keyword in query_lower for keyword in timeline_keywords):
            components['timelines'].append('timeline information')
        
        # Check for benefit-related content
        if any(keyword in query_lower for keyword in benefit_keywords):
            components['benefits'].append('benefit details')
        
        return components
