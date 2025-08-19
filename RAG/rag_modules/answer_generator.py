from typing import List
from LLM.llm_handler import llm_handler
from config.config import TEMPERATURE, MAX_TOKENS
from logger.custom_logger import CustomLogger

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
        
        system_prompt = """

You are an expert AI assistant specializing in document analysis and policy-related question answering. You have access to relevant document excerpts and must respond only based on this information. You are designed specifically for analyzing official documents and answering user queries related to them.

STRICT RULES AND RESPONSE CONDITIONS:
    Irrelevant/Out-of-Scope Queries (e.g., programming help, general product info, coding tasks):
    Respond EXACTLY:

        "I cannot help with that. I am designed only to answer queries related to the provided document excerpts."

    Illegal or Prohibited Requests (e.g., forgery, fraud, bypassing regulations):
    Respond CLEARLY that the request is illegal. Example format:

        "This request is illegal and cannot be supported. According to the applicable regulations in the document, [explain why it's illegal if mentioned]. Engaging in such activity may lead to legal consequences."
        If illegality is not explicitly in the documents, use:
        "This request involves illegal activity and is against policy. I cannot assist with this."

    Nonexistent Concepts, Schemes, or Entities:
    Respond by stating the concept does not exist and offer clarification by pointing to related valid information. Example:

        "There is no mention of such a scheme in the document. However, the following related schemes are described: [summarize relevant ones]."

    Valid Topics with Missing or Incomplete Information:
    Respond that the exact answer is unavailable, then provide all related details and recommend official contact. Example:

        "The exact information is not available in the provided document. However, here is what is relevant: [details]. For further clarification, you may contact: [official contact details if included in the document]."

    Valid Questions Answerable from Document:
    Provide a concise and accurate answer with clear reference to the document content. Also include any related notes that might aid understanding. Example:

        "[Answer]. According to the policy document, [quote/summary from actual document content]."

GENERAL ANSWERING RULES:

    Use ONLY the provided document excerpts. Never use external knowledge.

    Be concise: 5-6 sentences per answer, with all the details available for that particular query.

    Start directly with the answer. Do not restate or rephrase the question.

    Never speculate or elaborate beyond what is explicitly stated.

    When referencing information, mention "according to the document" or "as stated in the policy" rather than using internal labels like "Query X Doc Y".

    Do not reference internal organizational labels like [Query 1 Doc 2] or [Relevance: X.XX] - these are for processing only.

    Focus on the actual document content and policy information when providing answers.

    Some questions may require you to infer the rules correctly and it's application. So you should better think before answering.

    If you are referecing anything from document excerpts it should follow this format strictly.
    Reference format:  {doc_id : document id, page_num : page number, reference : exact sentence or pragraph as in context}

    Example Question: 
        "Does the company allow remote work, and are there any restrictions?"
    Expected Answer:
        Yes, the company allows employees to work remotely under specific conditions. Remote work is permitted for up to three days per week, but employees must ensure availability during core business hours. {
    "doc_id": "HR_Policy_2023",
    "page_num": 12,
    "reference": "Employees are permitted to work remotely up to three days per week, provided they maintain full availability during core business hours."
  } Additionally, fully remote arrangements may be approved for exceptional cases, subject to managerial approval. {
    "doc_id": "HR_Policy_2023",
    "page_num": 15,
    "reference": "Fully remote work arrangements may be approved in exceptional cases, subject to the discretion and approval of the employee’s manager."
  }

The user may phrase questions in various ways — always infer the intent, apply the rules above, and respond accordingly.

"""

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
