import json
import time
from datetime import datetime, timezone
from config import AUDIT_FILE

def log_audit(action, target, result="ok", details=None):
    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        "actor": "local_user", # In a multi-user app this would be session user
        "action": action,
        "target": target,
        "result": result,
        "details": details or {}
    }
    try:
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"Failed to write audit log: {e}")

def get_recent_audit(limit=100):
    entries = []
    if not AUDIT_FILE.exists():
        return []
    try:
        with open(AUDIT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        return entries[-limit:][::-1]
    except:
        return []
