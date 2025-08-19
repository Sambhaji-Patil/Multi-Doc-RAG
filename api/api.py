from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Any, Optional, Union
import tempfile
import os
import hashlib
import asyncio
import aiohttp
import time
from contextlib import asynccontextmanager

# ## MODIFIED: Ensure the correct preprocessor is imported
from preprocessing.preprocessing import ModularDocumentPreprocessor as DocumentPreprocessor
from RAG.advanced_rag_processor import AdvancedRAGProcessor
from logger.logger import rag_logger
from LLM.llm_handler import llm_handler
from LLM.image_data import extract_data_from_image
from config.config import *
import config.config as config

from LLM.tabular_answer import get_answer_for_tabluar
from LLM.image_answerer import get_answer_for_image
from LLM.one_shotter import get_oneshot_answer
from logger.custom_logger import CustomLogger

# Initialize security
security = HTTPBearer()
admin_security = HTTPBearer()
logger = CustomLogger().get_logger(__file__)

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
    if credentials.credentials != ADMIN_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin authentication token"
        )
    return credentials.credentials

# Pydantic models for request/response
class ProcessDocumentRequest(BaseModel):
    documents: Union[str, List[str]]
    questions: List[str]

class DocumentQuestionPair(BaseModel):
    document_url: HttpUrl
    questions: List[str]

class ProcessMultipleDocumentsRequest(BaseModel):
    document_question_pairs: List[DocumentQuestionPair]

class DocumentInfo(BaseModel):
    document_url: str
    doc_id: str
    chunk_count: int
    content: Optional[Any] = None  # Can hold text, file paths, or structured data
    status: str  # "processed", "cached", "error", "image", "tabular", "oneshot"
    processing_time: Optional[float] = None
    error_message: Optional[str] = None

class ProcessDocumentResponse(BaseModel):
    answers: List[str]

class DocumentAnswerResult(BaseModel):
    document_url: str
    doc_id: str
    answers: List[str]
    processing_time: float
    status: str
    error_message: Optional[str] = None

class ProcessMultipleDocumentsResponse(BaseModel):
    results: List[DocumentAnswerResult]
    total_processing_time: float
    successful_documents: int
    failed_documents: int

class HealthResponse(BaseModel):
    status: str
    message: str

class PreprocessingResponse(BaseModel):
    status: str
    message: str
    doc_id: str
    doc_type: str
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
    global rag_processor, document_preprocessor
    logger.info("Initializing Advanced RAG System")
    rag_processor = AdvancedRAGProcessor()
    document_preprocessor = DocumentPreprocessor()
    logger.info("Advanced RAG System initialized successfully")
    print("🟢 Advanced RAG System initialized successfully")
    yield
    logger.info("Shutting down RAG System")
    if rag_processor:
        rag_processor.cleanup()
    logger.info("Cleanup completed")
    print("🟢 Cleanup completed")

app = FastAPI(
    title="Advanced RAG API",
    description="API for document processing and question answering using RAG",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="healthy", message="RAG API is running successfully")

@app.post("/hackrx/run", response_model=ProcessDocumentResponse)
async def process_document(
    request: ProcessDocumentRequest, 
    token: str = Depends(verify_token)
):
    global rag_processor, document_preprocessor
    if not rag_processor or not document_preprocessor:
        raise HTTPException(status_code=503, detail="RAG system not initialized")

    start_time = time.time()
    document_urls = [str(request.documents)] if isinstance(request.documents, (str, HttpUrl)) else [str(url) for url in request.documents]
    questions = request.questions
    is_multi_document = len(document_urls) > 1
    
    request_id = rag_logger.generate_request_id()
    rag_logger.start_request_timing(request_id)
    
    documents_info = []
    processed_doc_ids = []
    successful_docs = 0
    failed_docs = 0
    final_answers = []
    
    try:
        logger.info("Processing documents", request_id=request_id, count=len(document_urls))
        print(f"🟢 Processing Documents: Req.Id: {request_id} Count: {len(document_urls)}")

        async def process_single_document(doc_url: str, index: int) -> tuple[str, DocumentInfo]:
            doc_start_time = time.time()
            doc_id = document_preprocessor.generate_doc_id(doc_url)
            
            try:
                if document_preprocessor.is_document_processed(doc_url):
                    logger.info("Using cached document", request_id=request_id, doc_index=index+1, doc_id=doc_id)
                    print("🟢 Using cached Document")
                    doc_info_data = document_preprocessor.get_document_info(doc_url)
                    processing_time = time.time() - doc_start_time
                    return doc_id, DocumentInfo(
                        document_url=doc_url,
                        doc_id=doc_id,
                        chunk_count=doc_info_data.get('chunk_count', 0),
                        status="cached",
                        processing_time=processing_time
                    )
                logger.info("Processing new document", request_id=request_id, doc_index=index+1, doc_id=doc_id)
                print(f"🟢 Processing new document: Doc.Id:{doc_id} ")
                
                ## MODIFIED: Unpack the (doc_id, doc_type) tuple from the preprocessor
                processed_doc_id, doc_type = await document_preprocessor.process_document(doc_url, skip_length_check=is_multi_document)
                
                processing_time = time.time() - doc_start_time

                doc_info_data = document_preprocessor.get_document_info(doc_url)
                
                # ## MODIFIED: Handle special types by fetching their content from the cache
                content = None
                if doc_type in ["image", "tabular", "oneshot"]:
                    content = document_preprocessor.get_special_document_details(processed_doc_id)
                logger.info("Document processed", request_id=request_id, doc_index=index+1, doc_id=processed_doc_id, doc_type=doc_type, chunks=doc_info_data.get('chunk_count', 0))
                return processed_doc_id, DocumentInfo(
                    document_url=doc_url,
                    doc_id=processed_doc_id,
                    chunk_count=doc_info_data.get('chunk_count', 0),
                    status=doc_type, # Use the type directly as status
                    processing_time=processing_time,
                    content=content
                )
                        
            except Exception as e:
                processing_time = time.time() - doc_start_time
                error_msg = str(e)
                logger.error("Failed to process document", request_id=request_id, doc_index=index+1, document_url=doc_url, error=error_msg)
                return None, DocumentInfo(
                    document_url=doc_url,
                    doc_id=doc_id,
                    chunk_count=0,
                    status="error",
                    processing_time=processing_time,
                    error_message=error_msg
                )

        doc_semaphore = asyncio.Semaphore(3)
        async def bounded_doc_process(doc_url: str, index: int):
            async with doc_semaphore:
                return await process_single_document(doc_url, index)
        
        doc_tasks = [bounded_doc_process(url, i) for i, url in enumerate(document_urls)]
        doc_results = await asyncio.gather(*doc_tasks, return_exceptions=True)

        if not doc_results:
            return ProcessDocumentResponse(answers=[f"No Files Found"]*len(questions))

        if len(doc_results) == 1 and not isinstance(doc_results[0], Exception):
            doc_id, doc_info = doc_results[0]

            if doc_info.status == "error":
                return ProcessDocumentResponse(answers=[doc_id]*len(questions))

            if doc_info.status in ["image", "tabular", "oneshot"]:
                logger.info("Handling single special document", request_id=request_id, doc_type=doc_info.status)
                print(f"🟢 Handling single special document {doc_info.status} ")
                try:
                    if doc_info.status == "image":
                        final_answers = get_answer_for_image(doc_info.content, questions)
                    elif doc_info.status == "tabular":
                        context = "\n---\n".join([f"doc id: {doc_id}, page number: {d['page_num']}\n{d['content']}" for d in doc_info.content])
                        final_answers = get_answer_for_tabluar(doc_info.content, questions)
                    elif doc_info.status == "oneshot":
                        context = "\n---\n".join(doc_info.content)
                        tasks = [get_oneshot_answer(context, questions[i:i + 3]) for i in range(0, len(questions), 3)]
                        results = await asyncio.gather(*tasks)
                        final_answers = [ans for batch in results for ans in batch]
                    
                    return ProcessDocumentResponse(
                        answers=final_answers
                    )
                except Exception as e:
                    raise e.with_traceback
                finally:
                    if doc_info.status == "image" and doc_info.content and os.path.exists(doc_info.content):
                        os.unlink(doc_info.content)
                        logger.info("Cleaned up image file", path=doc_info.content)
        
        special_chunks_for_rag = []
        for i, result in enumerate(doc_results):
            if isinstance(result, Exception):
                failed_docs += 1
                documents_info.append(DocumentInfo(document_url=document_urls[i], doc_id=f"exception_{i}", chunk_count=0, status="error", error_message=str(result)))
            else:
                doc_id, doc_info = result
                documents_info.append(doc_info)
                
                if doc_info.status == "error":
                    failed_docs += 1
                elif doc_info.status == "normal" or doc_info.status == "cached":
                    if doc_id: processed_doc_ids.append(doc_id)
                    successful_docs += 1
                else: # Handle special types for cross-search
                    successful_docs += 1
                    if doc_info.content:
                        try:
                            if doc_info.status == "image":
                                content = extract_data_from_image(doc_info.content, doc_id=doc_id)
                                special_chunks_for_rag.append(f"--- doc_id: {doc_id}, page number:{1}\n{content}")
                                if os.path.exists(doc_info.content): os.unlink(doc_info.content)
                            elif doc_info.status == "oneshot":
                                special_chunks_for_rag.extend(doc_info.content)
                            elif doc_info.status == "tabular":
                                special_chunks_for_rag.extend([f"doc id: {doc_id}, page number: {d['page_num']}\n{d['content']}" for d in doc_info.content])
                            else:
                                special_chunks_for_rag.append(str(doc_info.content))
                        except Exception as e:
                            logger.error("Error processing special document", doc_type=doc_info.status, error=str(e))
                            special_chunks_for_rag.append(f"Error processing {doc_info.status} document: {str(e)}")
        
        logger.info("Document processing complete", request_id=request_id, regular=len(processed_doc_ids), special=len(special_chunks_for_rag), failed=failed_docs)
        print("🟢 Document Processing completed")
        
        if processed_doc_ids or special_chunks_for_rag:
            logger.info("Processing questions", request_id=request_id, count=len(questions))
            print("🟢 Processing Questions...")
            
            async def answer_single_question(question: str, index: int):
                question_start = time.time()
                logger.info("Processing question", request_id=request_id, q_index=index+1, preview=question[:50])
                answer, pipeline_timings = await rag_processor.answer_question(
                    question=question, doc_ids=processed_doc_ids, logger=rag_logger, request_id=request_id, extra_chunks=special_chunks_for_rag
                )
                question_time = time.time() - question_start
                rag_logger.log_question_timing(request_id, index, question, answer, question_time, pipeline_timings)
                logger.info("Question completed", request_id=request_id, q_index=index+1, duration_sec=round(question_time, 4))
                return answer, pipeline_timings
            
            semaphore = asyncio.Semaphore(5)
            async def bounded_answer(question: str, index: int):
                async with semaphore: return await answer_single_question(question, index)
            
            tasks = [bounded_answer(q, i) for i, q in enumerate(questions)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            rag_answers = [f"Error processing question {i+1}: {str(res)}" if isinstance(res, Exception) else res[0] for i, res in enumerate(results)]
            final_answers = rag_answers
    
    except Exception as e:
        logger.error("Error processing request", request_id=request_id, error=str(e))
        print("🔴 Error processing request!!")
        if not final_answers: final_answers = [f"Error: {str(e)}" for _ in questions]
        raise
    
    finally:
        timing_data = rag_logger.end_request_timing(request_id)
        processing_time = time.time() - start_time
    rag_logger.log_request(
            document_url=document_urls[0] if len(document_urls) == 1 else f"multi_doc_{len(document_urls)}",
            questions=questions, answers=final_answers, processing_time=processing_time, status="success", error_message=None,
            document_id=processed_doc_ids[0] if len(processed_doc_ids) == 1 else f"multi_{len(processed_doc_ids)}",
            was_preprocessed=any(doc.status == "cached" for doc in documents_info), timing_data=timing_data
        )
    logger.info("Request logged", request_id=request_id, duration_sec=round(processing_time, 2))
    
    return ProcessDocumentResponse(answers=final_answers)

@app.post("/preprocess", response_model=PreprocessingResponse)
async def preprocess_document(document_url: str, force: bool = False, token: str = Depends(verify_admin_token)):
    global document_preprocessor
    if not document_preprocessor:
        raise HTTPException(status_code=503, detail="Document preprocessor not initialized")
    
    try:
        # ## MODIFIED: Unpack tuple and adapt response
        doc_id, doc_type = await document_preprocessor.process_document(document_url, force)
        if doc_type == "error":
            raise HTTPException(status_code=500, detail="Preprocessing failed for an unknown reason.")

        doc_info = document_preprocessor.get_document_info(document_url)
        
        return PreprocessingResponse(
            status="success",
            message=f"Document processed successfully as type '{doc_type}'",
            doc_id=doc_id,
            doc_type=doc_type,
            chunk_count=doc_info.get("chunk_count", 0)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to preprocess document: {str(e)}")


@app.get("/collections")
async def list_collections(token: str = Depends(verify_admin_token)):
    global document_preprocessor
    if not document_preprocessor:
        raise HTTPException(status_code=503, detail="Document preprocessor not initialized")
    try:
        return {"collections": document_preprocessor.list_processed_documents()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list collections: {str(e)}")

@app.get("/collections/stats")
async def get_collection_stats(token: str = Depends(verify_admin_token)):
    global document_preprocessor
    if not document_preprocessor:
        raise HTTPException(status_code=503, detail="Document preprocessor not initialized")
    try:
        return document_preprocessor.get_collection_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get collection stats: {str(e)}")
    
@app.get("/logs", response_model=LogsResponse)
async def get_logs(token: str = Depends(verify_admin_token), limit: Optional[int] = Query(None), minutes: Optional[int] = Query(None), document_url: Optional[str] = Query(None)):
    try:
        if document_url:
            logs = rag_logger.get_logs_by_document(document_url)
            metadata = {"filtered_by": "document_url", "document_url": document_url, "total_logs": len(logs)}
            return LogsResponse(export_timestamp=rag_logger.export_logs()["export_timestamp"], metadata=metadata, logs=logs)
        elif minutes:
            logs = rag_logger.get_recent_logs(minutes)
            metadata = {"filtered_by": "time_range", "minutes": minutes, "total_logs": len(logs)}
            return LogsResponse(export_timestamp=rag_logger.export_logs()["export_timestamp"], metadata=metadata, logs=logs)
        else:
            if limit:
                logs = rag_logger.get_logs(limit)
                metadata = rag_logger.get_logs_summary()
                metadata["limited_to"] = limit
                return LogsResponse(export_timestamp=rag_logger.export_logs()["export_timestamp"], metadata=metadata, logs=logs)
            else:
                return LogsResponse(**rag_logger.export_logs())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export logs: {str(e)}")

@app.get("/logs/summary", response_model=LogsSummaryResponse)
async def get_logs_summary(token: str = Depends(verify_admin_token)):
    try:
        return LogsSummaryResponse(summary=rag_logger.get_logs_summary())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logs summary: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host=API_HOST, port=API_PORT, reload=API_RELOAD, log_level="info")