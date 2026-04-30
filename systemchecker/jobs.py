import threading
import uuid
import time
import json
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional, Callable
from config import JOBS_FILE

@dataclass
class Job:
    id: str
    kind: str
    status: str = "queued"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    progress: int = 0
    message: str = ""
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

_jobs: Dict[str, Job] = {}
_jobs_lock = threading.Lock()

def save_job_to_disk(job: Job):
    try:
        with open(JOBS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(job), ensure_ascii=False) + "\n")
    except:
        pass

def create_job(kind: str, message: str = "") -> Job:
    job = Job(id=uuid.uuid4().hex[:12], kind=kind, message=message)
    with _jobs_lock:
        _jobs[job.id] = job
    save_job_to_disk(job)
    return job

def update_job(job_id: str, **kwargs):
    with _jobs_lock:
        if job_id in _jobs:
            job = _jobs[job_id]
            for k, v in kwargs.items():
                setattr(job, k, v)
            job.updated_at = datetime.now(timezone.utc).isoformat()
            save_job_to_disk(job)

def get_job(job_id: str) -> Optional[Job]:
    with _jobs_lock:
        return _jobs.get(job_id)

def run_in_background(kind: str, target: Callable, *args, **kwargs) -> str:
    job = create_job(kind, "Iniciando tarea...")
    
    def wrapper():
        try:
            update_job(job.id, status="running", progress=5)
            # Pass job_id as first argument if target expects it
            result = target(job.id, *args, **kwargs)
            update_job(job.id, status="done", progress=100, message="Completado", result=result or {})
        except Exception as e:
            update_job(job.id, status="error", progress=100, message="Error", error=str(e))
            
    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()
    return job.id

def list_active_jobs():
    with _jobs_lock:
        return [asdict(j) for j in _jobs.values()]
