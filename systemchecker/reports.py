import json
import csv
import uuid
from datetime import datetime, timezone
from config import REPORTS_DIR
from system_info import collect_system_info
from processes import collect_processes
from ports import list_active_ports

def generate_report(kind="full"):
    report_id = uuid.uuid4().hex[:12]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    data = {
        "report_id": report_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "system": collect_system_info(),
    }
    
    if kind in ["full", "processes"]:
        data["processes"] = collect_processes()
    if kind in ["full", "ports"]:
        data["ports"] = list_active_ports()
        
    # JSON Report
    json_path = REPORTS_DIR / f"report_{timestamp}_{report_id}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    # CSV Processes
    if "processes" in data:
        csv_path = REPORTS_DIR / f"processes_{timestamp}_{report_id}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["pid", "name", "username", "cpu_percent", "memory_percent", "risk_score", "status"])
            writer.writeheader()
            for p in data["processes"]:
                writer.writerow({k: p.get(k) for k in ["pid", "name", "username", "cpu_percent", "memory_percent", "risk_score", "status"]})

    return {
        "id": report_id,
        "timestamp": timestamp,
        "json_file": json_path.name,
        "csv_file": f"processes_{timestamp}_{report_id}.csv" if "processes" in data else None
    }

def list_reports():
    reports = []
    for f in REPORTS_DIR.iterdir():
        if f.suffix == ".json":
            reports.append({
                "name": f.name,
                "size": f.stat().st_size,
                "time": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
    return sorted(reports, key=lambda x: x["time"], reverse=True)
