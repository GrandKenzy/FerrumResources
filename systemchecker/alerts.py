import json
import time
import uuid
from datetime import datetime, timezone
from config import ALERTS_FILE
from settings import get_setting
from processes import collect_processes

def check_for_alerts():
    """Scan processes and system state to generate alerts based on settings."""
    procs = collect_processes()
    alerts = []
    
    cpu_thresh = get_setting("processes.high_cpu_threshold", 70)
    ram_thresh = get_setting("processes.high_ram_threshold", 80)
    score_thresh = get_setting("processes.suspicious_score_threshold", 50)
    
    for p in procs:
        # High CPU
        if p.get("cpu_percent", 0) > cpu_thresh:
            alerts.append(_create_alert("high_cpu", "high", f"Uso de CPU elevado: {p['name']} ({p['pid']})", p))
            
        # High RAM
        if p.get("memory_percent", 0) > ram_thresh:
            alerts.append(_create_alert("high_ram", "medium", f"Uso de RAM elevado: {p['name']} ({p['pid']})", p))
            
        # Suspicious
        if p.get("risk_score", 0) > score_thresh:
            severity = "critical" if p.get("risk_score", 0) > 80 else "high"
            alerts.append(_create_alert("suspicious", severity, f"Proceso sospechoso detectado: {p['name']} (Score {p['risk_score']})", p))

    # Save active alerts
    if alerts:
        _save_alerts(alerts)
    
    return alerts

def _create_alert(kind, severity, message, proc_info):
    return {
        "id": uuid.uuid4().hex[:12],
        "time": datetime.now(timezone.utc).isoformat(),
        "severity": severity,
        "kind": kind,
        "pid": proc_info.get("pid"),
        "process_name": proc_info.get("name"),
        "message": message,
        "details": {
            "cpu": proc_info.get("cpu_percent"),
            "ram": proc_info.get("memory_percent"),
            "risk_score": proc_info.get("risk_score"),
            "reasons": proc_info.get("risk_reasons")
        },
        "status": "active"
    }

def _save_alerts(alerts):
    try:
        with open(ALERTS_FILE, "a", encoding="utf-8") as f:
            for a in alerts:
                f.write(json.dumps(a, ensure_ascii=False) + "\n")
    except:
        pass

def get_active_alerts(limit=50):
    if not ALERTS_FILE.exists():
        return []
    alerts = []
    try:
        with open(ALERTS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    a = json.loads(line)
                    if a.get("status") == "active":
                        alerts.append(a)
        return alerts[-limit:][::-1]
    except:
        return []

def resolve_alert(alert_id):
    if not ALERTS_FILE.exists():
        return
    temp_file = ALERTS_FILE.with_suffix(".tmp")
    try:
        with open(ALERTS_FILE, "r", encoding="utf-8") as f, \
             open(temp_file, "w", encoding="utf-8") as out:
            for line in f:
                if line.strip():
                    a = json.loads(line)
                    if a.get("id") == alert_id:
                        a["status"] = "resolved"
                    out.write(json.dumps(a, ensure_ascii=False) + "\n")
        temp_file.replace(ALERTS_FILE)
    except:
        if temp_file.exists():
            temp_file.unlink()
