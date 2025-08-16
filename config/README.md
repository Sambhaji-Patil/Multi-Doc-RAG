# ShastraDocs Config Package

Centralized configuration management for the ShastraDocs RAG system. This package handles all system settings, environment variables, and multi-provider API configurations with automatic detection and validation.

## 🚀 Overview

The Config package provides:
- **Centralized Configuration**: Single source of truth for all system settings
- **Auto-Detection**: Automatic discovery of multiple API keys per provider
- **Environment Management**: Secure handling of API keys and sensitive settings
- **Provider Configuration**: Smart configuration for Groq, Gemini, and OpenAI providers
- **Validation**: Built-in validation and fallback mechanisms

## 📦 Package Structure

```
config/
├── __init__.py          # Package initialization
└── config.py           # Main configuration file with all settings
```

## 🎯 Core Features

### 🔧 Multi-Provider Auto-Detection
Automatically detects and configures multiple instances of each LLM provider:

```python
# Automatically finds and configures:
GROQ_API_KEY_1, GROQ_API_KEY_2, ... GROQ_API_KEY_10
GEMINI_API_KEY_1, GEMINI_API_KEY_2, ... GEMINI_API_KEY_10  
OPENAI_API_KEY_1, OPENAI_API_KEY_2, ... OPENAI_API_KEY_10
```

### ⚙️ Intelligent Model Assignment
- **Default Models**: Configurable default models per provider
- **Instance-Specific Models**: Custom models for specific API key instances
- **Fallback Logic**: Automatic fallback to defaults when specific models aren't configured

### 🔒 Secure Environment Handling
- **Environment Variable Loading**: Automatic `.env` file processing
- **Validation**: Required variable checking with clear error messages
- **Secure Defaults**: Safe fallback values for optional settings

## 📋 Configuration Categories

### LLM Provider Configuration


#### Specialized Pipelines
```bash
GROQ_API_KEY_TABULAR = "a groq api key" # Optional: If Groq key already exists in handler, but recomended 
GEMINI_API_KEY_IMAGE = "a gemini api key" # Optional: If Gemini key already exists in handler, but recomended 
```

#### Query Expander
```bash
GROQ_API_KEY_LITE = "a groq api key" # Optional: If Groq key already exists in handler, but recomended 
```

#### Groq Configuration
```bash
# Multiple Groq API Keys
GROQ_API_KEY_1=your_first_groq_key
GROQ_API_KEY_2=your_second_groq_key
GROQ_API_KEY_3=your_third_groq_key

# Default model for all Groq instances
DEFAULT_GROQ_MODEL=qwen/qwen3-32b

# Instance-specific models (optional)
GROQ_MODEL_1=llama3-70b-8192
GROQ_MODEL_2=mixtral-8x7b-32768
# GROQ_MODEL_3 will use DEFAULT_GROQ_MODEL
```

#### Gemini Configuration
```bash
# Multiple Gemini API Keys
GEMINI_API_KEY_1=your_first_gemini_key
GEMINI_API_KEY_2=your_second_gemini_key

# Default model configuration
DEFAULT_GEMINI_MODEL=gemini-2.0-flash

# Instance-specific models
GEMINI_MODEL_1=gemini-1.5-pro
GEMINI_MODEL_2=gemini-2.0-flash
```

#### OpenAI Configuration
```bash
# Multiple OpenAI API Keys
OPENAI_API_KEY_1=your_first_openai_key
OPENAI_API_KEY_2=your_second_openai_key

# Default model configuration
DEFAULT_OPENAI_MODEL=gpt-4o-mini

# Instance-specific models
OPENAI_MODEL_1=gpt-4o
OPENAI_MODEL_2=gpt-4-turbo
```

### RAG System Configuration

#### Retrieval Settings
```python
TOP_K = 9                    # Number of chunks to retrieve
SCORE_THRESHOLD = 0.3        # Minimum relevance score
RERANK_TOP_K = 7            # Results to rerank
BM25_WEIGHT = 0.3           # Keyword search weight
SEMANTIC_WEIGHT = 0.7       # Semantic search weight
```

#### Advanced RAG Features
```python
ENABLE_RERANKING = True         # Cross-encoder reranking
ENABLE_HYBRID_SEARCH = True     # BM25 + Semantic search
ENABLE_QUERY_EXPANSION = True   # Query decomposition
QUERY_EXPANSION_COUNT = 3       # Number of sub-queries
USE_TOTAL_BUDGET_APPROACH = True # Budget distribution
```

#### Processing Configuration
```python
CHUNK_SIZE = 1600              # Characters per chunk
CHUNK_OVERLAP = 400            # Overlap between chunks
MAX_CONTEXT_LENGTH = 16000     # Maximum context for LLM
BATCH_SIZE = 4                 # Embedding batch size
```

### API Configuration
```python
API_HOST = "0.0.0.0"          # API server host
API_PORT = 8000               # API server port
API_RELOAD = True             # Auto-reload in development
BEARER_TOKEN = "your_token"   # API authentication token
```

### External Services
```python
OCR_SPACE_API_KEY = "your_ocr_key"    # OCR Space API key
EMBEDDING_MODEL = "bge-large-en"       # Sentence transformer model
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
```

## 🎯 Auto-Detection Logic

### Provider Instance Naming
The system uses a sequence-based naming convention:

```python
sequence = [
    "primary", "secondary", "ternary", "quaternary", "quinary",
    "senary", "septenary", "octonary", "nonary", "denary"
]

# Results in names like:
# groq-primary, groq-secondary, groq-ternary, ...
# gemini-primary, gemini-secondary, ...
# openai-primary, openai-secondary, ...
```

### Configuration Generation Process

1. **Scan Environment**: Look for `PROVIDER_API_KEY_1` through `PROVIDER_API_KEY_10`
2. **Create Instances**: One instance per detected API key
3. **Assign Models**: Use specific model or fall back to default
4. **Name Assignment**: Use sequence names for easy identification


## ⚙️ Environment Setup Examples

### Minimal Configuration (.env)
```bash
# Minimum required for basic functionality
GROQ_API_KEY_1=your_groq_key
GEMINI_API_KEY_1=your_gemini_key
OCR_SPACE_API_KEY=your_ocr_key
BEARER_TOKEN=your_secure_token
```

### Recommended Configuration (.env)
```bash
# Development setup with multiple providers
GROQ_API_KEY_1=your_groq_key_1
GEMINI_API_KEY_1=your_gemini_key_1

GROQ_API_KEY_LITE=groq_api_key_for_query_expansion

OCR_SPACE_API_KEY=your_ocr_key
BEARER_TOKEN=dev_token_123
```

---

**ShastraDocs Config Package** - Centralized, secure, and intelligent configuration management for enterprise RAG systems.

*Built with auto-detection, validation, and production-ready defaults for seamless deployment across environments.*