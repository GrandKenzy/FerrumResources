"""
driver_manager.py
Windows driver management via pnputil and DISM.
"""
import subprocess
import platform
import re

_WIN = platform.system() == "Windows"

def _run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {"stdout": r.stdout.strip()[:4000], "stderr": r.stderr.strip()[:500], "ok": r.returncode == 0}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Timeout", "ok": False}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "ok": False}

def list_drivers():
    """List all third-party drivers using pnputil."""
    if not _WIN:
        return _linux_drivers()
    
    r = _run("pnputil /enum-drivers")
    if not r["ok"]:
        return []
    
    drivers = []
    current = {}
    for line in r["stdout"].splitlines():
        line = line.strip()
        if not line:
            if current.get("published_name"):
                drivers.append(current)
            current = {}
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip().lower().replace(" ", "_")
            val = val.strip()
            current[key] = val
    if current.get("published_name"):
        drivers.append(current)
    
    return drivers

def get_driver_info(published_name: str):
    """Get detailed info about a specific driver."""
    if not _WIN:
        return {"error": "Solo Windows."}
    r = _run(f'pnputil /enum-drivers /driver "{published_name}"')
    return {"raw": r["stdout"], "ok": r["ok"]}

def list_devices():
    """List all PnP devices and their driver status using PowerShell."""
    if not _WIN:
        return []
    r = _run('powershell -NoProfile -Command "Get-PnpDevice | Select-Object Status,Class,FriendlyName,InstanceId | ConvertTo-Json -Depth 2"', timeout=30)
    if not r["ok"]:
        return []
    try:
        import json
        devices = json.loads(r["stdout"])
        if isinstance(devices, dict):
            devices = [devices]
        return devices[:300]
    except:
        return []

def check_driver_updates():
    """Check for driver updates via Windows Update (basic)."""
    if not _WIN:
        return {"error": "Solo Windows."}
    r = _run('powershell -NoProfile -Command "Get-WindowsDriver -Online -All | Where-Object {$_.BootCritical -eq $false} | Select-Object Driver,ProviderName,Date,Version | ConvertTo-Json -Depth 2"', timeout=60)
    if not r["ok"]:
        return {"raw": r["stderr"], "ok": False}
    try:
        import json
        return {"drivers": json.loads(r["stdout"]), "ok": True}
    except:
        return {"raw": r["stdout"][:2000], "ok": True}

def install_driver(inf_path: str):
    """Install a driver from an .inf file."""
    if not _WIN:
        return {"error": "Solo Windows."}
    if not inf_path.lower().endswith(".inf"):
        return {"error": "Solo se permiten archivos .inf"}
    r = _run(f'pnputil /add-driver "{inf_path}" /install')
    return {"ok": r["ok"], "output": r["stdout"] or r["stderr"]}

def remove_driver(published_name: str, force: bool = False):
    """Remove a third-party driver package."""
    if not _WIN:
        return {"error": "Solo Windows."}
    cmd = f'pnputil /delete-driver "{published_name}"'
    if force:
        cmd += " /force"
    r = _run(cmd)
    return {"ok": r["ok"], "output": r["stdout"] or r["stderr"]}

def export_drivers(output_dir: str):
    """Export all third-party drivers to a folder (backup)."""
    if not _WIN:
        return {"error": "Solo Windows."}
    r = _run(f'powershell -NoProfile -Command "Export-WindowsDriver -Online -Destination \'{output_dir}\'"', timeout=120)
    return {"ok": r["ok"], "output": r["stdout"][:1000] or r["stderr"]}

def scan_hardware_changes():
    """Force Windows to re-scan for hardware changes."""
    if not _WIN:
        return {"error": "Solo Windows."}
    r = _run('pnputil /scan-devices')
    return {"ok": r["ok"], "output": r["stdout"] or r["stderr"]}

def _linux_drivers():
    """Basic Linux driver listing."""
    r = _run("lsmod 2>/dev/null | head -50")
    if not r["ok"]:
        return []
    drivers = []
    for line in r["stdout"].splitlines()[1:]:
        parts = line.split()
        if parts:
            drivers.append({"published_name": parts[0], "original_name": parts[0], "provider_name": "kernel"})
    return drivers
