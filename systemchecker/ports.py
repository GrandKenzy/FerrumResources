import psutil
import socket
from typing import List, Dict, Any
from system_info import bytes_fmt

COMMON_PORTS = {
    80: "HTTP", 443: "HTTPS", 21: "FTP", 22: "SSH", 25: "SMTP",
    53: "DNS", 3306: "MySQL", 5432: "PostgreSQL", 27017: "MongoDB",
    6379: "Redis", 8080: "HTTP-Alt", 3000: "Node/React", 5000: "Flask/Docker",
    5173: "Vite", 8000: "Django/Laravel", 9000: "PHP-FPM"
}

def list_active_ports() -> List[Dict[str, Any]]:
    connections = psutil.net_connections(kind="inet")
    ports = []
    
    # Process grouping to avoid multiple psutil.Process calls
    proc_cache = {}
    
    for conn in connections:
        if conn.status == "LISTEN":
            port = conn.laddr.port
            pid = conn.pid
            
            p_name = "Unknown"
            p_exe = ""
            if pid:
                if pid not in proc_cache:
                    try:
                        p = psutil.Process(pid)
                        proc_cache[pid] = (p.name(), p.exe())
                    except:
                        proc_cache[pid] = ("Unknown", "")
                p_name, p_exe = proc_cache[pid]
            
            ports.append({
                "port": port,
                "type": "TCP" if conn.type == socket.SOCK_STREAM else "UDP",
                "pid": pid,
                "process_name": p_name,
                "exe": p_exe,
                "status": conn.status,
                "label": COMMON_PORTS.get(port, ""),
                "is_http": port in {80, 443, 8080, 3000, 5000, 5173, 8000}
            })
            
    return sorted(ports, key=lambda x: x["port"])

def find_free_port(start=3000, end=9000, preferred=None):
    if preferred:
        for p in preferred:
            if _is_port_free(p): return p
            
    for p in range(start, end + 1):
        if _is_port_free(p): return p
    return None

def _is_port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except:
            return False
