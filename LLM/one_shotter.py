# Main FastAPI-compatible QA function with enhanced debugging
import re
import time
import asyncio
import httpx
from typing import List, Dict, Tuple, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from datetime import datetime
import random
from functools import lru_cache
from dataclasses import dataclass
import json
import threading

import os
from dotenv import load_dotenv
load_dotenv()

from logger.custom_logger import CustomLogger

# module logger
logger = CustomLogger().get_logger(__file__)


# BEARER_TOKEN = os.getenv("BEARER_TOKEN")

API_KEYS = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3")
]

# Thread-safe API Key Manager
class FastAPICompatibleKeyManager:
    def __init__(self, api_keys: List[str], requests_per_minute: int = 15):
        self.api_keys = [key for key in api_keys if key]
        self.requests_per_minute = requests_per_minute
        self.key_usage = {key: 0 for key in self.api_keys}
        self.last_reset = {key: datetime.now() for key in self.api_keys}
        self.current_index = 0
        self.lock = threading.RLock()
    
    def get_available_key(self) -> str:
        current_time = datetime.now()
        
        with self.lock:
            # Reset counters for keys older than 1 minute
            for key in self.api_keys:
                if (current_time - self.last_reset[key]).total_seconds() >= 60:
                    self.key_usage[key] = 0
                    self.last_reset[key] = current_time
            
            # Find available key
            for i in range(len(self.api_keys)):
                idx = (self.current_index + i) % len(self.api_keys)
                key = self.api_keys[idx]
                
                if self.key_usage[key] < self.requests_per_minute:
                    self.key_usage[key] += 1
                    self.current_index = (idx + 1) % len(self.api_keys)
                    return key
            
            # If all keys at limit, return oldest (with small delay)
            oldest_key = min(self.api_keys, key=lambda k: self.last_reset[k])
            return oldest_key

api_key_manager = FastAPICompatibleKeyManager(API_KEYS)

@lru_cache(maxsize=5)
def get_cached_gemini_llm(api_key: str, temperature: float = 0) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        google_api_key=api_key,
        model="gemini-2.0-flash",
        temperature=temperature,
        convert_system_message_to_human=True
    )

def get_gemini_llm(temperature: float = 0) -> ChatGoogleGenerativeAI:
    api_key = api_key_manager.get_available_key()
    return get_cached_gemini_llm(api_key, temperature)

# Define schemas
class QA(BaseModel):
    answer: str = Field(description="Detailed answer based on context")

class LinkRelevanceAssessment(BaseModel):
    relevant_links: List[Dict[str, str]] = Field(description="Relevant links with URL and reason")
    irrelevant_links: List[str] = Field(description="Irrelevant link URLs")
    can_answer_without_links: bool = Field(description="Can answer with current context")
    explanation: str = Field(description="Assessment explanation")

class SearchNeedAssessment(BaseModel):
    needs_web_search: bool = Field(description="Whether web search is needed")
    missing_information: List[str] = Field(description="Missing information")
    search_queries: List[str] = Field(description="Search queries if needed")
    confidence_score: float = Field(description="Confidence in current answer ability")
    explanation: str = Field(description="Assessment reasoning")

class FinalAnswer(BaseModel):
    answers: List[str] = Field(description="Final answers to all questions")

# Optimized URL extraction
URL_PATTERN = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

def extract_urls_from_text(text: str) -> List[str]:
    urls = URL_PATTERN.findall(text)
    seen = set()
    clean_urls = []
    for url in urls:
        clean_url = url.rstrip('.,;:!?)')
        if clean_url and clean_url not in seen and validate_url(clean_url):
            seen.add(clean_url)
            clean_urls.append(clean_url)
    return clean_urls

@lru_cache(maxsize=100)
def validate_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return bool(result.scheme and result.netloc)
    except:
        return False

# FastAPI-compatible async scraping
async def scrape_url_fastapi_compatible(url: str, max_chars: int = 3000) -> Dict[str, str]:
    """FastAPI-compatible URL scraping"""
    try:
        timeout = httpx.Timeout(15.0)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'advertisement', 'message']):
                tag.decompose()
            

            # Extract clean text
            text_content = soup.get_text(separator=' ', strip=True)
            
            # Clean and truncate
            cleaned_text = ' '.join(text_content.split())
            if len(cleaned_text) > max_chars:
                cleaned_text = cleaned_text[:max_chars] + "..."

            
            return {
                'url': url,
                'content': cleaned_text,
                'status': 'success',
                'length': len(cleaned_text),
                'title': soup.title.string if soup.title else 'No title'
            }
            
    except httpx.TimeoutException:
        logger.warning("Timeout scraping URL", url=url)
        return {
            'url': url,
            'content': "Timeout error - could not retrieve content",
            'status': 'timeout',
            'length': 0,
            'title': 'Timeout'
        }
    except Exception as e:
        logger.error("Error scraping URL", url=url, error=str(e)[:100])
        return {
            'url': url,
            'content': f"Error retrieving content: {str(e)[:100]}",
            'status': 'error',
            'length': 0,
            'title': 'Error'
        }

async def scrape_urls_fastapi(urls: List[str], max_chars: int = 3000) -> List[Dict[str, str]]:
    """FastAPI-compatible batch URL scraping"""
    if not urls:
        return []
    
    logger.info("Scraping URLs (FastAPI compatible)", url_count=len(urls))
    
    # Limit concurrent requests to avoid overwhelming servers
    semaphore = asyncio.Semaphore(7)
    
    async def scrape_with_semaphore(url):
        async with semaphore:
            return await scrape_url_fastapi_compatible(url, max_chars)
    
    tasks = [scrape_with_semaphore(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle exceptions
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error("Exception scraping URL", url=urls[i], error=str(result))
            processed_results.append({
                'url': urls[i],
                'content': f"Exception occurred: {str(result)[:100]}",
                'status': 'exception',
                'length': 0,
                'title': 'Exception'
            })
        else:
            processed_results.append(result)
    
    successful = sum(1 for r in processed_results if r['status'] == 'success')
    logger.info("Scraping complete", successful=successful, total=len(urls))
    return processed_results

# search function
async def search_web_async(query: str, num_results: int = 3) -> List[Dict[str, str]]:
    """Async web search using DuckDuckGo"""
    try:
        search_url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(search_url)
            data = response.json()
        
        results = []
        
        if 'RelatedTopics' in data:
            for topic in data['RelatedTopics'][:num_results]:
                if isinstance(topic, dict) and 'FirstURL' in topic:
                    results.append({
                        'title': topic.get('Text', 'No title')[:100],
                        'url': topic.get('FirstURL', ''),
                        'snippet': topic.get('Text', '')[:200]
                    })
        
        # If no results, try InstantAnswer
        if not results and 'Answer' in data and data['Answer']:
            results.append({
                'title': f"Answer for: {query}",
                'url': data.get('AbstractURL', ''),
                'snippet': data.get('Answer', '')
            })
        
        logger.info("Found search results", query=query, results_count=len(results))
        return results
        
    except Exception as e:
        logger.error("Search error", query=query, error=str(e))
        return []

# Enhanced assessment functions with better prompts
def assess_link_relevance_enhanced(context: str, questions: List[str], found_urls: List[str]) -> LinkRelevanceAssessment:
    """Enhanced link relevance assessment with better error handling"""
    
    try:
        llm = get_gemini_llm(temperature=0.1)
        
        # Create a more detailed prompt
        prompt = ChatPromptTemplate.from_messages([
            ("human", """You are an expert content analyst. Analyze whether the current context can fully answer all questions, and which URLs might contain essential additional information.

CURRENT CONTEXT:
{context}

QUESTIONS TO ANSWER:
{questions}

FOUND URLs:
{urls}

TASK: Determine if you can fully answer ALL questions using ONLY the current context. Be thorough and conservative.

If ANY question lacks sufficient detail or the context seems incomplete, mark can_answer_without_links as false.

Analyze each URL to determine if it likely contains relevant information for answering the questions.

Respond in this EXACT JSON format:
{{
    "relevant_links": [
        {{"url": "exact_url_here", "reason": "specific reason why this URL is relevant"}}
    ],
    "irrelevant_links": ["url1", "url2"],
    "can_answer_without_links": false,
    "explanation": "Clear explanation of your assessment"
}}""")
        ])
        
        # Format inputs nicely
        questions_text = "\n".join([f"{i+1}. {q.strip()}" for i, q in enumerate(questions[:5])])
        urls_text = "\n".join([f"- {url}" for url in found_urls[:8]])
        
        response = llm.invoke(prompt.format_messages(
            context=context[:2000],
            questions=questions_text,
            urls=urls_text
        ))
        
        # Parse JSON response
        try:
            result_dict = json.loads(response.content)
            result = LinkRelevanceAssessment(**result_dict)
        except:
            # Try extracting JSON from response
            import re
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                result_dict = json.loads(json_match.group())
                result = LinkRelevanceAssessment(**result_dict)
            else:
                raise ValueError("Could not parse JSON response")
        
        logger.info("Link assessment", relevant_count=len(result.relevant_links), can_answer=result.can_answer_without_links)
        return result

    except Exception as e:
        logger.error("Link assessment error", error=str(e))
        # Conservative fallback
        return LinkRelevanceAssessment(
            relevant_links=[{"url": url, "reason": "Included due to assessment error"} for url in found_urls[:3]],
            irrelevant_links=found_urls[3:],
            can_answer_without_links=False,
            explanation=f"Assessment failed, including links conservatively: {str(e)[:100]}"
        )

def assess_search_necessity_enhanced(context: str, questions: List[str]) -> SearchNeedAssessment:
    """Enhanced search necessity assessment"""
    try:
        llm = get_gemini_llm(temperature=0.1)
        
        prompt = ChatPromptTemplate.from_messages([
            ("human", """You are an expert information analyst. Assess whether the current context provides sufficient information to fully answer all questions.

AVAILABLE CONTEXT:
{context}

QUESTIONS:
{questions}

ANALYSIS CRITERIA:
1. Can ALL questions be answered comprehensively with the current context?
2. Is any crucial information missing that would require web search?
3. Are the answers complete and detailed enough?
4. Be conservative - if there's uncertainty, recommend search.

Respond in this EXACT JSON format:
{{
    "needs_web_search": true,
    "missing_information": ["specific missing info 1", "specific missing info 2"],
    "search_queries": ["focused search query 1", "focused search query 2"],
    "confidence_score": 0.4,
    "explanation": "detailed reasoning for your assessment"
}}""")
        ])
        
        questions_text = "\n".join([f"{i+1}. {q.strip()}" for i, q in enumerate(questions[:5])])
        
        response = llm.invoke(prompt.format_messages(
            context=context[:2500],
            questions=questions_text
        ))
        
        # Parse JSON response
        import json
        try:
            result_dict = json.loads(response.content)
            result = SearchNeedAssessment(**result_dict)
        except:
            import re
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                result_dict = json.loads(json_match.group())
                result = SearchNeedAssessment(**result_dict)
            else:
                raise ValueError("Could not parse JSON response")
        
        logger.info("Search assessment", needs_search=result.needs_web_search, confidence=result.confidence_score)
        return result
        
    except Exception as e:
        logger.error("Search assessment error", error=str(e))
        # Conservative fallback
        return SearchNeedAssessment(
            needs_web_search=True,
            missing_information=["Assessment failed, being conservative"],
            search_queries=[f"{q[:50]}..." for q in questions[:2]],
            confidence_score=0.3,
            explanation=f"Assessment error, recommending search: {str(e)[:100]}"
        )

def generate_answers_enhanced(context: str, questions: List[str]) -> List[str]:
    """Enhanced answer generation with better content utilization"""

    try:
        llm = get_gemini_llm(temperature=0.7)

        # Debug: log context summary to verify content is there
        logger.info("Context length", chars=len(context))
        if "Additional Information:" in context:
            additional_start = context.find("Additional Information:")
            logger.info("Additional info found", position=additional_start)
            additional_content = context[additional_start:additional_start+500]
            logger.debug("Sample additional content", preview=additional_content[:200])

        prompt = ChatPromptTemplate.from_messages([
            ("human", """You are an expert research assistant. You must analyze ALL provided context thoroughly and use EVERY relevant piece of information to answer the questions comprehensively.

FULL CONTEXT TO ANALYZE:
{context}

CRITICAL INSTRUCTIONS:
1. READ AND USE ALL CONTEXT: Carefully examine the entire context, including any "Additional Information" sections
2. COMPREHENSIVE ANSWERS: Use ALL relevant information from BOTH the original context AND any additional scraped content
3. CITE SOURCES: When using information from additional sources, mention where it came from.
4. BE THOROUGH: Don't just use the original context - actively look for and incorporate information from scraped websites
5. DETAILED EXPLANATIONS: Provide comprehensive, well-structured answers with specific details
6. IF MISSING INFO: Only state information is missing if it's truly not available in ANY part of the provided context
7. Your explaination should be short but informative.
8. If your answer is based on context, then mention the exact part referenced.
9. If the context is of different than actual language, then reference should in contexts's language itself followed by its meaning in users queries language.             
10. Think thoroughly before answering.
11. If you are using any reference from Orginal Context mention them in curly brackets in this format:
            {doc_id : document id, page_num : page number, reference : exact sentence or pragraph as in context}
             
The context may contain multiple sections:
- Original context
- Additional Information from relevant links  
- Search results content

USE ALL OF THESE SECTIONS TO PROVIDE COMPLETE ANSWERS.

Respond in this EXACT JSON format:
{{
    "answers": [
        "<Correct Answer to the question 1{doc_id: \"doc_fcebebab243d\", page_num: \"2\", reference: \"reference string\"} answer continued>",
        "<Correct Answer to the question 2 only if question 2 exists.>",
        ...
    ]
}}
             

QUESTIONS TO ANSWER:
{questions}
        """)
        ])

        questions_text = "\n".join([f"{i+1}. {q.strip()}" for i, q in enumerate(questions)])

        # Ensure we're passing the full context
        full_context = context
        if len(full_context) > 8000:  # Truncate if too long but keep important parts
            original_end = full_context.find("Additional Information:")
            if original_end > 0:
                # Keep original context and truncated additional info
                additional_part = full_context[original_end:original_end+6000]
                full_context = full_context[:original_end] + additional_part
            else:
                full_context = full_context[:8000]

        logger.info("Sending context to LLM", chars=len(full_context))

        response = llm.invoke(prompt.format_messages(
            context=full_context,
            questions=questions_text
        ))

        logger.info("LLM response received", length=len(response.content))
        logger.debug("LLM response preview", preview=response.content[:300])

        # Parse JSON response with better error handling
        import json
        import re
        try:
            # Try direct JSON parsing first
            result_dict = json.loads(response.content)
            result = FinalAnswer(**result_dict)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*"answers".*\}', response.content, re.DOTALL)
            if json_match:
                try:
                    result_dict = json.loads(json_match.group())
                    result = FinalAnswer(**result_dict)
                except Exception:
                    # Extract answers array specifically
                    logger.warning("Answer was not in proper JSON")
                    answers_match = re.search(r'"answers"\s*:\s*\[(.*?)\]', response.content, re.DOTALL)
                    if answers_match:
                        answers_text = answers_match.group(1)
                        # Split by quotes and clean
                        answers = []
                        for part in answers_text.split('\",'):
                            clean_answer = part.strip().strip('"').strip(',').strip()
                            if clean_answer and len(clean_answer) > 10:
                                answers.append(clean_answer)
                        result = FinalAnswer(answers=answers)
                    else:
                        raise ValueError("Could not extract answers")
            else:
                # Last resort - split response by questions
                lines = response.content.split('\n') if len(questions) > 1 else [response.content]
                answers = []
                current_answer = ""

                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('{') or line.startswith('}') or line.startswith('"answers"'):
                        continue

                    # Check if this looks like a new answer
                    if (
                        line.startswith('"')
                        or any(f"{i+1}." in line for i in range(len(questions)))
                        or (current_answer and len(line) > 50 and line[0].isupper())
                    ):
                        if current_answer and len(current_answer) > 20:
                            answers.append(current_answer.strip().strip('"').strip(','))
                        current_answer = line.strip('"').strip(',')
                    else:
                        current_answer += " " + line.strip('"').strip(',')

                if current_answer and len(current_answer) > 2:
                    answers.append(current_answer.strip().strip('"').strip(','))

                # Ensure we have the right number of answers
                while len(answers) < len(questions):
                    answers.append(f"Unable to generate answer for question {len(answers)+1}")
                if len(questions) == len(answers):
                    answers = ["\n".join(answers)]

                result = FinalAnswer(answers=answers[:len(questions)])

        logger.info("Generated answers", count=len(result.answers))

        return result.answers

    except Exception as e:
        logger.exception("Answer generation error", error=str(e))
        return [f"Error generating answer for question {i+1}: {str(e)[:100]}" for i in range(len(questions))]

# Debug function to verify content integration
async def debug_qa_process(context: str, questions: List[str]) -> Dict:
    """Debug version that returns detailed process information"""
    
    logger.info("Starting debug QA process")
    
    # Extract URLs
    found_urls = extract_urls_from_text(context + "\n" + "\n".join(questions))
    
    # Assess search necessity
    # Determine strategy
    should_scrape_links = len(found_urls) > 0
    
    
    debug_info = {
        "found_urls": found_urls,
        "strategy": {
            "should_scrape_links": should_scrape_links,
        },
        "scrape_results": [],
        "final_context_length": len(context),
        "additional_content_length": 0
    }
    
    # If we would scrape/search, do it
    if should_scrape_links:
        all_urls = found_urls
        
        if all_urls:
            scrape_results = await scrape_urls_fastapi(all_urls)
            debug_info["scrape_results"] = [
                {
                    "url": r["url"],
                    "status": r["status"],
                    "length": r["length"],
                    "title": r.get("title", ""),
                    "content_preview": r["content"][:200] if r["content"] else ""
                }
                for r in scrape_results
            ]
            
            # Build additional content
            additional_content = ""
            for result in scrape_results:
                if result['status'] == 'success' and result['length'] > 50:
                    additional_content += f"\n\n" + "="*50 + "\n"
                    additional_content += f"SOURCE: Scraped from {result['url']}\n"
                    additional_content += f"TITLE: {result.get('title', 'No title')}\n"
                    additional_content += "-"*30 + " CONTENT " + "-"*30 + "\n"
                    additional_content += f"{result['content']}\n"
                    additional_content += "="*50 + "\n"
            
            debug_info["additional_content_length"] = len(additional_content)
            
            final_context = context + f"\n\nADDITIONAL INFORMATION FROM SCRAPED SOURCES:\n{additional_content}"
            debug_info["final_context_length"] = len(final_context)
            
            # Generate answers
            answers = generate_answers_enhanced(final_context, questions)
            debug_info["answers"] = answers
    else:
        answers = generate_answers_enhanced(context, questions)
        debug_info["answers"] = answers
    
    return debug_info

# Main FastAPI-compatible function
async def get_oneshot_answer(context: str, questions: List[str]) -> List[str]:
    """Main FastAPI-compatible QA function"""
    
    start_time = time.time()
    logger.info("FastAPI QA start", questions=len(questions), chars=len(context))
    
    # Step 1: Extract URLs
    combined_text = context + "\n" + "\n".join(questions)
    found_urls = extract_urls_from_text(combined_text)
    
    logger.info("Found URLs", count=len(found_urls))
    
    should_scrape_links = len(found_urls) > 0
    
    logger.info("Strategy", scrape_links=should_scrape_links)
    
    # Step 4: Early return if sufficient context
    if not should_scrape_links:
        logger.info("Sufficient context, generating answers")
        answers = generate_answers_enhanced(context, questions)
        logger.info("Completed FastAPI QA", elapsed_seconds=round(time.time() - start_time, 2))
        return answers
    
    # Step 5: Gather additional content
    all_urls = found_urls
    
    # Step 6: Scrape URLs
    additional_content = ""
    successful_scrapes = 0
    if all_urls:
        logger.info("Scraping URLs for FastAPI QA", url_count=len(all_urls))
        scrape_results = await scrape_urls_fastapi(all_urls, max_chars=4000)
        
        for i, result in enumerate(scrape_results):
            if result['status'] == 'success':
                metadata = "Additional Source"
                
                # Better formatting for LLM recognition
                additional_content += f"\n\n" + "="*50 + "\n"
                additional_content += f"SOURCE: {metadata}\n"
                additional_content += f"URL: {result['url']}\n"
                additional_content += "-"*30 + " CONTENT " + "-"*30 + "\n"
                additional_content += f"{result['content']}\n"
                additional_content += "="*50 + "\n"
                successful_scrapes += 1
                
                # Debug output
                logger.info("Scraped URL", url=result['url'], title=result.get('title', 'No title'), length=result['length'])
                logger.debug("Scraped content preview", preview=result['content'][:100])
        
    logger.info("Scraping summary", successful=successful_scrapes, total=len(all_urls))
    logger.info("Total additional content", chars=len(additional_content))
    
    # Step 7: Generate final answers with better context integration
    if additional_content:
        logger.info("Integrating additional content")
        final_context = context + f"\n\nADDITIONAL INFORMATION FROM SCRAPED SOURCES:\n{additional_content}"
        logger.info("Final context stats", original_chars=len(context), additional_chars=len(additional_content), total_chars=len(final_context))
        # Verify the content is properly formatted
        if "ADDITIONAL INFORMATION FROM SCRAPED SOURCES:" in final_context:
            logger.info("Additional content properly integrated")
        else:
            logger.warning("Additional content integration failed")
    else:
        logger.warning("No additional content to integrate")
        final_context = context
    
    answers = generate_answers_enhanced(final_context, questions)
    
    total_time = time.time() - start_time
    logger.info("FastAPI QA completed", elapsed_seconds=round(total_time, 2))
    
    return answers

# Simple version for quick answers
async def get_simple_answer(context: str, questions: List[str]) -> List[str]:
    """Simple FastAPI-compatible version using only provided context"""
    return generate_answers_enhanced(context, questions)