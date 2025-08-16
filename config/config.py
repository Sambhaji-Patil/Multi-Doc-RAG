# RAG Configuration File
# Update these settings as needed

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Common LLM Settings
MAX_TOKENS = 1200 
TEMPERATURE = 0.4

OCR_SPACE_API_KEY = os.getenv("OCR_SPACE_API_KEY", "")
assert OCR_SPACE_API_KEY, "OCR_SPACE_API_KEY not set"

BEARER_TOKEN = os.getenv("BEARER_TOKEN")

# Chunking
CHUNK_SIZE = 400 * 4
CHUNK_OVERLAP = 100 * 4

TOP_K = 12
SCORE_THRESHOLD = 0.3 
RERANK_TOP_K =  9 
BM25_WEIGHT = 0.3 
SEMANTIC_WEIGHT = 0.7

# Advanced RAG Settings
ENABLE_RERANKING = True
ENABLE_HYBRID_SEARCH = True
ENABLE_QUERY_EXPANSION = True
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
QUERY_EXPANSION_COUNT = 3 
SCORE_THRESHOLD = 0.3 
MAX_CONTEXT_LENGTH = 4000*4

USE_TOTAL_BUDGET_APPROACH = True  

EMBEDDING_MODEL ="BAAI/bge-large-en"  
BATCH_SIZE = 8

OUTPUT_DIR = os.getenv("RAG_EMBEDDINGS_PATH", "./RAG/rag_embeddings")


API_HOST = "0.0.0.0"
API_PORT = 8000
API_RELOAD = True


sequence = ["primary", "secondary", "ternary", "quaternary", "quinary", "senary", "septenary", "octonary", "nonary", "denary"]


def get_provider_configs():
    """
    Get configurations for all provider instances.
    You can configure multiple instances of each provider type.
    """
    configs = {
        "groq": [],
        "gemini": [],
        "openai": []
    }
    
    # Groq configurations
    # You can add multiple Groq instances with different API keys
    # set API KEYS ass GROQ_API_KEY_1, GROQ_API_KEY_2... in your environment variables , .env
    DEFAULT_GROQ_MODEL = os.getenv("DEFAULT_GROQ_MODEL", "qwen/qwen3-32b")
    configs["groq"] = [{
        "name": sequence[i],
        "api_key": os.getenv(f"GROQ_API_KEY_{i}"),
        "model": os.getenv(f"GROQ_MODEL_{i}", DEFAULT_GROQ_MODEL)} for i in range(10) if  os.getenv(f"GROQ_API_KEY_{i}", "")
    ]
    
    # Gemini configurations
    # You can add multiple Gemini instances with different API keys
    # set API KEYS ass GEMINI_API_KEY_1, GEMINI_API_KEY_2... in your environment variables , .env
    DEFAULT_GEMINI_MODEL = os.getenv("DEFAULT_GEMINI_MODEL", "gemini-2.0-flash")
    configs["gemini"] = [{
            "name": sequence[i],
            "api_key": os.getenv(f"GEMINI_API_KEY_{i}"),
            "model": os.getenv(f"GEMINI_MODEL_{i}", DEFAULT_GEMINI_MODEL)
        } for i in range(10) if os.getenv(f"GEMINI_API_KEY_{i}", "")
    ]
    
    # OpenAI configurations
    # You can add multiple OpenAI instances with different API keys
    # set API KEYS ass OPENAI_API_KEY_1, OPENAI_API_KEY_2... in your environment variables , .env
    DEFAULT_OPENAI_MODEL = os.getenv("DEFAULT_OPENAI_MODEL", "gpt-4o-mini")
    configs["openai"] = [{
            "name": sequence[i],
            "api_key": os.getenv(f"OPENAI_API_KEY_{i}"),
            "model": os.getenv(f"OPENAI_MODEL_{i}", DEFAULT_OPENAI_MODEL)
        } for i in range(10) if os.getenv(f"OPENAI_MODEL_{i}", "")
    ]
    
    return configs