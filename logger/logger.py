"""
Enhanced in-memory logging system for RAG API with detailed pipeline timing.
Since HuggingFace doesn't allow persistent file storage, logs are stored in memory.
"""

import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict, field
import threading
from logger.custom_logger import CustomLogger

logger = CustomLogger().get_logger(__file__)

@dataclass
class PipelineTimings:
    """Detailed timing for each stage of the RAG pipeline."""
    query_expansion_time: float = 0.0
    hybrid_search_time: float = 0.0
    semantic_search_time: float = 0.0
    bm25_search_time: float = 0.0
    score_fusion_time: float = 0.0
    reranking_time: float = 0.0
    context_creation_time: float = 0.0
    llm_generation_time: float = 0.0
    total_pipeline_time: float = 0.0

@dataclass
class LogEntry:
    """Enhanced structure for a single log entry with detailed timing."""
    timestamp: str
    request_id: str
    document_url: str
    questions: List[str]
    answers: List[str]
    processing_time_seconds: float
    total_questions: int
    status: str  # 'success', 'error', 'partial'
    error_message: Optional[str] = None
    document_id: Optional[str] = None
    was_preprocessed: bool = False
    # Enhanced timing details
    request_start_time: str = ""
    request_end_time: str = ""
    pipeline_timings: Dict[str, Any] = field(default_factory=dict)
    # Per-question timings
    question_timings: List[Dict[str, Any]] = field(default_factory=list)

class RAGLogger:
    """Enhanced in-memory logging system for RAG API requests with detailed pipeline timing."""
    
    def __init__(self):
        self.logs: List[LogEntry] = []
        self.server_start_time = datetime.now().isoformat()
        self.request_counter = 0
        self._lock = threading.Lock()
        # Active request tracking for timing
        self._active_requests: Dict[str, Dict[str, Any]] = {}
    
    def generate_request_id(self) -> str:
        """Generate a unique request ID."""
        with self._lock:
            self.request_counter += 1
            return f"req_{self.request_counter:06d}"
    
    def start_request_timing(self, request_id: str) -> None:
        """Start timing for a new request."""
        self._active_requests[request_id] = {
            'start_time': time.time(),
            'start_timestamp': datetime.now().isoformat(),
            'pipeline_stages': {},
            'question_timings': []
        }
    
    def log_pipeline_stage(self, request_id: str, stage_name: str, duration: float) -> None:
        """Log the timing for a specific pipeline stage."""
        if request_id in self._active_requests:
            self._active_requests[request_id]['pipeline_stages'][stage_name] = {
                'duration_seconds': round(duration, 4),
                'timestamp': datetime.now().isoformat()
            }
            logger.info("pipeline_stage", request_id=request_id, stage=stage_name, duration_sec=round(duration, 4))
    
    def log_question_timing(self, request_id: str, question_index: int, question: str, 
                           answer: str, duration: float, pipeline_timings: Dict[str, float]) -> None:
        """Log timing for individual question processing."""
        if request_id in self._active_requests:
            question_timing = {
                'question_index': question_index,
                'question': question[:100] + "..." if len(question) > 100 else question,
                'answer_length': len(answer),
                'total_time_seconds': round(duration, 4),
                'pipeline_breakdown': {k: round(v, 4) for k, v in pipeline_timings.items()},
                'timestamp': datetime.now().isoformat()
            }
            self._active_requests[request_id]['question_timings'].append(question_timing)
            # Compact structured log
            logger.info(
                "question_timing",
                request_id=request_id,
                q_index=question_index + 1,
                duration_sec=round(duration, 4),
                answer_length=len(answer),
                breakdown={k: round(v, 4) for k, v in pipeline_timings.items()},
                preview=question[:60]
            )
    
    def end_request_timing(self, request_id: str) -> Dict[str, Any]:
        """End timing for a request and return timing data."""
        if request_id not in self._active_requests:
            return {}
        
        request_data = self._active_requests[request_id]
        total_time = time.time() - request_data['start_time']
        
        timing_data = {
            'start_time': request_data['start_timestamp'],
            'end_time': datetime.now().isoformat(),
            'total_time_seconds': round(total_time, 4),
            'pipeline_stages': request_data['pipeline_stages'],
            'question_timings': request_data['question_timings']
        }
        
        # Cleanup
        del self._active_requests[request_id]
        
        return timing_data
    
    def log_request(
        self, 
        document_url: str, 
        questions: List[str], 
        answers: List[str], 
        processing_time: float,
        status: str = "success",
        error_message: Optional[str] = None,
        document_id: Optional[str] = None,
        was_preprocessed: bool = False,
        timing_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a RAG API request with enhanced timing information.
        
        Args:
            document_url: URL of the document processed
            questions: List of questions asked
            answers: List of answers generated
            processing_time: Time taken in seconds
            status: Request status ('success', 'error', 'partial')
            error_message: Error message if any
            document_id: Generated document ID
            was_preprocessed: Whether document was already processed
            timing_data: Detailed timing breakdown from pipeline
        
        Returns:
            str: Request ID
        """
        request_id = self.generate_request_id()
        
        # Extract timing information
        pipeline_timings = {}
        question_timings = []
        request_start_time = ""
        request_end_time = ""
        
        if timing_data:
            request_start_time = timing_data.get('start_time', '')
            request_end_time = timing_data.get('end_time', '')
            pipeline_timings = timing_data.get('pipeline_stages', {})
            question_timings = timing_data.get('question_timings', [])
        
        log_entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            request_id=request_id,
            document_url=document_url,
            questions=questions,
            answers=answers,
            processing_time_seconds=round(processing_time, 2),
            total_questions=len(questions),
            status=status,
            error_message=error_message,
            document_id=document_id,
            was_preprocessed=was_preprocessed,
            request_start_time=request_start_time,
            request_end_time=request_end_time,
            pipeline_timings=pipeline_timings,
            question_timings=question_timings
        )
        
        with self._lock:
            self.logs.append(log_entry)
        
        # Structured log summary
        logger.info(
            "request_completed",
            request_id=request_id,
            duration_sec=round(processing_time, 2),
            document=document_url,
            questions=len(questions),
            status=status,
            error=error_message,
            stages={k: v.get('duration_seconds', 0) for k, v in pipeline_timings.items()} if pipeline_timings else {},
        )
        
        return request_id
    
    def get_logs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all logs as a list of dictionaries.
        
        Args:
            limit: Maximum number of logs to return (most recent first)
        
        Returns:
            List of log entries as dictionaries
        """
        with self._lock:
            logs_list = [asdict(log) for log in self.logs]
        
        # Return most recent first
        logs_list.reverse()
        
        if limit:
            logs_list = logs_list[:limit]
        
        return logs_list
    
    def get_logs_summary(self) -> Dict[str, Any]:
        """Get summary statistics of all logs."""
        with self._lock:
            total_requests = len(self.logs)
            if total_requests == 0:
                return {
                    "server_start_time": self.server_start_time,
                    "total_requests": 0,
                    "successful_requests": 0,
                    "error_requests": 0,
                    "average_processing_time": 0,
                    "total_questions_processed": 0,
                    "total_documents_processed": 0
                }
            
            successful_requests = len([log for log in self.logs if log.status == "success"])
            error_requests = len([log for log in self.logs if log.status == "error"])
            total_processing_time = sum(log.processing_time_seconds for log in self.logs)
            total_questions = sum(log.total_questions for log in self.logs)
            unique_documents = len(set(log.document_url for log in self.logs))
            preprocessed_count = len([log for log in self.logs if log.was_preprocessed])
            
            # Enhanced timing statistics
            pipeline_times = []
            question_times = []
            stage_times = {'query_expansion': [], 'hybrid_search': [], 'reranking': [], 
                          'context_creation': [], 'llm_generation': []}
            
            for log in self.logs:
                # Collect question timing data
                for q_timing in log.question_timings:
                    question_times.append(q_timing.get('total_time_seconds', 0))
                    # Collect stage-specific timings
                    breakdown = q_timing.get('pipeline_breakdown', {})
                    for stage, duration in breakdown.items():
                        if stage in stage_times:
                            stage_times[stage].append(duration)
            
            # Calculate averages for each stage
            avg_stage_times = {}
            for stage, times in stage_times.items():
                if times:
                    avg_stage_times[f'avg_{stage}_time'] = round(sum(times) / len(times), 4)
                    avg_stage_times[f'max_{stage}_time'] = round(max(times), 4)
                else:
                    avg_stage_times[f'avg_{stage}_time'] = 0
                    avg_stage_times[f'max_{stage}_time'] = 0
            
            return {
                "server_start_time": self.server_start_time,
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "error_requests": error_requests,
                "partial_requests": total_requests - successful_requests - error_requests,
                "success_rate": round((successful_requests / total_requests) * 100, 2),
                "average_processing_time": round(total_processing_time / total_requests, 2),
                "total_questions_processed": total_questions,
                "total_documents_processed": unique_documents,
                "documents_already_preprocessed": preprocessed_count,
                "documents_newly_processed": total_requests - preprocessed_count,
                "average_question_time": round(sum(question_times) / len(question_times), 4) if question_times else 0,
                "pipeline_performance": avg_stage_times
            }
    
    def export_logs(self) -> Dict[str, Any]:
        """
        Export all logs in a structured format for external consumption.
        
        Returns:
            Dict containing metadata and all logs
        """
        summary = self.get_logs_summary()
        logs = self.get_logs()
        
        return {
            "export_timestamp": datetime.now().isoformat(),
            "metadata": summary,
            "logs": logs
        }
    
    def get_logs_by_document(self, document_url: str) -> List[Dict[str, Any]]:
        """Get all logs for a specific document URL."""
        with self._lock:
            filtered_logs = [
                asdict(log) for log in self.logs 
                if log.document_url == document_url
            ]
        
        # Return most recent first
        filtered_logs.reverse()
        return filtered_logs
    
    def get_recent_logs(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get logs from the last N minutes."""
        cutoff_time = datetime.now().timestamp() - (minutes * 60)
        
        with self._lock:
            recent_logs = []
            for log in self.logs:
                log_time = datetime.fromisoformat(log.timestamp).timestamp()
                if log_time >= cutoff_time:
                    recent_logs.append(asdict(log))
        
        # Return most recent first
        recent_logs.reverse()
        return recent_logs

# Global logger instance
rag_logger = RAGLogger()
