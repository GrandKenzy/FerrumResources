import os
import psutil
import time
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple
from system_info import bytes_fmt, pct
from security import load_security_rules

def normalize_name(name: str) -> str:
    return (name or "").strip().lower()

def path_lower(path: str) -> str:
    return str(path or "").replace("/", os.sep).lower()

def risk_score(proc_info: Dict[str, Any], rules: Dict[str, Any]) -> Tuple[int, List[str]]:
    score = 0
    reasons: List[str] = []
    name = normalize_name(proc_info.get("name"))
    exe = path_lower(proc_info.get("exe"))
    cmdline = " ".join(proc_info.get("cmdline") or [])
    
    if not name:
        score += 10
        reasons.append("Proceso sin nombre visible")

    if name in {normalize_name(x) for x in rules.get("blacklist_exact", [])}:
        score += 100
        reasons.append("Coincide con blacklist exacta")

    for needle in rules.get("blacklist_contains", []):
        if needle and needle.lower() in name:
            score += 45
            reasons.append(f"Nombre contiene patrón sospechoso: {needle}")

    for pattern in rules.get("suspicious_cmdline_patterns", []):
        try:
            if re.search(pattern, cmdline):
                score += 35
                reasons.append(f"Cmdline sospechosa: {pattern}")
        except:
            continue

    if not proc_info.get("exe"):
        score += 8
        reasons.append("Ruta del ejecutable no disponible")

    for p in rules.get("suspicious_paths", []):
        if p.lower().replace("/", os.sep) in exe:
            score += 25
            reasons.append(f"Ejecutándose desde ruta temporal/sensible: {p}")

    if proc_info.get("cpu_percent", 0) >= 75 and name not in {normalize_name(x) for x in rules.get("known_good_names", [])}:
        score += 12
        reasons.append("CPU alto en proceso no conocido")

    if proc_info.get("memory_percent", 0) >= 20 and name not in {normalize_name(x) for x in rules.get("known_good_names", [])}:
        score += 12
        reasons.append("RAM alta en proceso no conocido")

    conns = proc_info.get("connections_count", 0) or 0
    if conns >= 20 and name not in {normalize_name(x) for x in rules.get("known_good_names", [])}:
        score += 15
        reasons.append("Muchas conexiones de red")

    if name not in {normalize_name(x) for x in rules.get("known_good_names", [])} and not reasons:
        score += 4
        reasons.append("No está en lista de conocidos")

    score = max(0, min(score, 100))
    return score, reasons

def risk_label(score: int) -> str:
    if score >= 80: return "critical"
    if score >= 50: return "high"
    if score >= 20: return "medium"
    return "low"

def collect_processes() -> List[Dict[str, Any]]:
    rules = load_security_rules()
    attrs = ["pid", "name", "username", "status", "cpu_percent", "memory_percent", "create_time", "exe", "cmdline", "num_threads"]
    rows = []
    
    # Prime CPU counters
    for p in psutil.process_iter(["pid"]):
        try: p.cpu_percent(interval=None)
        except: pass
    time.sleep(0.04)

    for proc in psutil.process_iter(attrs):
        try:
            info = proc.info
            cpu = proc.cpu_percent(interval=None)
            mem = proc.memory_percent()
            
            try: conns = len(proc.net_connections(kind="inet"))
            except: conns = 0
            
            row = {
                "pid": info.get("pid"),
                "name": info.get("name") or "",
                "username": info.get("username") or "",
                "status": info.get("status") or "",
                "cpu_percent": pct(cpu),
                "memory_percent": pct(mem),
                "memory_rss": bytes_fmt(proc.memory_info().rss),
                "create_time": datetime.fromtimestamp(info.get("create_time") or time.time()).isoformat(timespec="seconds"),
                "exe": info.get("exe") or "",
                "cmdline": info.get("cmdline") or [],
                "num_threads": info.get("num_threads") or 0,
                "connections_count": conns,
                "protected": normalize_name(info.get("name")) in {normalize_name(x) for x in rules.get("protected_names", [])},
            }
            score, reasons = risk_score(row, rules)
            row["risk_score"] = score
            row["risk_label"] = risk_label(score)
            row["risk_reasons"] = reasons
            rows.append(row)
        except:
            continue
    
    rows.sort(key=lambda r: (r["risk_score"], r["cpu_percent"]), reverse=True)
    return rows

def process_detail(pid: int) -> Dict[str, Any]:
    rules = load_security_rules()
    try:
        proc = psutil.Process(pid)
        with proc.oneshot():
            mem = proc.memory_info()
            try: conns = [{"laddr": f"{c.laddr.ip}:{c.laddr.port}", "raddr": f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "", "status": c.status} for c in proc.net_connections(kind="inet")[:50]]
            except: conns = []
            
            try: files = [f.path for f in proc.open_files()[:50]]
            except: files = []
            
            info = {
                "pid": pid,
                "ppid": proc.ppid(),
                "name": proc.name(),
                "username": proc.username(),
                "status": proc.status(),
                "exe": proc.exe(),
                "cwd": proc.cwd(),
                "cmdline": proc.cmdline(),
                "create_time": datetime.fromtimestamp(proc.create_time()).isoformat(timespec="seconds"),
                "cpu_percent": pct(proc.cpu_percent(interval=0.05)),
                "memory_percent": pct(proc.memory_percent()),
                "memory_info": {k: bytes_fmt(v) for k, v in mem._asdict().items()},
                "threads": proc.num_threads(),
                "connections": conns,
                "open_files": files,
                "children": [{"pid": c.pid, "name": c.name()} for c in proc.children()[:20]]
            }
            score, reasons = risk_score({**info, "connections_count": len(conns)}, rules)
            info["risk_score"] = score
            info["risk_label"] = risk_label(score)
            info["risk_reasons"] = reasons
            return info
    except:
        return {}
