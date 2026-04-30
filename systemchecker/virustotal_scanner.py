"""
virustotal_scanner.py
VirusTotal API integration + basic local heuristic scanner.
Requires a free VirusTotal API key (set in settings or env VT_API_KEY).
"""
import hashlib
import os
import re
import json
import time
import struct
import platform
from pathlib import Path

_WIN = platform.system() == "Windows"

# ── VirusTotal API ──

def _get_api_key():
    """Get VT API key from env or settings."""
    key = os.getenv("VT_API_KEY", "")
    if not key:
        try:
            from settings import get_setting
            key = get_setting("security.vt_api_key", "")
        except:
            pass
    return key

def _vt_request(method, endpoint, **kwargs):
    """Make a request to the VirusTotal API v3."""
    import requests
    key = _get_api_key()
    if not key:
        return {"error": "API Key de VirusTotal no configurada. Ve a Settings > Seguridad."}
    
    url = f"https://www.virustotal.com/api/v3/{endpoint}"
    headers = {"x-apikey": key}
    
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=30, **kwargs)
        elif method == "POST":
            r = requests.post(url, headers=headers, timeout=60, **kwargs)
        else:
            return {"error": f"Método no soportado: {method}"}
        
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 401:
            return {"error": "API Key inválida."}
        elif r.status_code == 429:
            return {"error": "Límite de API alcanzado (4 req/min en plan gratuito). Espera un momento."}
        else:
            return {"error": f"Error HTTP {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"error": f"Error de conexión: {str(e)}"}

def scan_file_vt(file_path: str):
    """Upload and scan a file on VirusTotal."""
    path = Path(file_path)
    if not path.exists():
        return {"error": f"Archivo no encontrado: {file_path}"}
    
    size_mb = path.stat().st_size / 1e6
    if size_mb > 32:
        return {"error": f"Archivo demasiado grande ({size_mb:.1f}MB). Máximo 32MB en API gratuita."}
    
    # First check by hash
    file_hash = _sha256(file_path)
    hash_result = lookup_hash_vt(file_hash)
    if "data" in hash_result:
        return _parse_vt_result(hash_result, file_path, file_hash)
    
    # Upload if not found
    import requests
    key = _get_api_key()
    if not key:
        return {"error": "API Key de VirusTotal no configurada."}
    
    with open(file_path, "rb") as f:
        r = requests.post(
            "https://www.virustotal.com/api/v3/files",
            headers={"x-apikey": key},
            files={"file": (path.name, f)},
            timeout=120
        )
    
    if r.status_code == 200:
        data = r.json()
        analysis_id = data.get("data", {}).get("id", "")
        return {
            "status": "uploaded",
            "analysis_id": analysis_id,
            "file": path.name,
            "hash": file_hash,
            "message": "Archivo subido. Usa el analysis_id para verificar resultados en unos minutos.",
        }
    return {"error": f"Error al subir: {r.status_code} {r.text[:200]}"}

def lookup_hash_vt(file_hash: str):
    """Look up a file hash on VirusTotal."""
    return _vt_request("GET", f"files/{file_hash}")

def scan_url_vt(url: str):
    """Scan a URL on VirusTotal."""
    import base64
    url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
    
    # First try to get existing result
    result = _vt_request("GET", f"urls/{url_id}")
    if "data" in result:
        return _parse_vt_url_result(result, url)
    
    # Submit for scanning
    result = _vt_request("POST", "urls", data={"url": url})
    if "data" in result:
        return {
            "status": "submitted",
            "url": url,
            "analysis_id": result["data"].get("id", ""),
            "message": "URL enviada para análisis. Resultados disponibles en segundos.",
        }
    return result

def get_analysis_result(analysis_id: str):
    """Get the result of a pending analysis."""
    return _vt_request("GET", f"analyses/{analysis_id}")

def _parse_vt_result(data, file_path, file_hash):
    """Parse VT file scan result into readable format."""
    attrs = data.get("data", {}).get("attributes", {})
    stats = attrs.get("last_analysis_stats", {})
    
    malicious = stats.get("malicious", 0)
    suspicious = stats.get("suspicious", 0)
    harmless = stats.get("harmless", 0)
    undetected = stats.get("undetected", 0)
    total = malicious + suspicious + harmless + undetected
    
    if malicious > 0:
        threat_level = "PELIGROSO" if malicious > 5 else "SOSPECHOSO"
    elif suspicious > 0:
        threat_level = "PRECAUCIÓN"
    else:
        threat_level = "LIMPIO"
    
    return {
        "status": "found",
        "file": os.path.basename(file_path),
        "hash": file_hash,
        "threat_level": threat_level,
        "detections": f"{malicious}/{total}",
        "malicious": malicious,
        "suspicious": suspicious,
        "harmless": harmless,
        "names": attrs.get("meaningful_name", ""),
        "type": attrs.get("type_description", ""),
        "size": attrs.get("size", 0),
        "vt_link": f"https://www.virustotal.com/gui/file/{file_hash}",
    }

def _parse_vt_url_result(data, url):
    """Parse VT URL scan result."""
    attrs = data.get("data", {}).get("attributes", {})
    stats = attrs.get("last_analysis_stats", {})
    
    malicious = stats.get("malicious", 0)
    total = sum(stats.values())
    
    return {
        "status": "found",
        "url": url,
        "threat_level": "PELIGROSO" if malicious > 3 else ("SOSPECHOSO" if malicious > 0 else "LIMPIO"),
        "detections": f"{malicious}/{total}",
        "malicious": malicious,
        "categories": attrs.get("categories", {}),
    }

# ── Basic Local Heuristic Scanner ──

SUSPICIOUS_EXTENSIONS = {
    ".exe", ".scr", ".bat", ".cmd", ".vbs", ".vbe", ".js",
    ".wsf", ".wsh", ".ps1", ".msi", ".pif", ".com", ".hta",
}

SUSPICIOUS_STRINGS = [
    b"CreateRemoteThread", b"VirtualAllocEx", b"WriteProcessMemory",
    b"NtCreateThreadEx", b"RtlCreateUserThread",
    b"keylogger", b"Mimikatz", b"inject", b"ransom",
    b"WScript.Shell", b"powershell -enc", b"powershell -e ",
    b"cmd /c del", b"net user add", b"reg add",
    b"FromBase64String", b"DownloadString", b"IEX(",
    b"cryptocurrency", b"mining", b"xmrig",
]

def local_scan_file(file_path: str):
    """
    Basic heuristic scan: checks for suspicious strings, PE anomalies.
    NOT a replacement for real antivirus, but catches common red flags.
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": "Archivo no encontrado."}
    
    result = {
        "file": path.name,
        "path": str(path),
        "size_mb": round(path.stat().st_size / 1e6, 2),
        "extension": path.suffix.lower(),
        "flags": [],
        "risk_score": 0,
        "hash_sha256": _sha256(file_path),
    }
    
    # Check extension
    if path.suffix.lower() in SUSPICIOUS_EXTENSIONS:
        result["flags"].append(f"Extensión ejecutable: {path.suffix}")
        result["risk_score"] += 10
    
    # Read file content (max 5MB)
    try:
        with open(path, "rb") as f:
            content = f.read(5 * 1024 * 1024)
    except Exception as e:
        result["flags"].append(f"No se pudo leer: {e}")
        return result
    
    # Check for suspicious strings
    for pattern in SUSPICIOUS_STRINGS:
        if pattern.lower() in content.lower():
            result["flags"].append(f"Cadena sospechosa detectada: {pattern.decode(errors='ignore')}")
            result["risk_score"] += 15
    
    # PE header check
    if content[:2] == b"MZ":
        result["flags"].append("Archivo PE (ejecutable Windows)")
        result["risk_score"] += 5
        
        # Check for packed/encrypted sections
        if b"UPX" in content[:2000]:
            result["flags"].append("Empaquetado con UPX (posible ofuscación)")
            result["risk_score"] += 20
        if b"Themida" in content or b"VMProtect" in content:
            result["flags"].append("Protector de software detectado (anti-análisis)")
            result["risk_score"] += 30
    
    # Determine threat level
    if result["risk_score"] >= 50:
        result["threat_level"] = "ALTO"
    elif result["risk_score"] >= 25:
        result["threat_level"] = "MEDIO"
    elif result["risk_score"] >= 10:
        result["threat_level"] = "BAJO"
    else:
        result["threat_level"] = "LIMPIO"
    
    return result

def local_scan_directory(dir_path: str, max_files: int = 200):
    """Scan a directory for suspicious files."""
    path = Path(dir_path)
    if not path.exists():
        return {"error": "Directorio no encontrado."}
    
    results = []
    scanned = 0
    flagged = 0
    
    for item in path.rglob("*"):
        if item.is_file() and item.suffix.lower() in SUSPICIOUS_EXTENSIONS:
            if scanned >= max_files:
                break
            r = local_scan_file(str(item))
            if r.get("risk_score", 0) > 0:
                results.append(r)
                flagged += 1
            scanned += 1
    
    return {
        "directory": str(path),
        "scanned": scanned,
        "flagged": flagged,
        "results": results,
    }

def _sha256(file_path: str):
    """Calculate SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
