import json
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta
from config import SCHEDULER_FILE, AUDIT_FILE
from audit import log_audit

_tasks = []
_scheduler_thread = None
_stop_event = threading.Event()

def load_tasks():
    global _tasks
    if not SCHEDULER_FILE.exists():
        _tasks = [
            {
                "id": "daily_temp_cleanup",
                "name": "Limpieza temporal diaria",
                "kind": "cleanup_temp",
                "enabled": True,
                "interval_minutes": 1440,
                "last_run": None,
                "next_run": (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat(),
                "config": {"min_age_hours": 24}
            }
        ]
        save_tasks()
    else:
        try:
            with open(SCHEDULER_FILE, "r", encoding="utf-8") as f:
                _tasks = json.load(f)
        except:
            _tasks = []
    return _tasks

def save_tasks():
    with open(SCHEDULER_FILE, "w", encoding="utf-8") as f:
        json.dump(_tasks, f, indent=2)

def start_scheduler():
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    _stop_event.clear()
    _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True)
    _scheduler_thread.start()

def stop_scheduler():
    _stop_event.set()

def _scheduler_loop():
    while not _stop_event.is_set():
        now = datetime.now(timezone.utc)
        tasks = load_tasks()
        changed = False
        
        for task in tasks:
            if not task.get("enabled"): continue
            
            next_run_str = task.get("next_run")
            if not next_run_str:
                task["next_run"] = (now + timedelta(minutes=task["interval_minutes"])).isoformat()
                changed = True
                continue
                
            next_run = datetime.fromisoformat(next_run_str)
            if now >= next_run:
                # Run task
                _run_task_bg(task)
                
                # Schedule next
                task["last_run"] = now.isoformat()
                task["next_run"] = (now + timedelta(minutes=task["interval_minutes"])).isoformat()
                changed = True
        
        if changed:
            save_tasks()
            
        time.sleep(30)

def _run_task_bg(task):
    def worker():
        kind = task.get("kind")
        log_audit("scheduler_run", f"Task: {task.get('name')} ({kind})", "running")
        try:
            # Import here to avoid circular imports
            if kind == "cleanup_temp":
                from cleanup import scan_safe_cleanup, quarantine_files
                scan = scan_safe_cleanup(task.get("config", {}).get("min_age_hours", 24))
                if scan["files"]:
                    quarantine_files([f["path"] for f in scan["files"]], reason="Scheduled Cleanup")
            elif kind == "high_usage_scan":
                from alerts import check_for_alerts
                check_for_alerts()
            
            log_audit("scheduler_run", f"Task: {task.get('name')}", "ok")
        except Exception as e:
            log_audit("scheduler_run", f"Task: {task.get('name')}", "error", {"error": str(e)})
            
    threading.Thread(target=worker, daemon=True).start()

def run_task_now(task_id):
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            _run_task_bg(t)
            return True
    return False
