from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


from fastapi import FastAPI, UploadFile, Form, Depends
from pydantic import BaseModel
from typing import List, Optional

import uuid, sqlite3, os, shutil, datetime, json
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import requests

import random
from urllib.parse import urlparse

from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Any, Optional, Union
import tempfile
import re
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

from LLM.tabular_answer import get_answer_for_tabular
from LLM.image_answerer import get_answer_for_image
from LLM.one_shotter import get_oneshot_answer
from logger.custom_logger import CustomLogger

import sqlite3


# Initialize security
security = HTTPBearer()
admin_security = HTTPBearer()
logger = CustomLogger().get_logger(__file__)

DB_NAME = "database.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT,
            user_id TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT,
            docs TEXT,
            name TEXT,
            last_updated TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            path TEXT,
            mime_type TEXT
        )
    """)
    # FIXED: Quoted the "references" column name to avoid SQL keyword conflict
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id TEXT PRIMARY KEY,
            session_id TEXT,
            sender TEXT,
            content TEXT,
            "references" TEXT,
            timestamp TEXT
        )
    """)
    
    # FIXED: Ensure the alter table command also uses quoted "references"
    try:
        cursor.execute("PRAGMA table_info(messages)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'references' not in columns:
            cursor.execute('ALTER TABLE messages ADD COLUMN "references" TEXT')
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

def get_db():
    return sqlite3.connect(DB_NAME)

init_db()


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

class SignupRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class QueryRequest(BaseModel):
    session_id: str
    question: str

class CloneRequest(BaseModel):
    session_id: str


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

origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:5500",
    "http://localhost:3000",
    "*",
    "null"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


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
                        final_answers = get_answer_for_tabular(doc_info.content, questions)
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


tabular_data_cache = {}

# UI Endpoints
@app.get("/")
async def main_page():
    return FileResponse("templates/index.html")

@app.get("/service-worker.js")
async def sw():
    return FileResponse("templates/service-worker.js")

@app.get("/hello")
def hello():
    return {'message': 'hello'}

@app.post("/signup")
def signup(req: SignupRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email=?", (req.email,))
    if cursor.fetchone():
        return {"error": "User already exists"}
    user_id = str(uuid.uuid4())
    cursor.execute("INSERT INTO users (email, password, user_id) VALUES (?, ?, ?)",
                   (req.email, req.password, user_id))
    conn.commit()
    conn.close()
    return {"message": "User created", "user_id": user_id}

@app.post("/login")
def login(req: LoginRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, password FROM users WHERE email=?", (req.email,))
    row = cursor.fetchone()
    conn.close()
    if not row or row[1] != req.password:
        return {"error": "Invalid credentials"}
    return {"message": "Login successful", "user_id": row[0]}

@app.get("/my_sessions/{user_id}")
def my_sessions(user_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT session_id, docs, name, last_updated FROM sessions WHERE user_id=? ORDER BY last_updated DESC", (user_id,))
    sessions = [{
        "session_id": row[0],
        "docs": [doc_id for doc_id in row[1].split(',') if doc_id] if row[1] else [],
        "name": row[2],
        "last_updated": row[3]
    } for row in cursor.fetchall()]
    conn.close()
    return {"sessions": sessions}

# FIXED: Quoted "references" in the SELECT statement
@app.get("/messages/{session_id}")
def get_messages(session_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT sender, content, "references" FROM messages WHERE session_id=? ORDER BY timestamp ASC', (session_id,))
    messages = []
    for row in cursor.fetchall():
        references_data = []
        if row[2]:
            try:
                references_data = json.loads(row[2])
            except (json.JSONDecodeError, TypeError):
                references_data = []
        
        messages.append({
            "sender": row[0], 
            "content": row[1],
            "references": references_data
        })
        
    conn.close()
    return {"messages": messages}

@app.post("/new_session")
def new_session(user_id: str = Form(...), session_name: str = Form(...)):
    conn = get_db()
    cursor = conn.cursor()
    session_id = str(uuid.uuid4())
    current_time = datetime.datetime.utcnow().isoformat()
    cursor.execute("INSERT INTO sessions (session_id, user_id, docs, name, last_updated) VALUES (?, ?, ?, ?, ?)",
                   (session_id, user_id, "", session_name, current_time))
    conn.commit()
    new_session_data = {
        "session_id": session_id,
        "docs": [],
        "name": session_name,
        "last_updated": current_time
    }
    conn.close()
    return new_session_data

@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
    cursor.execute("DELETE FROM sessions WHERE session_id=?", (session_id,))
    conn.commit()
    if cursor.rowcount == 0:
        conn.close()
        return {"error": "Session not found"}
    conn.close()
    return {"message": "Session deleted successfully"}


@app.post("/clone")
def clone(req: CloneRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, docs, name FROM sessions WHERE session_id=?", (req.session_id,))
    row = cursor.fetchone()
    if not row:
        return {"error": "Invalid session_id"}
    user_id, docs, old_name = row
    new_session_id = str(uuid.uuid4())
    new_name = f"{old_name} (Copy)"
    current_time = datetime.datetime.utcnow().isoformat()
    cursor.execute("INSERT INTO sessions (session_id, user_id, docs, name, last_updated) VALUES (?, ?, ?, ?, ?)",
                   (new_session_id, user_id, docs, new_name, current_time))
    conn.commit()
    new_session_data = {"session_id": new_session_id, "name": new_name, "last_updated": current_time}
    conn.close()
    return new_session_data


@app.post("/upload")
async def upload(session_id: str = Form(...), files: Optional[List[UploadFile]] = None, url: Optional[str] = Form(None)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT docs FROM sessions WHERE session_id=?", (session_id,))
    row = cursor.fetchone()
    if not row: 
        conn.close()
        return {"error": "Invalid session"}
    
    doc_ids = []
    
    
    MIME_TYPE_MAP = {
        'txt': 'text/plain', '.csv': 'text/csv', '.md': 'text/markdown', 
        'py': 'text/x-python', '.js': 'application/javascript', 
        'html': 'text/html', '.css': 'text/css', '.json': 'application/json', 
        'java': 'text/x-java-source', '.pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'
    }

    if files:
        unsupported_count = 0
        for file in files:
            try:
                # Read file content into bytes
                file_content = await file.read()
                
                # Use the new FileDownloader to handle the bytes
                cache_path, file_extension = await document_preprocessor.file_downloader.fetch_file(file_content, file.filename)
                if cache_path == 'not supported':
                    unsupported_count += 1
                    continue
                # Determine mime type
                mime_type = file.content_type
                if mime_type == "application/octet-stream" or not mime_type:
                    mime_type = MIME_TYPE_MAP.get(file_extension, "application/octet-stream")
                
                cursor.execute("INSERT INTO documents (name, path, mime_type) VALUES (?, ?, ?)", 
                              (file.filename, cache_path, mime_type))
                doc_id = cursor.lastrowid
                doc_ids.append(str(doc_id))
                processed_doc_id, doc_type = await document_preprocessor.process_document((cache_path, file_extension, doc_id), force_reprocess=True, skip_length_check=True)
                if doc_type == "tabular":
                    tabular_data_cache[doc_id] = document_preprocessor.get_special_document_details(processed_doc_id)
                elif doc_type == "oneshot":
                    pass
            
                
            except Exception as e:
                logger.error("Failed to process uploaded file", filename=file.filename, error=str(e))
                conn.close()
                return {"error": f"Failed to process file {file.filename}: {str(e)}"}
    
    elif url:
        try:
            result = await document_preprocessor.file_downloader.fetch_file(url)
            
            # Handle the result based on what FileDownloader returns
            if isinstance(result, list) and len(result) == 2 and result[0] == 'not supported':
                conn.close()
                return {"error": f"File type '.{result[1]}' is not supported"}
            
            cache_path, file_extension = result
            
            # If it's just a URL (unsupported type), handle as before
            if file_extension == "url":
                conn.close()
                return {"error": "Unsupported file type from URL"}
            
            original_name = Path(urlparse(url).path).name or f"download_{uuid.uuid4()}"
            
            # Determine display name and mime type
            display_name = original_name
            mime_type = MIME_TYPE_MAP.get(file_extension, "application/octet-stream")
            cursor.execute("INSERT INTO documents (name, path, mime_type) VALUES (?, ?, ?)", 
                          (display_name, cache_path, mime_type))
            doc_id = cursor.lastrowid
            doc_ids.append(str(doc_id))
            
            processed_doc_id, doc_type = await document_preprocessor.process_document((cache_path, file_extension, doc_id), force_reprocess=True, skip_length_check=True)
            
            
        except Exception as e:
            logger.error("Failed to download from URL", url=url, error=str(e))
            conn.close()
            return {"error": f"Failed to fetch URL: {str(e)}"}
    
    else:
        conn.close()
        return {"error": "No file or URL provided"}
    
    # Update session docs (keeping your original logic)
    docs_list = [doc_id for doc_id in row[0].split(',') if doc_id] if row[0] else []
    docs_list.extend(doc_ids)
    current_time = datetime.datetime.utcnow().isoformat()
    cursor.execute("UPDATE sessions SET docs=?, last_updated=? WHERE session_id=?", 
                  (",".join(docs_list), current_time, session_id))
    conn.commit()
    conn.close()
    
    return {"message": "File(s) uploaded", "doc_ids": doc_ids} if unsupported_count == 0 else {"message": "Files Uploaded, skipped unsopported", "doc_ids":doc_ids}

@app.get("/get_doc/{session_id}/{doc_id}")
def get_doc(session_id: str, doc_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT docs FROM sessions WHERE session_id=?", (session_id,))
    row = cursor.fetchone()
    if not row: conn.close(); return {"error": "Invalid session"}
    docs_list = row[0].split(",") if row[0] else []
    if str(doc_id) not in docs_list: conn.close(); return {"error": "Document not part of this session"}
    cursor.execute("SELECT path, mime_type, name FROM documents WHERE doc_id=?", (doc_id,))
    doc_row = cursor.fetchone()
    conn.close()
    if not doc_row: return {"error": "Invalid document"}
    file_path, mime_type, file_name = doc_row
    if not os.path.exists(file_path): return {"error": "File not found on server"}
    headers = {'Content-Disposition': f'inline; filename="{file_name}"'}
    return FileResponse(file_path, media_type=mime_type, headers=headers)



def parse_references(response_text: str) -> List[Dict[str, Any]]:
    """
    Parses a semi-structured LLM response string into a structured list of 
    dictionaries, separating text from its references.

    Args:
        response_text: The raw string output from the LLM.

    Returns:
        A list of dictionaries, where each dictionary represents a text segment
        with its corresponding references.
    """
    
    # This regex pattern looks for the reference block. The parentheses `()`
    # create a capturing group. When re.split is used with a capturing group,
    # the delimiters (the reference blocks themselves) are kept in the resulting list.
    # \s*[\s\S]*?\s* is a non-greedy way to match any character including newlines
    # inside the curly braces.
    pattern = r'(\s*\n\s*\{\s*[\s\S]*?\s*\})'
    
    # Split the text by the reference blocks. The result is an interleaved list:
    # ['text1', '{ref1}', 'text2', '{ref2}', 'text3']
    parts = re.split(pattern, response_text)
    
    # Filter out any empty or whitespace-only strings that might result from the split
    cleaned_parts = [part for part in parts if part and part.strip()]
    
    results: List[Dict[str, Union[str, list]]] = []
    i = 0
    while i < len(cleaned_parts):
        # The current part is assumed to be a text chunk
        text_chunk = cleaned_parts[i].strip()
        
        # Look ahead to see if the next part is a reference block
        if i + 1 < len(cleaned_parts) and cleaned_parts[i+1].strip().startswith('{'):
            reference_str = cleaned_parts[i+1].strip()
            try:
                # Try to parse the reference string as JSON
                ref_json = json.loads(reference_str)
                
                # Reformat the reference to match the target structure
                # This includes renaming the 'reference' key to 'text_snippet'
                formatted_ref = {
                    "doc_id": ref_json.get("doc_id"),
                    "page_num": ref_json.get("page_num"),
                    "text_snippet": ref_json.get("reference")
                }
                
                # Append the text chunk with its parsed reference
                results.append({
                    "text": text_chunk,
                    "references": [formatted_ref]
                })
                # We have processed both the text and the reference, so jump ahead by 2
                i += 2
                continue
            except json.JSONDecodeError:
                # --- SAFE FALLBACK ---
                # If JSON parsing fails, the LLM generated a malformed reference.
                # Treat the malformed block as plain text and append it to the
                # current text chunk.
                text_chunk += "\n\n" + reference_str
                # We still consumed two parts, so jump ahead by 2
                i += 2
                # The loop will continue, and this combined text_chunk will be
                # processed in the 'else' block below in the next iteration,
                # or added as a no-reference block if it's the end.
                # To handle it now, we can just create the block here.
                results.append({
                    "text": text_chunk,
                    "references": []
                })
                continue
        
        # If there was no reference block following, or if we are at the end
        # of the list, this is a text chunk with no references.
        if text_chunk: # Ensure we don't add empty text blocks
            results.append({
                "text": text_chunk,
                "references": []
            })
        
        # Move to the next part
        i += 1
        
    return results

@app.post("/query")
async def query(req: QueryRequest):
    conn = get_db()
    cursor = conn.cursor()
    current_time = datetime.datetime.utcnow().isoformat()

    
    request_id = rag_logger.generate_request_id()
    rag_logger.start_request_timing(request_id)
    logger.info("Query", request_id=request_id, session_id = req.session_id)
    print(f"Query. request id: {request_id} session_id : {req.session_id}")
    print(f"Question:{req.question}")

    cursor.execute('INSERT INTO messages (message_id, session_id, sender, content, "references", timestamp) VALUES (?, ?, ?, ?, ?, ?)',
                   (str(uuid.uuid4()), req.session_id, 'user', req.question, None, current_time))

    # RAG Logic
    cursor.execute("SELECT docs FROM sessions WHERE session_id=?", (req.session_id,))
    row = cursor.fetchone()
    if not row or not row[0]: conn.close(); return {"error": "No documents in this session"}
    doc_ids = [doc_id for doc_id in row[0].split(',') if doc_id]
    if not doc_ids: conn.close(); return {"error": "No valid documents in this session"}

    extra_chunks = []
    not_found = []


    tabular_MIMES = ['text/csv', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']

    for doc_id in doc_ids:
        cursor.execute("SELECT path, mime_type FROM documents WHERE doc_id=?", (doc_id,))
        doc_row = cursor.fetchone()
        if not doc_row: conn.close(); not_found.append(doc_id)
        file_path, mime_type = doc_row
        if mime_type in tabular_MIMES:
            chunks = tabular_data_cache.get(doc_id)
            if chunks is None:
                chunks = document_preprocessor.process_document((file_path, file_path.split('.')[-1], doc_id),  force_reprocess=True)
                tabular_data_cache[doc_id] = chunks
                extra_chunks.extend(chunks)
        elif mime_type.startswith("image/"):
            extra_chunks.append(extract_data_from_image(file_path))

    answer, pipeline_timings = await rag_processor.answer_question(
        question=req.question, doc_ids=doc_ids, logger=rag_logger, request_id=request_id, extra_chunks=extra_chunks
    )
    print(f"Answer: {answer}")
    print("Pipeline Timings: ", json.dumps(pipeline_timings, indent=2))

    formatted_answer = parse_references(answer)

    print("formatted_answer", json.dumps(formatted_answer, indent=2))

    all_references = []
    full_answer = ""
    for d in formatted_answer:
        full_answer += d['text']
        all_references.extend(d['references'])


    # Store assistant response
    references_json = json.dumps(all_references)
    print("References: ", references_json)
    cursor.execute('INSERT INTO messages (message_id, session_id, sender, content, "references", timestamp) VALUES (?, ?, ?, ?, ?, ?)',
                   (str(uuid.uuid4()), req.session_id, 'assistant', full_answer, references_json, current_time))

    cursor.execute("UPDATE sessions SET last_updated=? WHERE session_id=?", (current_time, req.session_id))
    conn.commit()
    conn.close()
    
    return {
        "answer_parts": formatted_answer,
        "metadata": {"confidence_score": round(random.uniform(0.5, 0.99), 2), "language": "en"}
    }



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host=API_HOST, port=API_PORT, reload=API_RELOAD, log_level="info")
