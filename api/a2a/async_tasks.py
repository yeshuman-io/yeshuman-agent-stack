"""
Async Task Management for A2A Protocol.
Enables long-running operations beyond the 30-second HTTP timeout.
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json
import threading
import time
from django.utils import timezone


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AsyncTaskResult:
    """Result of an async task execution."""
    task_id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    callback_url: Optional[str] = None


class AsyncTaskManager:
    """
    Manages long-running async tasks for the A2A protocol.
    
    This enables operations that take longer than typical HTTP timeouts
    by providing task tracking, progress updates, and callback notifications.
    """
    
    def __init__(self):
        self.tasks: Dict[str, AsyncTaskResult] = {}
        self.task_functions: Dict[str, Callable] = {}
        self.lock = threading.Lock()
        
        # Register default task types
        self._register_default_tasks()
    
    def _register_default_tasks(self):
        """Register default async task types."""
        self.register_task_type("long_calculation", self._long_calculation_task)
        self.register_task_type("data_analysis", self._data_analysis_task)
        self.register_task_type("web_research", self._web_research_task)
        self.register_task_type("file_processing", self._file_processing_task)
    
    def register_task_type(self, task_type: str, task_function: Callable):
        """Register a new task type with its execution function."""
        self.task_functions[task_type] = task_function
    
    def create_task(self, task_type: str, params: Dict[str, Any], 
                   callback_url: Optional[str] = None) -> str:
        """
        Create and start a new async task.
        
        Args:
            task_type: Type of task to execute
            params: Parameters for the task
            callback_url: URL to notify when task completes
            
        Returns:
            task_id: Unique identifier for the task
        """
        task_id = str(uuid.uuid4())
        
        if task_type not in self.task_functions:
            raise ValueError(f"Unknown task type: {task_type}")
        
        task_result = AsyncTaskResult(
            task_id=task_id,
            status=TaskStatus.PENDING,
            callback_url=callback_url
        )
        
        with self.lock:
            self.tasks[task_id] = task_result
        
        # Start task in background thread
        thread = threading.Thread(
            target=self._execute_task,
            args=(task_id, task_type, params)
        )
        thread.daemon = True
        thread.start()
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[AsyncTaskResult]:
        """Get the current status of a task."""
        with self.lock:
            return self.tasks.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                    task.status = TaskStatus.CANCELLED
                    task.completed_at = datetime.now(dt_timezone.utc)
                    return True
        return False
    
    def _execute_task(self, task_id: str, task_type: str, params: Dict[str, Any]):
        """Execute a task in the background."""
        try:
            with self.lock:
                task = self.tasks[task_id]
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now(dt_timezone.utc)
            
            # Execute the task function
            task_function = self.task_functions[task_type]
            result = task_function(task_id, params, self._update_progress)
            
            with self.lock:
                task = self.tasks[task_id]
                if task.status != TaskStatus.CANCELLED:
                    task.status = TaskStatus.COMPLETED
                    task.result = result
                    task.progress = 100.0
                    task.completed_at = datetime.now(dt_timezone.utc)
            
            # Send callback notification if provided
            if task.callback_url:
                self._send_callback_notification(task_id)
                
        except Exception as e:
            with self.lock:
                task = self.tasks[task_id]
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.completed_at = datetime.now(dt_timezone.utc)
            
            # Send callback notification for failures too
            if task.callback_url:
                self._send_callback_notification(task_id)
    
    def _update_progress(self, task_id: str, progress: float):
        """Update task progress (0-100)."""
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].progress = min(100.0, max(0.0, progress))
    
    def _send_callback_notification(self, task_id: str):
        """Send HTTP callback notification when task completes."""
        try:
            import requests
            task = self.tasks[task_id]
            
            payload = {
                "task_id": task_id,
                "status": task.status.value,
                "result": task.result,
                "error": task.error,
                "progress": task.progress,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None
            }
            
            requests.post(
                task.callback_url,
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
        except Exception as e:
            # Log callback errors but don't fail the task
            print(f"Callback notification failed for task {task_id}: {e}")
    
    # Default task implementations
    
    def _long_calculation_task(self, task_id: str, params: Dict[str, Any], 
                              update_progress: Callable) -> Dict[str, Any]:
        """Simulate a long-running calculation."""
        expression = params.get("expression", "2+2")
        iterations = params.get("iterations", 100)
        
        result = 0
        for i in range(iterations):
            time.sleep(0.1)  # Simulate work
            result += eval(expression) if expression.replace("+", "").replace("-", "").replace("*", "").replace("/", "").replace("(", "").replace(")", "").replace(" ", "").isdigit() else i
            update_progress(task_id, (i + 1) / iterations * 100)
        
        return {
            "type": "long_calculation",
            "expression": expression,
            "iterations": iterations,
            "final_result": result,
            "completed_at": datetime.now(dt_timezone.utc).isoformat()
        }
    
    def _data_analysis_task(self, task_id: str, params: Dict[str, Any], 
                           update_progress: Callable) -> Dict[str, Any]:
        """Simulate data analysis task."""
        data_size = params.get("data_size", 1000)
        analysis_type = params.get("analysis_type", "statistical")
        
        # Simulate processing chunks of data
        chunk_size = 100
        chunks = data_size // chunk_size
        results = []
        
        for i in range(chunks):
            time.sleep(0.2)  # Simulate processing time
            
            # Mock analysis results
            chunk_result = {
                "chunk": i + 1,
                "mean": 50.0 + (i * 0.1),
                "std": 10.0 + (i * 0.05),
                "samples": chunk_size
            }
            results.append(chunk_result)
            
            update_progress(task_id, (i + 1) / chunks * 100)
        
        return {
            "type": "data_analysis",
            "analysis_type": analysis_type,
            "data_size": data_size,
            "chunks_processed": len(results),
            "summary": {
                "total_mean": sum(r["mean"] for r in results) / len(results),
                "total_std": sum(r["std"] for r in results) / len(results),
                "total_samples": sum(r["samples"] for r in results)
            },
            "detailed_results": results
        }
    
    def _web_research_task(self, task_id: str, params: Dict[str, Any], 
                          update_progress: Callable) -> Dict[str, Any]:
        """Simulate web research task."""
        query = params.get("query", "artificial intelligence")
        num_sources = params.get("num_sources", 5)
        
        sources = []
        for i in range(num_sources):
            time.sleep(1.0)  # Simulate web request time
            
            source = {
                "url": f"https://example.com/source_{i+1}",
                "title": f"Research Article {i+1}: {query}",
                "summary": f"This article discusses {query} from perspective {i+1}.",
                "relevance_score": 0.9 - (i * 0.1),
                "retrieved_at": datetime.now(dt_timezone.utc).isoformat()
            }
            sources.append(source)
            
            update_progress(task_id, (i + 1) / num_sources * 100)
        
        return {
            "type": "web_research",
            "query": query,
            "sources_found": len(sources),
            "sources": sources,
            "summary": f"Found {len(sources)} relevant sources for '{query}'"
        }
    
    def _file_processing_task(self, task_id: str, params: Dict[str, Any], 
                             update_progress: Callable) -> Dict[str, Any]:
        """Simulate file processing task."""
        file_type = params.get("file_type", "text")
        file_size_mb = params.get("file_size_mb", 10)
        
        # Simulate processing file in chunks
        chunks = file_size_mb  # 1 MB per chunk
        processed_chunks = []
        
        for i in range(chunks):
            time.sleep(0.5)  # Simulate processing time per MB
            
            chunk_info = {
                "chunk": i + 1,
                "size_mb": 1,
                "words_processed": 1000 + (i * 100),
                "lines_processed": 100 + (i * 10)
            }
            processed_chunks.append(chunk_info)
            
            update_progress(task_id, (i + 1) / chunks * 100)
        
        return {
            "type": "file_processing",
            "file_type": file_type,
            "file_size_mb": file_size_mb,
            "chunks_processed": len(processed_chunks),
            "total_words": sum(c["words_processed"] for c in processed_chunks),
            "total_lines": sum(c["lines_processed"] for c in processed_chunks),
            "processing_details": processed_chunks
        }


# Global task manager instance
async_task_manager = AsyncTaskManager()
