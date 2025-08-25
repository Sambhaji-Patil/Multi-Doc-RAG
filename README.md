---
title: "ShastraDocsv2"
emoji: "📚"
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
license: mit
tags: [rag, document-analysis, llm, enterprise, ai]
---

<div align="center">

# 📚 ShastraDocs v2
## Enterprise RAG System for Document Analysis

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-ready-green.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)

**🚀 Production-ready API •**3. OCR Space API Issues**
```bash
# Verify OCR API key
export OCR_SPACE_API_KEY="your_key"

# Test OCR endpoint
curl -X POST "https://api.ocr.space/parse/image" \
  -F "apikey=your_key" \
  -F "url=https://example.com/image.jpg"
```

**4. Memory Issues**
```python
# Reduce batch sizes in config.py
BATCH_SIZE = 16
CHUNK_SIZE = 1200
```

**5. Web Interface Issues**
```bash
# Check static file serving
curl http://localhost:7860/static/styles.css

# Verify templates directory
ls templates/
# Should contain: index.html, service-worker.js
```ormats • 🤖 Multi-LLM Support • ⚡ Advanced Retrieval**

[**Try the API**](#-quick-start) | [**Full Docs**](https://github.com/Sambhaji-Patil/Multi-Doc-RAG) | [**GitHub**](https://github.com/Sambhaji-Patil/Multi-Doc-RAG)

</div>

---

## 🚀 Overview

ShastraDocs v2 is a production-ready, modular RAG system designed for comprehensive document analysis and intelligent question answering. Built with enterprise requirements in mind, it supports 8+ document formats, features intelligent multi-provider LLM management, and provides advanced retrieval techniques with comprehensive monitoring capabilities.

### ✨ Key Highlights

- **🎯 Multi-Format Support**: PDF, DOCX, PPTX, XLSX, Images, Text, CSV, and URLs
- **⚡ Intelligent Processing**: Automatic format detection with specialized handlers
- **🔄 Multi-Provider LLM**: Smart rotation between Groq, Gemini, and OpenAI with rate limit handling
- **🔍 Advanced Retrieval**: Hybrid search with BM25 + semantic search and cross-encoder reranking
- **�️ LanceDB Vector Storage**: High-performance vector database with unified document collections
- **🌐 Web Interface**: Modern PWA with document viewer and interactive chat
- **�📊 Production Features**: Comprehensive logging, monitoring, and health checks
- **🐳 Docker Ready**: Containerized deployment with HuggingFace Spaces optimization
- **💰 Cost Effective**: Process 200+ questions at $0 cost using free tier rotation

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ShastraDocs v2                           │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI REST API (Authentication, Endpoints, Health Checks)    │
├─────────────────────────────────────────────────────────────────┤
│     Multi-Provider LLM Handler (Groq, Gemini, OpenAI)           │
├─────────────────────────────────────────────────────────────────┤
│        Advanced RAG Processor (Query Expansion, Reranking)      │
├─────────────────────────────────────────────────────────────────┤
│   Document Preprocessing (8+ Formats, OCR, Table Extraction)    │
├─────────────────────────────────────────────────────────────────┤
│    Vector Storage & Search (LanceDB, Hybrid Search, Caching)    │
├─────────────────────────────────────────────────────────────────┤
│  Comprehensive Logging & Monitoring (Request Tracking, Stats)   │
└─────────────────────────────────────────────────────────────────┘
```

## 📦 Project Structure

```
Multi-Doc-RAG/
├── 📁 api/                          # FastAPI REST API
│   ├── __init__.py
│   ├── api.py                       # Main API endpoints and authentication
│   └── README.md                    # API documentation
├── 📁 config/                       # Centralized configuration
│   ├── __init__.py
│   ├── config.py                    # Auto-detecting multi-provider configs
│   └── README.md                    # Configuration documentation
├── 📁 LLM/                         # Multi-provider LLM management
│   ├── __init__.py
│   ├── llm_handler.py              # Unified multi-provider handler
│   ├── one_shotter.py              # Enhanced QA with web scraping
│   ├── image_answerer.py           # Specialized image analysis
│   ├── image_data.py               # Image data extraction utilities
│   ├── tabular_answer.py           # Structured data handler
│   ├── lite_llm.py                 # Lightweight handler
│   └── README.md                   # LLM documentation
├── 📁 RAG/                         # Advanced retrieval system
│   ├── __init__.py
│   ├── advanced_rag_processor.py   # Main RAG orchestrator
│   ├── README.md                   # RAG documentation
│   ├── rag_embeddings/             # Embedding storage directory
│   │   ├── 1_metadata.json
│   │   └── 4_metadata.json
│   └── rag_modules/                # Modular RAG components
│       ├── __init__.py
│       ├── query_expansion.py      # Query decomposition
│       ├── embedding_manager.py    # Semantic embeddings
│       ├── search_manager.py       # Hybrid search engine
│       ├── reranking_manager.py    # Cross-encoder reranking
│       ├── context_manager.py      # Context assembly
│       └── answer_generator.py     # LLM answer generation
├── 📁 shared/                      # Shared utilities
│   ├── __init__.py
│   └── model_manager.py             # Ensures one embedding model instance is created
├── 📁 preprocessing/               # Document processing pipeline
│   ├── __init__.py
│   ├── preprocessing.py            # Main entry point and CLI
│   ├── README.md                   # Preprocessing documentation
│   └── preprocessing_modules/      # Specialized extractors
│       ├── __init__.py
│       ├── modular_preprocessor.py # Main orchestrator
│       ├── file_downloader.py      # Universal file downloading
│       ├── file_readers.py         # Generic file readers
│       ├── pdf_extractor.py        # Advanced PDF processing
│       ├── pdf_downloader.py       # PDF-specific downloading
│       ├── docx_extractor.py       # Word document handling
│       ├── pptx_extractor.py       # PowerPoint processing
│       ├── xlsx_extractor.py       # Excel with OCR support
│       ├── image_extractor.py      # Image and table extraction
│       ├── text_chunker.py         # Smart text chunking
│       ├── embedding_manager.py    # Batch embedding generation
│       ├── vector_storage.py       # LanceDB integration
│       └── metadata_manager.py     # Document metadata
├── 📁 prompt/                      # System prompts
│   └── prompt.py                   # Centralized prompt templates
├── 📁 logger/                      # Advanced logging system
│   ├── __init__.py
│   ├── logger.py                   # In-memory logging with analytics
│   ├── custom_logger.py            # Structured logging utilities
│   └── README.md                   # Logging documentation
├── 📁 exception/                   # Custom exceptions
│   ├── __init__.py
│   └── custom_exception.py         # Project-specific exceptions
├── 📁 static/                      # Frontend assets
│   ├── scripts.js                  # Main application JavaScript
│   └── styles.css                  # Application styles
├── 📁 templates/                   # HTML templates
│   ├── index.html                  # Main web interface
│   └── service-worker.js           # PWA service worker
├── 📄 app.py                       # Application entry point
├── 📄 main.py                      # Alternative entry point for HuggingFace Spaces
├── 📄 startup.sh                   # Production startup script
├── 📄 Dockerfile                   # Container configuration
├── 📄 requirements.txt             # Python dependencies
├── 📄 LICENSE                      # MIT License
└── 📄 README.md                    # This file
```

## 🎯 Core Features

### 🔧 Multi-Provider LLM Management

**Smart Rate Limit Handling**
- Automatic rotation between Groq, Gemini, and OpenAI
- 60-second cooldown management per provider
- Intelligent fallback with zero downtime
- Real-time provider health monitoring

**Multi-Instance Support**
- Up to 10 API keys per provider
- Custom model assignment per instance
- Priority-based routing (Groq → Gemini → OpenAI)
- Cost-effective free tier optimization

### 📋 Document Processing Pipeline

**Supported Formats**
| Format | Extensions | Special Features |
|--------|------------|-----------------|
| PDF | .pdf | CID font mapping, table extraction, parallel processing |
| Word | .docx | Text boxes, tables, gridSpan handling |
| PowerPoint | .pptx | OCR Space API for images, notes extraction |
| Excel | .xlsx | Cell processing, embedded image OCR |
| Images | .png, .jpg, .jpeg | Table detection, OCR text extraction |
| Text | .txt, .csv | Direct processing, structured data handling |
| URLs | http/https | Google Docs conversion, web scraping |

**Advanced Processing**
- **Smart Chunking**: Sentence-boundary aware with configurable overlap
- **OCR Integration**: OCR Space API and Tesseract support
- **Table Extraction**: Automatic detection and markdown formatting
- **Caching System**: Document-level caching to avoid reprocessing
- **Parallel Processing**: Multi-threaded operations for efficiency

### 🔍 Advanced RAG System

**Query Processing**
- **Query Expansion**: Automatic decomposition into focused sub-queries
- **Multi-aspect Analysis**: Process/document/contact identification
- **Budget Management**: Intelligent retrieval budget distribution

**Hybrid Search Engine**
- **Semantic Search**: Dense vector similarity (SentenceTransformers)
- **Keyword Search**: BM25 for exact term matching
- **Score Fusion**: Reciprocal Rank Fusion with weighted combination
- **Reranking**: Cross-encoder models for relevance refinement

**Context-Aware Generation**
- **Multi-perspective Context**: Equal representation from sub-queries
- **Enhanced Prompting**: Specialized prompts for policy documents
- **Centralized Prompt Management**: Organized prompt templates in dedicated module
- **Error Handling**: Graceful handling of edge cases

## 🌐 Production-Ready API

**REST Endpoints**
- `POST /hackrx/run` - Document processing and Q&A
- `GET /health` - System health monitoring  
- `POST /preprocess` - Batch document preprocessing (admin)
- `GET /logs` - Request logs export with filtering (admin)
- `GET /collections` - List processed documents (admin)
- `GET /` - Web interface for interactive document analysis
- `GET /service-worker.js` - PWA service worker

**Web Interface Features**
- **Progressive Web App**: Modern, responsive interface with offline capabilities
- **Document Viewer**: Integrated PDF/document viewer with highlighting
- **Interactive Chat**: Real-time question answering with document references
- **Session Management**: User sessions with document upload and management
- **Visual Feedback**: Answer highlighting and source referencing

**Security Features**
- Bearer token authentication for main endpoints
- Admin token for administrative functions
- Request validation using Pydantic models
- CORS and security headers configuration

### 📊 Comprehensive Monitoring

**Request Tracking**
- Unique request ID generation
- Pipeline stage timing breakdown
- Per-question performance metrics
- Success/failure tracking

**Performance Analytics**
- Real-time processing statistics
- Provider usage distribution
- Memory and resource monitoring
- Export capabilities with filtering

**Health Monitoring**
- System component status
- Provider availability tracking
- Database connection health
- Resource usage monitoring

### 🗄️ Database Architecture

**LanceDB Vector Storage**
- **High-Performance**: Apache Arrow-based columnar storage
- **Unified Collections**: Single table for multi-document retrieval
- **Advanced Filtering**: Document-based filtering for targeted search
- **Scalable**: Efficient storage and retrieval for large document collections

**SQLite User Management**
- **User Sessions**: Authentication and session management
- **Document Tracking**: User-document associations
- **Lightweight**: Embedded database for metadata storage
- **Portable**: Self-contained database files for easy deployment

## ⚙️ Quick Setup

### Prerequisites

- Python 3.10+
- Docker (optional)
- At least one LLM provider API key (Groq/Gemini/OpenAI)
- OCR Space API key (for PowerPoint images)

### 🚀 Local Development Setup

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd Multi-Doc-RAG
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
   **Key Dependencies:**
   - `lancedb` - High-performance vector database
   - `sentence-transformers` - Embedding models
   - `fastapi` - Modern web framework
   - `rank-bm25` - Keyword search
   - `langchain` - LLM framework integration

3. **Configure Environment**
   Create `.env` file with your API keys:
   ```bash
   # === LLM PROVIDERS ===
   # Groq (Primary provider - fastest)
   GROQ_API_KEY_1=your_first_groq_key
   DEFAULT_GROQ_MODEL=qwen/qwen3-32b
   
   # Gemini (Secondary provider)
   GEMINI_API_KEY_1=your_gemini_key
   DEFAULT_GEMINI_MODEL=gemini-2.0-flash
   
   # OpenAI (Backup provider)
   OPENAI_API_KEY_1=your_openai_key
   DEFAULT_OPENAI_MODEL=gpt-4o-mini

   #You can add more api keys just change the number


   # === Specialized Pipelines ===
   GROQ_API_KEY_TABULAR = "a groq api key" # Optional: If Groq key already exists in handler, but recomended 
   GEMINI_API_KEY_IMAGE = "a gemini api" # Optional: If Gemini key already exists in handler, but recomended 

   # === Query Expansion ===
   GROQ_API_KEY_LITE = "a groq api key" # Optional: If Groq key already exists in handler, but recomended 
   
   # === SERVICES ===
   OCR_SPACE_API_KEY=your_ocr_space_key
   BEARER_TOKEN=your_secure_api_token

4. **Run Application**
   ```bash
   python app.py
   ```
   
   **Access Points:**
   - API: `http://localhost:7860`
   - Web Interface: `http://localhost:7860`
   - Health Check: `http://localhost:7860/health`

### 🐳 Docker Deployment

1. **Build Image**
   ```bash
   docker build -t multi-doc-rag .
   ```

2. **Run Container**
   ```bash
   docker run -p 7860:7860 --env-file .env multi-doc-rag
   ```

### ☁️ HuggingFace Spaces Deployment

The application is optimized for HuggingFace Spaces:

1. Upload project files to your Space
2. Set environment variables in Space settings
3. The `startup.sh` script handles database initialization
4. Access via your Space URL

## 📖 Usage Examples

### Python Client

```python
import httpx
import asyncio

async def analyze_document():
    url = "http://localhost:7860/hackrx/run"
    headers = {"Authorization": "Bearer your_token"}
    
    data = {
        "documents": "https://example.com/policy.pdf",
        "questions": [
            "What is the claim submission process?",
            "What documents are required?",
            "Who should I contact for help?"
        ]
    }
    
    async with httpx.AsyncClient(timeout=600) as client:
        response = await client.post(url, json=data, headers=headers)
        result = response.json()
        
        print("📄 Document Analysis Results:")
        for i, answer in enumerate(result["answers"]):
            print(f"\nQ{i+1}: {data['questions'][i]}")
            print(f"A{i+1}: {answer}")
        
        # Performance metrics
        if "pipeline_timings" in result:
            timings = result["pipeline_timings"]
            print(f"\n⏱️ Processing Time: {timings.get('total_pipeline', 0):.2f}s")

asyncio.run(analyze_document())
```

### cURL Examples

```bash
# Process document with questions
curl -X POST "http://localhost:7860/hackrx/run" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": "https://example.com/policy.pdf",
    "questions": [
      "What are the key policy highlights?",
      "How do I submit a claim?"
    ]
  }'

# Check system health
curl -X GET "http://localhost:7860/health"

# Get request logs (admin)
curl -X GET "http://localhost:7860/logs?minutes=60&limit=50" \
  -H "Authorization: Bearer 9420689497"

# Preprocess document (admin)
curl -X POST "http://localhost:7860/preprocess" \
  -H "Authorization: Bearer 9420689497" \
  -d "document_url=https://example.com/document.pdf&force=false"
```

### 🌐 Web Interface Usage

The system includes a modern web interface accessible at the root URL:

**Features:**
- **Document Upload**: Drag-and-drop file upload with progress tracking
- **Interactive Chat**: Real-time question answering with typing indicators
- **Document Viewer**: Integrated PDF viewer with highlighting capabilities
- **Session Management**: User authentication and document organization
- **Progressive Web App**: Offline capabilities and mobile-friendly design

**Access the Interface:**
```bash
# Start the server
python app.py

# Open in browser
http://localhost:7860
```

**Web Interface Capabilities:**
- Upload documents (PDF, DOCX, PPTX, images)
- Ask questions and get highlighted answers
- View source references in the document
- Manage multiple document sessions
- Export conversation history

### CLI Usage

```bash
# Process single document
python -m preprocessing --url "https://example.com/document.pdf"

# Process multiple documents
python -m preprocessing --urls-file urls.txt

# List processed documents
python -m preprocessing --list

# Show statistics
python -m preprocessing --stats
```

## 🎛️ Configuration Guide

### Environment Variables

**Required Variables**
```bash
# At least one LLM provider
GROQ_API_KEY_1=your_key        # OR
GEMINI_API_KEY_1=your_key      # OR  
OPENAI_API_KEY_1=your_key

# Authentication
BEARER_TOKEN=your_secure_token

# OCR for PowerPoint processing
OCR_SPACE_API_KEY=your_ocr_key
```

**Optional Variables**
```bash
# Additional LLM keys (up to 10 per provider)
GROQ_API_KEY_2=backup_key
GEMINI_API_KEY_2=backup_key

# Custom models per provider
DEFAULT_GROQ_MODEL=qwen/qwen3-32b
GROQ_MODEL_1=llama3-70b-8192

# API configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false

# RAG configuration
TOP_K=9
CHUNK_SIZE=1600
ENABLE_RERANKING=true
```

### Processing Modes

The system automatically selects optimal processing modes:

**1. Advanced RAG Processing**
- Complex documents requiring full pipeline
- Vector database storage and hybrid search with LanceDB
- Best for policy documents, manuals

**2. OneShot Processing**
- Simple text documents
- Direct LLM processing without vector search
- Faster for short documents

**3. Tabular Analysis**
- Excel, CSV files with structured data
- Specialized data analysis prompts
- Optimized for numerical data

**4. Image Processing**
- Visual content with OCR
- Table detection in images
- Automatic cleanup after processing

## 📊 Performance Metrics

### Processing Speed
- **Simple Queries**: 1-2 seconds
- **Complex Multi-aspect**: 2-4 seconds
- **Document Preprocessing**: 2-5 pages/second (PDF)
- **Embedding Generation**: 100-500 chunks/second

### Cost Optimization
- **Free Tier Usage**: 200+ questions at $0 cost
- **Provider Rotation**: Automatic cost-effective routing  
- **Rate Limit Avoidance**: Prevents unnecessary paid calls
- **Intelligent Caching**: Reduces redundant processing

### Resource Usage
- **Memory**: 500MB-1GB (model dependent)
- **CPU**: Moderate during processing, minimal idle
- **Storage**: LanceDB tables stored locally with efficient columnar format
- **Disk I/O**: Optimized with Apache Arrow for fast data access

## 🛠️ Troubleshooting

### Common Issues

**1. No LLM Providers Available**
```python
# Check provider status
from LLM.llm_handler import llm_handler
status = llm_handler.get_provider_status()
print(f"Available providers: {len(status)}")

# Reset cooldowns if needed
llm_handler.reset_cooldowns()
```

**2. Document Processing Failures**
```bash
# Check document accessibility
curl -I "https://your-document-url.pdf"

# Force reprocessing
curl -X POST "http://localhost:7860/preprocess" \
  -H "Authorization: Bearer admin_token" \
  -d "document_url=your_url&force=true"
```

**3. LanceDB Connection Issues**
```python
# Check LanceDB database status
from pathlib import Path
import lancedb

db_path = Path("RAG/rag_embeddings/unified_documents.lance")
if db_path.exists():
    db = lancedb.connect(db_path)
    print(f"Tables: {db.table_names()}")
else:
    print("Database not found - run document preprocessing first")
```

**3. OCR Space API Issues**
```bash
# Verify OCR API key
export OCR_SPACE_API_KEY="your_key"

# Test OCR endpoint
curl -X POST "https://api.ocr.space/parse/image" \
  -F "apikey=your_key" \
  -F "url=https://example.com/image.jpg"
```

**4. Memory Issues**
```python
# Reduce batch sizes in config.py
BATCH_SIZE = 16
CHUNK_SIZE = 1200
```

### Debug Mode

Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Check system health
from api.api import app
# Health check includes detailed component status
```

### Health Monitoring

```bash
# System health check
curl http://localhost:8000/health

# Detailed logs export
curl -H "Authorization: Bearer admin_token" \
  "http://localhost:8000/logs?minutes=60" > debug_logs.json
```

## 🚀 Production Deployment

### Docker Production Setup

```dockerfile
# Multi-stage build for optimization
FROM python:3.10-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.10-slim
COPY --from=builder /root/.local /root/.local
COPY . /app
WORKDIR /app

# Environment setup
ENV PATH=/root/.local/bin:$PATH
ENV HF_HOME=/app/.cache/huggingface
EXPOSE 7860

CMD ["bash", "startup.sh"]
```

### Environment-Specific Configuration

**Development**
```bash
API_RELOAD=true
API_HOST=127.0.0.1
LOG_LEVEL=DEBUG
```

**Staging**
```bash
API_RELOAD=false
API_HOST=0.0.0.0
LOG_LEVEL=INFO
```

**Production**
```bash
API_RELOAD=false
API_HOST=0.0.0.0
LOG_LEVEL=WARNING
# Multiple API keys for redundancy
GROQ_API_KEY_1=prod_key_1
GROQ_API_KEY_2=prod_key_2
```

### Monitoring Setup

```bash
# Health check endpoint for load balancers
curl -f http://localhost:7860/health || exit 1

# Prometheus metrics (custom implementation)
curl http://localhost:7860/metrics

# Log aggregation
curl -H "Authorization: Bearer admin" \
  "http://localhost:7860/logs" | jq '.metadata'
```

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

### Development Setup
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Follow modular architecture patterns
4. Maintain async/await compatibility
5. Add comprehensive error handling
6. Include type hints and documentation

### Code Standards
- **Python**: Follow PEP 8 style guidelines
- **Documentation**: Update README for new features
- **Testing**: Add tests for new components
- **Error Handling**: Implement graceful error recovery

### Pull Request Process
1. Update documentation
2. Add tests for new functionality
3. Ensure all tests pass
4. Update CHANGELOG.md
5. Submit PR with detailed description

## 🔒 Security Considerations

### Authentication
- **Bearer Tokens**: Secure API access with rotation support
- **Admin Endpoints**: Separate authentication for sensitive operations
- **Input Validation**: Comprehensive request sanitization

### Data Security
- **No Persistent Storage**: Documents processed in memory only
- **Automatic Cleanup**: Temporary files removed after processing
- **Secure Headers**: CORS and security headers configured

### Rate Limiting
- **Request Throttling**: Built-in concurrency limits
- **Provider Management**: Smart rate limit handling
- **Graceful Degradation**: Continues operation during issues

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Copyright (c) 2025 Rahul Samedavar and Sambhaji Patil**

## 🙏 Acknowledgments

- **HuggingFace**: For model hosting and Spaces platform
- **LanceDB**: For high-performance vector database capabilities  
- **FastAPI**: For modern API framework
- **SentenceTransformers**: For embedding models
- **Community Contributors**: For feedback and improvements

---

<div align="center">

**ShastraDocs v2** - *Enterprise-grade RAG system for intelligent document analysis*

[🌟 Star on GitHub](https://github.com/Sambhaji-Patil/Multi-Doc-RAG) 

</div>