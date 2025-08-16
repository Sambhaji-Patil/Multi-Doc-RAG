from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Any, Optional
import tempfile
import os
import hashlib
import asyncio
import aiohttp
import time
from contextlib import asynccontextmanager

from RAG.advanced_rag_processor import AdvancedRAGProcessor
from preprocessing.preprocessing import DocumentPreprocessor
from logger.logger import rag_logger
from LLM.llm_handler import llm_handler
from config.config import *
import config.config as config

from LLM.tabular_answer import get_answer_for_tabluar
from LLM.image_answerer import get_answer_for_image
from LLM.one_shotter import get_oneshot_answer

# Initialize security
security = HTTPBearer()
admin_security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify the bearer token for main API."""
    if credentials.credentials != BEARER_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )
    return credentials.credentials

def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(admin_security)):
    """Verify the bearer token for admin endpoints."""
    if credentials.credentials != "9420689497":
        raise HTTPException(
            status_code=401,
            detail="Invalid admin authentication token"
        )
    return credentials.credentials

# Pydantic models for request/response
class ProcessDocumentRequest(BaseModel):
    documents: HttpUrl  # URL to the PDF document
    questions: List[str]  # List of questions to answer

class ProcessDocumentResponse(BaseModel):
    answers: List[str]

class HealthResponse(BaseModel):
    status: str
    message: str

class PreprocessingResponse(BaseModel):
    status: str
    message: str
    doc_id: str
    chunk_count: int

class LogsResponse(BaseModel):
    export_timestamp: str
    metadata: Dict[str, Any]
    logs: List[Dict[str, Any]]

class LogsSummaryResponse(BaseModel):
    summary: Dict[str, Any]

# Global instances
rag_processor: Optional[AdvancedRAGProcessor] = None
document_preprocessor: Optional[DocumentPreprocessor] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup the RAG processor."""
    global rag_processor, document_preprocessor
    
    # Startup
    print("🚀 Initializing Advanced RAG System...")
    rag_processor = AdvancedRAGProcessor()  # Use advanced processor for better accuracy
    document_preprocessor = DocumentPreprocessor()
    print("✅ Advanced RAG System initialized successfully")
    
    yield
    
    # Shutdown
    print("🔄 Shutting down RAG System...")
    if rag_processor:
        rag_processor.cleanup()
    print("✅ Cleanup completed")

# FastAPI app with lifespan management
app = FastAPI(
    title="Advanced RAG API",
    description="API for document processing and question answering using RAG",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        message="RAG API is running successfully"
    )

@app.post("/hackrx/run", response_model=ProcessDocumentResponse)
async def process_document(
    request: ProcessDocumentRequest, 
    token: str = Depends(verify_token)
):
    """
    Process a PDF document and answer questions about it.
    
    This endpoint implements an optimized flow:
    1. Check if the document is already processed (pre-computed embeddings)
    2. If yes, use existing embeddings for fast retrieval + generation
    3. If no, run full RAG pipeline (download + process + embed + store + answer)
    
    Args:
        request: Contains document URL and list of questions
        token: Bearer token for authentication
        
    Returns:
        ProcessDocumentResponse: List of answers corresponding to the questions
    """
    global rag_processor, document_preprocessor
    
    if not rag_processor or not document_preprocessor:
        raise HTTPException(
            status_code=503, 
            detail="RAG system not initialized"
        )
    
    # Start timing and logging
    start_time = time.time()
    document_url = str(request.documents)
    questions = request.questions
    answers = []
    status = "success"
    error_message = None
    doc_id = None
    was_preprocessed = False
    final_answers = []  # Initialize final_answers to prevent UnboundLocalError
    
    # Initialize enhanced logging
    request_id = rag_logger.generate_request_id()
    rag_logger.start_request_timing(request_id)
    
    try:
        print(f"📋 [{request_id}] Processing document: {document_url[:50]}...")
        print(f"🤔 [{request_id}] Number of questions: {len(questions)}")
        print(f"")
        print(f"📌 [{request_id}] PRIORITY 1: Checking stored embeddings database...")
        
        # Generate document ID
        doc_id = document_preprocessor.generate_doc_id(document_url)
        
        # Step 2: Check if document is already processed (stored embeddings)
        is_processed = document_preprocessor.is_document_processed(document_url)
        was_preprocessed = is_processed
        
        if is_processed:
            print(f"✅ [{request_id}] ✅ FOUND STORED EMBEDDINGS for {doc_id}")
            print(f"⚡ [{request_id}] Using fast path with pre-computed embeddings")
            # Fast path: Use existing embeddings
            doc_info = document_preprocessor.get_document_info(document_url)
            print(f"📊 [{request_id}] Using existing collection with {doc_info.get('chunk_count', 'N/A')} chunks")
        else:
            print(f"❌ [{request_id}] No stored embeddings found for {doc_id}")
            print(f"📌 [{request_id}] PRIORITY 2: Running full RAG pipeline (download + process + embed)...")
            # Full path: Download and process document
            resp = await document_preprocessor.process_document(document_url)
            if isinstance(resp, List):
                # Handle different return formats: [content, type] or [content, type, no_cleanup_flag]
                content, _type = resp[0], resp[1]
                if content == 'unsupported':
                    return ProcessDocumentResponse(answers=[f"File not supported: {_type}"])
                
                if _type  == "image":
                    try:
                        final_answers = get_answer_for_image(content, questions)
                        return ProcessDocumentResponse(answers=final_answers)
                    finally:
                        # Clean up the image file after processing
                        if os.path.exists(content):
                            os.unlink(content)
                            print(f"🗑️ Cleaned up image file: {content}")

                if _type == "tabular":
                    final_answers = get_answer_for_tabluar(content, questions)
                    return ProcessDocumentResponse(answers=final_answers)
                
                if _type == "oneshot":
                    # final_answers =  await get_oneshot_answer(content, questions)
                    tasks = [
                        get_oneshot_answer(content, questions[i:i + 3])
                        for i in range(0, len(questions), 3)
                    ]
                    
                    # Run all batches in parallel
                    results = await asyncio.gather(*tasks)
                    
                    # Flatten results
                    final_answers = [ans for batch in results for ans in batch]
                    return ProcessDocumentResponse(answers=final_answers)          
            else:
                doc_id = resp

            print(f"✅ [{request_id}] Document {doc_id} processed and stored")
        
        print(f"🚀 [{request_id}] Processing {len(questions)} questions in parallel...")
        
        async def answer_single_question(question: str, index: int) -> tuple[str, Dict[str, float]]:
            """Answer a single question with error handling and timing."""
            try:
                question_start = time.time()
                print(f"❓ [{request_id}] Q{index+1}: {question[:50]}...")
                
                answer, pipeline_timings = await rag_processor.answer_question(
                    question=question,
                    doc_id=doc_id,
                    logger=rag_logger,
                    request_id=request_id
                )
                
                question_time = time.time() - question_start
                
                # Log question timing
                rag_logger.log_question_timing(
                    request_id, index, question, answer, question_time, pipeline_timings
                )
                
                print(f"✅ [{request_id}] Q{index+1} completed in {question_time:.4f}s")
                return answer, pipeline_timings
            except Exception as e:
                print(f"❌ [{request_id}] Q{index+1} Error: {str(e)}")
                return f"I encountered an error while processing this question: {str(e)}", {}
        
        # Process questions in parallel with controlled concurrency
        s_count = 5
        semaphore = asyncio.Semaphore(s_count)  # Reduced concurrency for better logging visibility
        print(f"Semaphore count: {s_count}")
        
        async def bounded_answer(question: str, index: int) -> tuple[str, Dict[str, float]]:
            async with semaphore:
                return await answer_single_question(question, index)
        
        # Execute all questions concurrently
        tasks = [
            bounded_answer(question, i) 
            for i, question in enumerate(questions)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions in answers
        final_answers = []
        error_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_count += 1
                final_answers.append(f"Error processing question {i+1}: {str(result)}")
            else:
                answer, _ = result
                final_answers.append(answer)
        
        # Determine final status
        if error_count == 0:
            status = "success"
        elif error_count == len(questions):
            status = "error"
        else:
            status = "partial"
        
        print(f"✅ [{request_id}] Successfully processed {len(questions) - error_count}/{len(questions)} questions")
        
    except Exception as e:
        print(f"❌ [{request_id}] Error processing request: {str(e)}")
        status = "error"
        error_message = str(e)
        final_answers = [f"Error: {str(e)}" for _ in questions]
    
    finally:
        # End request timing and get detailed timing data
        timing_data = rag_logger.end_request_timing(request_id)
        
        # Log the request with enhanced timing
        processing_time = time.time() - start_time
        logged_request_id = rag_logger.log_request(
            document_url=document_url,
            questions=questions,
            answers=final_answers,
            processing_time=processing_time,
            status=status,
            error_message=error_message,
            document_id=doc_id,
            was_preprocessed=was_preprocessed,
            timing_data=timing_data
        )
        
        print(f"📊 Request logged with ID: {logged_request_id} (Status: {status}, Time: {processing_time:.2f}s)")
        
        if status == "error":
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process document: {error_message}"
            )
    
    return ProcessDocumentResponse(answers=final_answers)

@app.post("/preprocess", response_model=PreprocessingResponse)
async def preprocess_document(document_url: str, force: bool = False, token: str = Depends(verify_admin_token)):
    """
    Preprocess a document (for batch preprocessing).
    
    Args:
        document_url: URL of the PDF to preprocess
        force: Whether to reprocess if already processed
        
    Returns:
        PreprocessingResponse: Status and document info
    """
    global document_preprocessor
    
    if not document_preprocessor:
        raise HTTPException(
            status_code=503,
            detail="Document preprocessor not initialized"
        )
    
    try:
        doc_id = await document_preprocessor.process_document(document_url, force)
        doc_info = document_preprocessor.get_document_info(document_url)
        
        return PreprocessingResponse(
            status="success",
            message=f"Document processed successfully",
            doc_id=doc_id,
            chunk_count=doc_info.get("chunk_count", 0)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to preprocess document: {str(e)}"
        )

@app.get("/collections")
async def list_collections(token: str = Depends(verify_admin_token)):
    """List all available document collections."""
    global document_preprocessor
    
    if not document_preprocessor:
        raise HTTPException(
            status_code=503,
            detail="Document preprocessor not initialized"
        )
    
    try:
        processed_docs = document_preprocessor.list_processed_documents()
        return {"collections": processed_docs}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list collections: {str(e)}"
        )

@app.get("/collections/stats")
async def get_collection_stats(token: str = Depends(verify_admin_token)):
    """Get statistics about all collections."""
    global document_preprocessor
    
    if not document_preprocessor:
        raise HTTPException(
            status_code=503,
            detail="Document preprocessor not initialized"
        )
    
    try:
        stats = document_preprocessor.get_collection_stats()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get collection stats: {str(e)}"
        )
    
# Logging Endpoints
@app.get("/logs", response_model=LogsResponse)
async def get_logs(
    token: str = Depends(verify_admin_token),
    limit: Optional[int] = Query(None, description="Maximum number of logs to return"),
    minutes: Optional[int] = Query(None, description="Get logs from last N minutes"),
    document_url: Optional[str] = Query(None, description="Filter logs by document URL")
):
    """
    Export all API request logs as JSON.
    
    Query Parameters:
        limit: Maximum number of recent logs to return
        minutes: Get logs from the last N minutes
        document_url: Filter logs for a specific document URL
    
    Returns:
        LogsResponse: Complete logs export with metadata
    """
    try:
        if document_url:
            # Get logs for specific document
            logs = rag_logger.get_logs_by_document(document_url)
            metadata = {
                "filtered_by": "document_url",
                "document_url": document_url,
                "total_logs": len(logs)
            }
            return LogsResponse(
                export_timestamp=rag_logger.export_logs()["export_timestamp"],
                metadata=metadata,
                logs=logs
            )
        
        elif minutes:
            # Get recent logs
            logs = rag_logger.get_recent_logs(minutes)
            metadata = {
                "filtered_by": "time_range",
                "minutes": minutes,
                "total_logs": len(logs)
            }
            return LogsResponse(
                export_timestamp=rag_logger.export_logs()["export_timestamp"],
                metadata=metadata,
                logs=logs
            )
        
        else:
            # Get all logs (with optional limit)
            if limit:
                logs = rag_logger.get_logs(limit)
                metadata = rag_logger.get_logs_summary()
                metadata["limited_to"] = limit
            else:
                logs_export = rag_logger.export_logs()
                return LogsResponse(**logs_export)
            
            return LogsResponse(
                export_timestamp=rag_logger.export_logs()["export_timestamp"],
                metadata=metadata,
                logs=logs
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export logs: {str(e)}"
        )

@app.get("/logs/summary", response_model=LogsSummaryResponse)
async def get_logs_summary(token: str = Depends(verify_admin_token)):
    """
    Get summary statistics of all logs.
    
    Returns:
        LogsSummaryResponse: Summary statistics
    """
    try:
        summary = rag_logger.get_logs_summary()
        return LogsSummaryResponse(summary=summary)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get logs summary: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    
    # Run the FastAPI server
    uvicorn.run(
        "api:app",
        host=API_HOST,
        port=API_PORT,
        reload=API_RELOAD,
        log_level="info"
    )
