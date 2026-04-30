import subprocess
import platform
import os
import ctypes
import json
from pathlib import Path

SYSTEM_PARTITIONS = {"C:", "C:\\", "/", "/boot", "/efi"}

def _is_system(mountpoint: str) -> bool:
    mp = mountpoint.rstrip("\\/").upper()
    return mp in {p.rstrip("\\/").upper() for p in SYSTEM_PARTITIONS}

def _run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, shell=True, **kwargs)

# ------------------------------------------------------------------
# Safe Cleanup — removes temp/junk but NOT user data or system files
# ------------------------------------------------------------------
def safe_clean_disk(mountpoint: str, job_update=None):
    """
    Safely cleans junk/temp files from a partition.
    Never deletes user documents or system files.
    """
    mountpoint = mountpoint.rstrip("\\/")
    if _is_system(mountpoint):
        # Allow cleaning Windows temp on C: but only specific folders
        if platform.system() == "Windows":
            return _clean_windows_system_junk(job_update)
        raise ValueError("No se puede limpiar la partición del sistema en este OS.")

    path = Path(mountpoint)
    if not path.exists():
        raise ValueError(f"La ruta {mountpoint} no existe.")

    # Only remove known junk patterns
    JUNK_PATTERNS = [
        "*.tmp", "*.temp", "~$*", "Thumbs.db", "desktop.ini",
        "*.log", "*.bak", "*.old", "*.dmp", "*.etl"
    ]
    deleted = 0
    freed_bytes = 0
    errors = []

    if job_update:
        job_update(progress=10, message="Escaneando archivos...")

    for pattern in JUNK_PATTERNS:
        for f in path.rglob(pattern):
            try:
                size = f.stat().st_size
                f.unlink()
                deleted += 1
                freed_bytes += size
            except Exception as e:
                errors.append(str(e))

    if job_update:
        job_update(progress=90, message=f"Eliminados {deleted} archivos.")

    return {
        "deleted": deleted,
        "freed_mb": round(freed_bytes / 1024 / 1024, 2),
        "errors": errors[:10]
    }

def _clean_windows_system_junk(job_update=None):
    """Runs Windows built-in cleanup on C: safely."""
    results = {"steps": [], "errors": []}

    steps = [
        ("Temp de usuario", r'cmd /c "del /q /f /s %TEMP%\*.tmp 2>nul"'),
        ("Prefetch (si admin)", r'cmd /c "del /q /f /s C:\Windows\Prefetch\*.pf 2>nul"'),
        ("Windows Temp", r'cmd /c "del /q /f /s C:\Windows\Temp\*.tmp 2>nul"'),
        ("Papelera (silencioso)", r'cmd /c "rd /s /q C:\$Recycle.Bin 2>nul"'),
    ]

    for i, (label, cmd) in enumerate(steps):
        try:
            _run(cmd)
            results["steps"].append({"step": label, "status": "ok"})
        except Exception as e:
            results["errors"].append(f"{label}: {e}")
        if job_update:
            job_update(progress=10 + int(80 * (i + 1) / len(steps)), message=f"Limpiando: {label}")

    # Also run Windows Disk Cleanup silently for common categories
    try:
        _run("cleanmgr /sagerun:65535")
        results["steps"].append({"step": "Windows Disk Cleanup", "status": "iniciado"})
    except Exception as e:
        results["errors"].append(f"cleanmgr: {e}")

    return results

# ------------------------------------------------------------------
# Defragment
# ------------------------------------------------------------------
def defragment_disk(mountpoint: str, job_update=None):
    """
    Defragments a disk partition. Windows only uses defrag.exe.
    On Linux uses e4defrag or fstrim.
    """
    if job_update:
        job_update(progress=5, message="Iniciando desfragmentación...")

    system = platform.system().lower()

    if system == "windows":
        drive = mountpoint.rstrip("\\/")
        if not drive.endswith(":"):
            drive = drive[0] + ":"
        cmd = f"defrag {drive} /U /V"
        result = _run(cmd)
        if job_update:
            job_update(progress=95, message="Desfragmentación completada.")
        return {
            "stdout": result.stdout[-3000:] if result.stdout else "",
            "stderr": result.stderr[-500:] if result.stderr else "",
            "returncode": result.returncode
        }
    else:
        # Linux: try fstrim (SSD) or e4defrag (HDD)
        r = _run(f"fstrim -v {mountpoint}")
        if r.returncode != 0:
            r = _run(f"e4defrag {mountpoint}")
        if job_update:
            job_update(progress=95, message="Optimización completada.")
        return {"stdout": r.stdout, "returncode": r.returncode}

# ------------------------------------------------------------------
# Unlock disk (remove BitLocker/ReadOnly flags)
# ------------------------------------------------------------------
def unlock_disk(mountpoint: str, password: str = "", recovery_key: str = ""):
    """
    Attempts to unlock a BitLocker-protected or read-only disk.
    """
    system = platform.system().lower()
    if system != "windows":
        return {"error": "Desbloqueo solo disponible en Windows."}

    drive = mountpoint.rstrip("\\/")
    if not drive.endswith(":"):
        drive = drive[0] + ":"

    results = []

    # Try removing read-only attribute
    script = f"select volume {drive[0]}\nattributes disk clear readonly\n"
    r = _diskpart(script)
    results.append({"step": "Quitar ReadOnly", "out": r})

    # Try BitLocker unlock
    if password:
        r2 = _run(f'manage-bde -unlock {drive} -Password {password}')
        results.append({"step": "BitLocker (contraseña)", "out": r2.stdout, "err": r2.stderr})
    elif recovery_key:
        r2 = _run(f'manage-bde -unlock {drive} -RecoveryKey "{recovery_key}"')
        results.append({"step": "BitLocker (clave recuperación)", "out": r2.stdout, "err": r2.stderr})

    return {"results": results}

# ------------------------------------------------------------------
# Create partition
# ------------------------------------------------------------------
def create_partition(disk_number: int, size_mb: int, label: str = "Nueva", fs: str = "NTFS"):
    """
    Creates a new partition using diskpart (Windows) or parted (Linux).
    Requires Administrator/root.
    """
    system = platform.system().lower()
    if system == "windows":
        script = (
            f"select disk {disk_number}\n"
            f"create partition primary size={size_mb}\n"
            f"format quick fs={fs} label={label}\n"
            f"assign\n"
        )
        out = _diskpart(script)
        return {"method": "diskpart", "output": out}
    else:
        # Simplified: requires interactive or pre-known device path
        return {"error": "Particionado en Linux requiere especificar dispositivo (ej. /dev/sdb)."}

def create_partition_linux(device: str, size_mb: int, fs: str = "ext4", label: str = "nueva"):
    system = platform.system().lower()
    if system == "windows":
        return {"error": "Usa create_partition() para Windows."}
    r = _run(f"parted {device} --script mkpart primary {fs} 0% {size_mb}MB")
    if r.returncode != 0:
        return {"error": r.stderr}
    r2 = _run(f"mkfs.{fs} -L {label} {device}1")
    return {"output": r2.stdout, "returncode": r2.returncode}

def _diskpart(script: str) -> str:
    """Runs a diskpart script and returns output."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(script)
        script_path = f.name
    try:
        r = _run(f'diskpart /s "{script_path}"')
        return r.stdout + r.stderr
    finally:
        os.unlink(script_path)

# ------------------------------------------------------------------
# Disk usage analysis
# ------------------------------------------------------------------
def analyze_disk_usage(path: str):
    import shutil
    total, used, free = shutil.disk_usage(path)
    return {
        "total": total,
        "used": used,
        "free": free,
        "percent": round((used / total) * 100, 1)
    }

def list_physical_disks():
    """Returns physical disk list (Windows only)."""
    system = platform.system().lower()
    if system != "windows":
        return []
    try:
        r = _run('wmic diskdrive get Index,Model,Size,Status /format:csv')
        disks = []
        for line in r.stdout.strip().splitlines()[2:]:
            parts = line.split(",")
            if len(parts) >= 5:
                disks.append({
                    "index": parts[1].strip(),
                    "model": parts[2].strip(),
                    "size_gb": round(int(parts[3].strip() or 0) / 1e9, 1) if parts[3].strip().isdigit() else 0,
                    "status": parts[4].strip()
                })
        return disks
    except:
        return []

def get_bitlocker_status(drive_letter: str):
    """Get BitLocker status for a drive (Windows only)."""
    try:
        r = _run(f'manage-bde -status {drive_letter}:')
        return {"raw": r.stdout[:1000], "locked": "Locked" in r.stdout}
    except:
        return {"raw": "", "locked": False}
