# ShastraDocs Logger Package

An advanced in-memory logging system designed for RAG API request tracking with detailed pipeline timing, performance analytics, and comprehensive monitoring capabilities. Built for HuggingFace Spaces and environments without persistent storage.

## 🚀 Overview

The Logger package provides:
- **Enhanced Request Tracking**: Detailed logging of RAG pipeline stages with precise timing
- **In-Memory Storage**: No file system dependencies, perfect for HuggingFace Spaces
- **Performance Analytics**: Comprehensive pipeline performance monitoring
- **Real-time Monitoring**: Live request tracking with unique identifiers
- **Export Capabilities**: JSON export with filtering and aggregation options

## 📦 Package Structure

```
logger/
├── __init__.py          # Package initialization
└── logger.py           # Main logging system with RAGLogger class
```

## 🎯 Core Features

### ⏱️ Detailed Pipeline Timing
Tracks every stage of the RAG pipeline with microsecond precision:
- Query expansion timing
- Hybrid search performance
- Semantic/BM25 search breakdown
- Reranking duration
- Context creation time
- LLM generation timing
- End-to-end request processing

### 📊 Per-Question Analytics
Individual question processing metrics:
- Question-specific timing breakdown
- Pipeline stage performance per question
- Answer length and complexity tracking
- Success/failure tracking per question

### 🔍 Request Lifecycle Management
Complete request tracking from start to finish:
- Unique request ID generation
- Request start/end timestamps
- Status tracking (success/error/partial)
- Document preprocessing detection
- Error message capture

## 📋 Core Components

### RAGLogger Class
Main logging orchestrator with comprehensive tracking capabilities.

#### Key Methods

**Request Lifecycle:**
```python
# Start request timing
request_id = rag_logger.generate_request_id()
rag_logger.start_request_timing(request_id)

# Track pipeline stages
rag_logger.log_pipeline_stage(request_id, "query_expansion", 0.156)
rag_logger.log_pipeline_stage(request_id, "hybrid_search", 0.423)

# Track individual questions
rag_logger.log_question_timing(
    request_id, question_index, question, answer, 
    duration, pipeline_timings
)

# Complete request
timing_data = rag_logger.end_request_timing(request_id)
final_request_id = rag_logger.log_request(
    document_url, questions, answers, processing_time,
    status, error_message, document_id, was_preprocessed, timing_data
)
```

### LogEntry Dataclass
Structured data model for log entries:

```python
@dataclass
class LogEntry:
    timestamp: str                          # ISO timestamp
    request_id: str                         # Unique request identifier
    document_url: str                       # Document URL processed
    questions: List[str]                    # Questions asked
    answers: List[str]                      # Answers generated
    processing_time_seconds: float          # Total processing time
    total_questions: int                    # Number of questions
    status: str                            # success/error/partial
    error_message: Optional[str]           # Error details if any
    document_id: Optional[str]             # Generated document ID
    was_preprocessed: bool                 # Whether document was cached
    request_start_time: str                # Request start timestamp
    request_end_time: str                  # Request end timestamp
    pipeline_timings: Dict[str, Any]       # Pipeline stage timings
    question_timings: List[Dict[str, Any]] # Per-question timings
```

### PipelineTimings Dataclass
Detailed timing breakdown for RAG pipeline stages:

```python
@dataclass
class PipelineTimings:
    query_expansion_time: float = 0.0      # Query decomposition time
    hybrid_search_time: float = 0.0        # Combined search time
    semantic_search_time: float = 0.0      # Vector similarity time
    bm25_search_time: float = 0.0         # Keyword search time
    score_fusion_time: float = 0.0         # Score combination time
    reranking_time: float = 0.0           # Cross-encoder reranking
    context_creation_time: float = 0.0     # Context assembly time
    llm_generation_time: float = 0.0       # Answer generation time
    total_pipeline_time: float = 0.0       # End-to-end pipeline time
```