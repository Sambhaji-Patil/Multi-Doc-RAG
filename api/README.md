# ShastraDocs API Package

A production-ready FastAPI REST API for the ShastraDocs document analysis system. This package provides secure, authenticated endpoints for document processing, question answering, and system management with comprehensive logging and monitoring.

## 🚀 Overview

The API package serves as the main interface for the ShastraDocs RAG system, offering:
- **Document Processing**: Upload and analyze documents in 8+ formats
- **Question Answering**: Intelligent responses using advanced RAG techniques
- **System Management**: Admin endpoints for monitoring and maintenance
- **Enhanced Logging**: Detailed request tracking and performance analytics

## 📦 Package Structure

```
api/
├── __init__.py          # Package initialization
└── api.py              # Main FastAPI application with all endpoints
```

## 🎯 Core Features

### 🔐 Security & Authentication
- **Bearer Token Authentication**: Secure API access with configurable tokens
- **Admin Endpoints**: Separate authentication for administrative functions
- **Request Validation**: Comprehensive input validation using Pydantic models

### ⚡ Intelligent Document Processing
- **Optimized Flow**: Checks for pre-processed documents to avoid redundant work
- **Multi-Format Support**: Handles PDFs, Word docs, presentations, spreadsheets, images
- **Parallel Processing**: Concurrent question answering with configurable limits
- **Fallback Handling**: Graceful degradation for unsupported formats

### 📊 Advanced Processing Modes
- **Standard RAG**: Full pipeline for complex documents
- **OneShot Processing**: Fast processing for simple text documents
- **Tabular Analysis**: Specialized handling for structured data
- **Image Analysis**: OCR and visual question answering

### 🔍 Monitoring & Observability
- **Real-time Logging**: Detailed request tracking with unique IDs
- **Performance Metrics**: Pipeline timing breakdown and statistics
- **Health Monitoring**: System status and component health checks
- **Export Capabilities**: JSON log export with filtering options

## 📋 API Endpoints

### Core Processing Endpoints

#### `POST /hackrx/run` - Document Processing & QA
Process documents and answer questions using the advanced RAG pipeline.

**Request:**
```json
{
  "documents": "https://example.com/policy.pdf",
  "questions": [
    "What is the claim submission process?",
    "What documents are required?",
    "Who should I contact for help?"
  ]
}
```

**Response:**
```json
{
  "answers": [
    "The claim submission process involves three main steps...",
    "Required documents include: policy certificate, claim form...",
    "For assistance, contact the customer service team at..."
  ]
}
```

**Features:**
- ✅ **Smart Caching**: Reuses pre-processed embeddings
- ⚡ **Parallel Processing**: Handles multiple questions concurrently
- 🔄 **Automatic Fallback**: Switches between processing modes based on document type
- 📊 **Detailed Timing**: Returns comprehensive performance metrics

#### `GET /health` - Health Check
Simple health check endpoint for monitoring system status.

**Response:**
```json
{
  "status": "healthy",
  "message": "RAG API is running successfully"
}
```

### Administrative Endpoints (Admin Token Required)

#### `POST /preprocess` - Batch Document Preprocessing
Pre-process documents for faster future queries.

**Parameters:**
- `document_url`: URL of document to preprocess
- `force`: Boolean to force reprocessing

#### `GET /collections` - List Processed Documents
Retrieve information about all processed document collections.

#### `GET /collections/stats` - Collection Statistics
Get comprehensive statistics about the document database.

### Logging & Monitoring Endpoints (Admin Token Required)

#### `GET /logs` - Export Request Logs
Export detailed API request logs with optional filtering.

**Query Parameters:**
- `limit`: Maximum number of logs to return
- `minutes`: Get logs from last N minutes
- `document_url`: Filter by specific document URL

**Response:**
```json
{
  "export_timestamp": "2024-01-15T10:30:00Z",
  "metadata": {
    "total_requests": 156,
    "successful_requests": 152,
    "success_rate": 97.44,
    "average_processing_time": 2.34
  },
  "logs": [...]
}
```

#### `GET /logs/summary` - Logs Summary
Get aggregated statistics and performance metrics.

## 🔧 Configuration

### Environment Variables

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=True

# Authentication
BEARER_TOKEN=your_secure_api_token

# LLM Provider Keys (auto-detects multiple keys)
GROQ_API_KEY_1=your_groq_key_1
GROQ_API_KEY_2=your_groq_key_2
GEMINI_API_KEY_1=your_gemini_key_1

# OCR Service
OCR_SPACE_API_KEY=your_ocr_space_key
```

### Key Settings

```python
# Processing Configuration
SEMAPHORE_COUNT = 5          # Concurrent question processing limit
TIMEOUT_SECONDS = 600        # Request timeout for large documents
MAX_RETRIES = 3             # Automatic retry attempts

# Authentication
ADMIN_TOKEN = "9420689497"   # Default admin token (change in production)
BEARER_TOKEN = "your_token"  # Main API bearer token
```

## 🚀 Usage Examples

### Python Client

```python
import httpx
import asyncio

async def process_document():
    url = "http://localhost:8000/hackrx/run"
    headers = {"Authorization": "Bearer your_token"}
    
    data = {
        "documents": "https://example.com/policy.pdf",
        "questions": [
            "What is the main policy coverage?",
            "How do I file a claim?"
        ]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        result = response.json()
        
        for i, answer in enumerate(result["answers"]):
            print(f"Q{i+1}: {data['questions'][i]}")
            print(f"A{i+1}: {answer}\n")

asyncio.run(process_document())
```

### cURL Examples

```bash
# Process document with questions
curl -X POST "http://localhost:8000/hackrx/run" \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": "https://example.com/document.pdf",
    "questions": ["What is this document about?"]
  }'

# Check system health
curl -X GET "http://localhost:8000/health"

# Get recent logs (admin)
curl -X GET "http://localhost:8000/logs?minutes=60" \
  -H "Authorization: Bearer 9420689497"

# Preprocess document (admin)
curl -X POST "http://localhost:8000/preprocess" \
  -H "Authorization: Bearer 9420689497" \
  -d "document_url=https://example.com/policy.pdf&force=false"
```

## 🎯 Processing Modes

### 1. Standard RAG Processing
For complex documents requiring full pipeline processing:
- Downloads and processes document
- Creates embeddings and stores in vector database
- Uses hybrid search with reranking
- Returns detailed answers with citations

### 2. OneShot Processing
For simple text documents or when context is sufficient:
- Processes small documents directly
- Uses LLM without vector search
- Faster response times
- Suitable for short documents or summaries

### 3. Tabular Data Processing
For structured data like spreadsheets and CSV files:
- Specialized tabular analysis
- Handles data relationships and calculations
- Optimized for numerical and categorical data
- Batch processing for efficiency

### 4. Image Processing
For visual content analysis:
- OCR text extraction
- Table detection in images
- Visual question answering
- Automatic cleanup of processed images

## 📊 Performance Monitoring

### Request Lifecycle Tracking
Each request is tracked with comprehensive metrics:

```json
{
  "request_id": "req_000123",
  "processing_time_seconds": 2.45,
  "pipeline_timings": {
    "query_expansion": 0.156,
    "hybrid_search": 0.423,
    "reranking": 0.089,
    "context_creation": 0.012,
    "llm_generation": 1.245
  },
  "question_timings": [
    {
      "question_index": 0,
      "total_time_seconds": 1.234,
      "pipeline_breakdown": {...}
    }
  ]
}
```

### System Health Metrics
- **Success Rate**: Percentage of successful requests
- **Average Response Time**: Mean processing time across requests
- **Provider Status**: Health of LLM providers
- **Resource Usage**: Memory and processing statistics

## 🛠️ Development

### Running the API

```bash
# Development mode with auto-reload
python api/api.py

# Production mode with uvicorn
uvicorn api.api:app --host 0.0.0.0 --port 8000

# With specific workers (for production)
uvicorn api.api:app --host 0.0.0.0 --port 8000 --workers 4
```

### Testing

```python
import pytest
from fastapi.testclient import TestClient
from api.api import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_process_document():
    headers = {"Authorization": "Bearer your_test_token"}
    data = {
        "documents": "https://example.com/test.pdf",
        "questions": ["What is this about?"]
    }
    
    response = client.post("/hackrx/run", json=data, headers=headers)
    assert response.status_code == 200
    assert "answers" in response.json()
```

### Custom Error Handling

The API includes comprehensive error handling:

```python
# Example error responses
{
  "status_code": 401,
  "detail": "Invalid authentication token"
}

{
  "status_code": 500,
  "detail": "Failed to process document: Unsupported file format"
}

{
  "status_code": 503,
  "detail": "RAG system not initialized"
}
```

## 🔒 Security Considerations

### Authentication
- **Bearer Token**: All main endpoints require valid bearer token
- **Admin Token**: Administrative functions use separate token
- **Token Validation**: Server-side token verification

### Data Security
- **No Persistent Storage**: Documents processed in memory only
- **Automatic Cleanup**: Temporary files removed after processing
- **Secure Headers**: CORS and security headers configured

### Rate Limiting
- **Request Throttling**: Built-in concurrency limits
- **Provider Management**: Smart rate limit handling for LLM APIs
- **Graceful Degradation**: Continues operation during provider issues

## 🚀 Deployment

### HuggingFace Spaces
The API is optimized for HuggingFace Spaces deployment:

```python
# app.py - HuggingFace Spaces entry point
from api.api import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "api.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment-Specific Configuration

```bash
# Development
export API_RELOAD=true
export API_HOST=127.0.0.1

# Production
export API_RELOAD=false
export API_HOST=0.0.0.0
export API_PORT=8000
```

## 📞 Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify bearer token configuration
   - Check token format in Authorization header
   - Ensure admin token for admin endpoints

2. **Processing Failures**
   - Check document URL accessibility
   - Verify file format compatibility
   - Review error logs for specific issues

3. **Performance Issues**
   - Monitor semaphore count for concurrency
   - Check LLM provider status
   - Review timeout configurations

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable detailed logging for troubleshooting
```

---

**ShastraDocs API Package** - Production-ready REST API for advanced document analysis and question answering.

*Built with FastAPI, featuring comprehensive authentication, monitoring, and error handling for enterprise deployment.*