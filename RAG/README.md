# RAG Package - Shastra Docs

An advanced Retrieval-Augmented Generation (RAG) system designed for intelligent document analysis and question answering, particularly optimized for policy documents and official documentation.

## 🚀 Overview

The RAG package provides a modular, production-ready system that combines multiple retrieval techniques with large language models to deliver accurate, context-aware answers from document collections. It's specifically designed for analyzing official documents, policies, and complex regulatory content.

## 🏗️ Architecture

### Core Components

The system follows a modular architecture with six main components:

```
RAG Processor (Orchestrator)
├── Query Expansion Manager    # Breaks complex queries into focused sub-queries
├── Embedding Manager         # Handles semantic embeddings using SentenceTransformers
├── Search Manager           # Hybrid search (BM25 + Semantic) with score fusion
├── Reranking Manager        # Cross-encoder reranking for relevance refinement
├── Context Manager          # Multi-perspective context creation
└── Answer Generator         # LLM-based answer generation with enhanced prompting
```

## 📦 Package Structure

```
rag/
├── __init__.py
├── advanced_rag_processor.py      # Main orchestrator class
└── rag_modules/
    ├── __init__.py
    ├── query_expansion.py          # Query decomposition and expansion
    ├── embedding_manager.py        # Text embedding operations
    ├── search_manager.py          # Hybrid search implementation
    ├── reranking_manager.py       # Result reranking with cross-encoders
    ├── context_manager.py         # Context creation and management
    └── answer_generator.py        # LLM-based answer generation
```

## 🔧 Key Features

### 1. **Advanced Query Processing**
- **Query Expansion**: Automatically breaks complex questions into focused sub-queries
- **Multi-aspect Analysis**: Identifies different components (processes, documents, contacts, etc.)
- **Focused Retrieval**: Each sub-query targets specific information types

### 2. **Hybrid Search System**
- **Semantic Search**: Dense vector similarity using SentenceTransformers
- **Keyword Search**: BM25 for exact term matching
- **Score Fusion**: Reciprocal Rank Fusion with weighted combination
- **Budget Management**: Intelligent distribution of retrieval budget across queries

### 3. **Intelligent Reranking**
- **Cross-encoder Models**: Advanced relevance scoring
- **Multi-stage Filtering**: Progressive refinement of results
- **Score Combination**: Weighted fusion of retrieval and reranking scores

### 4. **Context-Aware Generation**
- **Multi-perspective Context**: Equal representation from all sub-queries
- **Enhanced Prompting**: Specialized prompts for policy and document analysis
- **Error Handling**: Graceful handling of edge cases and invalid requests

### 5. **Production Features**
- **Resource Management**: Efficient cleanup and memory management
- **Performance Monitoring**: Detailed timing and usage statistics
- **Provider Fallback**: Multi-provider LLM support with automatic fallback
- **Health Monitoring**: System status and component health checks

## 🚦 Usage

### Basic Usage

```python
from rag.advanced_rag_processor import AdvancedRAGProcessor

# Initialize the RAG processor
rag = AdvancedRAGProcessor()

# Process a question
question = "What is the dental claim submission process and required documents?"
doc_id = "policy_document_2024"

answer, timings = await rag.answer_question(question, doc_id)
print(answer)
```

### Advanced Usage with Monitoring

```python
import logging
from rag.advanced_rag_processor import AdvancedRAGProcessor

# Initialize with logging
rag = AdvancedRAGProcessor()

# Get system information
system_info = rag.get_system_info()
print(f"RAG Version: {system_info['version']}")

# Process question with detailed tracking
answer, timings = await rag.answer_question(
    question="How to update surname in policy records?",
    doc_id="hr_policy_2024",
    logger=your_logger,
    request_id="req_123"
)

# Monitor performance
print(f"Total processing time: {timings['total_pipeline']:.4f}s")
print(f"Search time: {timings['hybrid_search']:.4f}s")
print(f"Generation time: {timings['llm_generation']:.4f}s")

# Get provider usage statistics
stats = rag.get_provider_usage_stats()
print(f"Provider usage: {stats}")

# Check system health
health = rag.get_health_status()
print(f"System status: {health['status']}")
```

## ⚙️ Configuration

The system relies on configuration from `config/config.py`:

### Key Configuration Options

```python
# Search Configuration
TOP_K = 9                          # Number of chunks to retrieve
SCORE_THRESHOLD = 0.3              # Minimum relevance score
ENABLE_HYBRID_SEARCH = True        # Enable BM25 + Semantic search
USE_TOTAL_BUDGET_APPROACH = True   # Distribute budget across queries

# Query Expansion
ENABLE_QUERY_EXPANSION = True      # Enable query decomposition
QUERY_EXPANSION_COUNT = 3          # Number of sub-queries to generate

# Reranking
ENABLE_RERANKING = True           # Enable cross-encoder reranking
RERANK_TOP_K = 6                  # Number of results to rerank

# Models
EMBEDDING_MODEL = "bge-large-en"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# LLM Generation
TEMPERATURE = 0.1                 # LLM temperature
MAX_TOKENS = 800                  # Maximum response tokens
MAX_CONTEXT_LENGTH = 8000         # Maximum context length
```

### Weight Configuration

```python
# Score fusion weights
BM25_WEIGHT = 0.3                 # Weight for keyword search
SEMANTIC_WEIGHT = 0.7             # Weight for semantic search
```

## 🎯 Specialized Answer Generation

The system includes specialized prompting for different query types:

### Supported Query Categories

1. **Valid Document Queries**: Comprehensive answers with document references
2. **Invalid/Out-of-scope**: Polite redirection to document-specific assistance
3. **Illegal Requests**: Clear refusal with legal context
4. **Missing Information**: Transparent acknowledgment with available alternatives
5. **Non-existent Concepts**: Clarification with related valid information

## 📊 Performance Monitoring

### Timing Breakdown

The system provides detailed performance metrics:

```python
timings = {
    'query_expansion': 0.156,      # Query decomposition time
    'hybrid_search': 0.423,       # Search across all sub-queries  
    'reranking': 0.089,           # Cross-encoder reranking
    'context_creation': 0.012,    # Context assembly
    'llm_generation': 1.245,      # Answer generation
    'total_pipeline': 1.925       # End-to-end processing
}
```

## 🔒 Error Handling & Safety

### Built-in Safety Features

1. **Input Validation**: Comprehensive query validation and sanitization
2. **Content Filtering**: Detection and handling of inappropriate requests
3. **Resource Limits**: Protection against excessive resource usage
4. **Graceful Degradation**: Fallback strategies for component failures
5. **Provider Fallback**: Automatic switching between LLM providers

### Error Recovery

```python
try:
    answer, timings = await rag.answer_question(question, doc_id)
except Exception as e:
    # System provides graceful error messages
    print(f"Processing failed: {e}")
    
    # Check system health
    health = rag.get_health_status()
    if health['status'] == 'degraded':
        # Handle degraded performance
        rag.force_reset_llm_cooldowns()
```

## 🧹 Resource Management

### Cleanup Operations

```python
# Cleanup resources when done
rag.cleanup()

# Reset statistics
rag.reset_provider_stats()

# Force reset provider cooldowns (emergency)
rag.force_reset_llm_cooldowns()
```

## 📈 System Health Monitoring

```python
# Get comprehensive health status
health = rag.get_health_status()

{
    "status": "healthy",           # healthy/degraded/error
    "available_llm_providers": 2,
    "total_llm_providers": 3,
    "provider_details": {...},
    "modules_loaded": 6,
    "last_check": 1703123456.789
}
```

## 🔧 Dependencies

### Core Dependencies

- **sentence-transformers**: Embedding and cross-encoder models
- **qdrant-client**: Vector database operations
- **rank-bm25**: BM25 implementation for keyword search
- **numpy**: Numerical operations and score fusion

### LLM Integration

- Requires configured LLM handler (supports multiple providers)
- Automatic fallback between providers
- Configurable temperature and token limits

## 🚀 Getting Started

1. **Install Dependencies**: Ensure all required packages are installed
2. **Configure Settings**: Update `config/config.py` with your preferences
3. **Initialize Database**: Ensure document collections are processed and stored
4. **Initialize RAG**: Create an `AdvancedRAGProcessor` instance
5. **Process Queries**: Use `answer_question()` method for document Q&A

## 📊 Performance Characteristics

### Typical Processing Times

- **Simple Queries**: 0.5-1.5 seconds
- **Complex Queries**: 1.5-3.0 seconds
- **Multi-aspect Queries**: 2.0-4.0 seconds

### Resource Usage

- **Memory**: ~500MB-1GB (depends on model sizes)
- **CPU**: Moderate during processing, minimal during idle
- **Storage**: Vector databases stored locally

## 🤝 Contributing

The modular architecture makes it easy to extend and customize:

1. **Add New Search Methods**: Extend `SearchManager`
2. **Custom Rerankers**: Implement new reranking strategies
3. **Enhanced Prompting**: Modify answer generation prompts
4. **New Query Types**: Extend query expansion logic

---

## 📄 License

This package is part of the ShastraDocs project. See the main project license for details.



*This RAG system is optimized for document analysis and policy-related question answering. It provides production-ready performance with comprehensive monitoring and error handling capabilities.*