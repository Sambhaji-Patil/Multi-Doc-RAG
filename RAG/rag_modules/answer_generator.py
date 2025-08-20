from typing import List
from LLM.llm_handler import llm_handler
from config.config import TEMPERATURE, MAX_TOKENS
from logger.custom_logger import CustomLogger
from prompt.prompt import system_msg_answer_gen

# module logger
logger = CustomLogger().get_logger(__file__)
"""
Answer Generation Module for Advanced RAG
Handles LLM-based answer generation with enhanced prompting.
"""

from typing import List
from LLM.llm_handler import llm_handler
from config.config import TEMPERATURE, MAX_TOKENS


class AnswerGenerator:
    """Manages answer generation using LLM."""
    
    def __init__(self):
        """Initialize the answer generator."""
        self.llm_handler = llm_handler
        self.answer_count = 0  # Counter for generated answers
    logger.info("Answer Generator initialized")
    
    async def generate_enhanced_answer(self, original_question: str, context: str, expanded_queries: List[str]) -> str:
        """Generate enhanced answer using the original question with retrieved context."""
        
        # Use only the original question for LLM generation
        query_context = f"Question: {original_question}"
        
        system_prompt = system_msg_answer_gen

        user_prompt = f"""{query_context}

Document Excerpts:
{context}

Provide a comprehensive answer based on the document excerpts above:"""
        
        try:
            answer, provider, instance = await self.llm_handler.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS
            )
            self.answer_count += 1
            print(f"🟢 Answer {self.answer_count} generated successfully")
            return answer.strip(), provider, instance
            
        except Exception as e:
            logger.exception("Error generating enhanced", error=str(e))
            return "I encountered an error while generating the response.", "None", "None" 
