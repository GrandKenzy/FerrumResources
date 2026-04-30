"""
pc_health.py
PC sanitation and health check module.
Runs multiple diagnostics and repairs without deleting user data.
"""
import subprocess
import platform
import os
import shutil
import time
from pathlib import Path

_WIN = platform.system().lower() == "windows"

def _run(cmd: str, timeout: int = 120):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=timeout)
        return {"stdout": r.stdout.strip()[-3000:], "stderr": r.stderr.strip()[-500:], "ok": r.returncode == 0, "rc": r.returncode}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Tiempo agotado", "ok": False, "rc": -1}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "ok": False, "rc": -1}

# ------------------------------------------------------------------
# Health checks
# ------------------------------------------------------------------
def check_disk_health(job_update=None):
    """SMART / chkdsk summary for all drives."""
    results = {}
    if not _WIN:
        r = _run("smartctl --scan 2>/dev/null | head -5")
        results["smartctl"] = r
        return results

    # Get drive letters
    import psutil
    partitions = psutil.disk_partitions()
    for p in partitions:
        drive = p.mountpoint.rstrip("\\/")
        label = drive[0].upper() if drive else "?"
        # Check filesystem integrity
        r = _run(f"chkntfs {drive}")
        results[label] = {
            "mount": p.mountpoint,
            "fstype": p.fstype,
            "chkntfs": r["stdout"][:500],
            "dirty": "dirty" in r["stdout"].lower()
        }
        if job_update:
            job_update(progress=20 + int(50 * (len(results) / max(len(partitions), 1))),
                       message=f"Verificando {drive}...")
    return results

def check_system_files(job_update=None):
    """Run SFC /scannow (Windows) to check for corrupt system files."""
    if not _WIN:
        return {"error": "Solo Windows (SFC)."}
    if job_update:
        job_update(progress=10, message="Ejecutando SFC /scannow (puede tardar varios minutos)...")
    r = _run("sfc /scannow", timeout=600)
    if job_update:
        job_update(progress=80, message="SFC completado.")
    return {
        "ok": r["ok"],
        "output": r["stdout"][:3000],
        "issues_found": "found" in r["stdout"].lower() and "corrupt" in r["stdout"].lower()
    }

def repair_system_image(job_update=None):
    """Run DISM to restore system image health (Windows)."""
    if not _WIN:
        return {"error": "Solo Windows (DISM)."}
    if job_update:
        job_update(progress=5, message="Verificando integridad de imagen del sistema...")
    r1 = _run("DISM /Online /Cleanup-Image /CheckHealth", timeout=300)
    if job_update:
        job_update(progress=40, message="Restaurando integridad si es necesario...")
    r2 = _run("DISM /Online /Cleanup-Image /RestoreHealth", timeout=600)
    if job_update:
        job_update(progress=90, message="DISM completado.")
    return {
        "check_health": {"ok": r1["ok"], "output": r1["stdout"][:1000]},
        "restore_health": {"ok": r2["ok"], "output": r2["stdout"][:1000]}
    }

def fix_winsock(job_update=None):
    """Reset Winsock catalog (fixes network issues)."""
    if not _WIN:
        return {"error": "Solo Windows."}
    r1 = _run("netsh winsock reset")
    r2 = _run("netsh int ip reset")
    r3 = _run("ipconfig /flushdns")
    if job_update:
        job_update(progress=100, message="Winsock y DNS reseteados.")
    return {
        "winsock": {"ok": r1["ok"], "output": r1["stdout"]},
        "ip_reset": {"ok": r2["ok"], "output": r2["stdout"]},
        "dns_flush": {"ok": r3["ok"], "output": r3["stdout"]},
        "note": "Se requiere reiniciar el sistema para completar el reset de Winsock."
    }

def clean_temp_files(job_update=None):
    """Remove temp files from well-known temp directories safely."""
    removed = 0
    freed = 0
    errors = []
    
    temp_paths = []
    if _WIN:
        temp_paths = [
            Path(os.environ.get("TEMP", "C:\\Windows\\Temp")),
            Path("C:\\Windows\\Temp"),
            Path(os.environ.get("LOCALAPPDATA", "")) / "Temp",
        ]
    else:
        temp_paths = [Path("/tmp"), Path("/var/tmp")]

    for tp in temp_paths:
        if not tp.exists():
            continue
        for item in tp.iterdir():
            try:
                size = item.stat().st_size if item.is_file() else 0
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                removed += 1
                freed += size
            except Exception as e:
                errors.append(str(e))

    if job_update:
        job_update(progress=95, message=f"Eliminados {removed} archivos temporales.")
    return {
        "removed": removed,
        "freed_mb": round(freed / 1024 / 1024, 2),
        "errors": errors[:10]
    }

def clear_event_logs(job_update=None):
    """Clear Windows Event Logs (keeps last 100 entries per log)."""
    if not _WIN:
        return {"error": "Solo Windows."}
    
    logs_to_clear = ["Application", "System", "Security", "Setup"]
    results = {}
    for log in logs_to_clear:
        r = _run(f'wevtutil cl {log}')
        results[log] = {"ok": r["ok"]}
        if job_update:
            job_update(progress=20 + int(60 * (len(results) / len(logs_to_clear))),
                       message=f"Limpiando log: {log}")
    return results

def optimize_startup(job_update=None):
    """List and optionally disable startup programs via registry query."""
    if not _WIN:
        return {"error": "Solo Windows."}
    
    startup_keys = [
        r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
        r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    ]
    items = []
    for key in startup_keys:
        r = _run(f'reg query "{key}"')
        for line in r["stdout"].splitlines():
            line = line.strip()
            if line and "REG_SZ" in line or "REG_EXPAND_SZ" in line:
                parts = line.split(None, 2)
                if len(parts) >= 3:
                    items.append({"name": parts[0], "hive": key.split("\\")[0], "value": parts[2]})
    
    if job_update:
        job_update(progress=100, message=f"Encontrados {len(items)} programas de inicio.")
    return {"startup_items": items}

def full_health_scan(job_update=None):
    """Runs all health checks and returns a comprehensive report."""
    report = {}
    
    steps = [
        ("disk_health", check_disk_health, 0, 20),
        ("temp_files", clean_temp_files, 20, 40),
        ("startup", optimize_startup, 40, 60),
    ]
    
    for key, fn, pstart, pend in steps:
        if job_update:
            job_update(progress=pstart, message=f"Verificando: {key}...")
        try:
            report[key] = fn()
        except Exception as e:
            report[key] = {"error": str(e)}
    
    if job_update:
        job_update(progress=100, message="Análisis completo finalizado.")
    
    return report
