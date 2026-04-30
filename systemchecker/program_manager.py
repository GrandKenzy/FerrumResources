"""
program_manager.py
Lists installed programs and provides safe uninstallation.
Uses Windows Registry (Win32) or dpkg/rpm on Linux.
"""
import subprocess
import platform
import winreg
import re

_WIN = platform.system() == "Windows"

def list_installed_programs():
    """Returns a list of installed programs with name, version, publisher, uninstall command."""
    if not _WIN:
        return _list_linux_packages()
    
    programs = []
    seen = set()
    
    # Registry paths for installed software
    keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    
    for hive, path in keys:
        try:
            key = winreg.OpenKey(hive, path)
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    subkey = winreg.OpenKey(key, subkey_name)
                    
                    name = _reg_val(subkey, "DisplayName")
                    if not name or name in seen:
                        i += 1
                        continue
                    seen.add(name)
                    
                    programs.append({
                        "name": name,
                        "version": _reg_val(subkey, "DisplayVersion") or "—",
                        "publisher": _reg_val(subkey, "Publisher") or "—",
                        "install_date": _reg_val(subkey, "InstallDate") or "—",
                        "size_mb": _parse_size(_reg_val(subkey, "EstimatedSize")),
                        "uninstall_cmd": _reg_val(subkey, "UninstallString") or "",
                        "quiet_uninstall": _reg_val(subkey, "QuietUninstallString") or "",
                        "install_location": _reg_val(subkey, "InstallLocation") or "",
                        "reg_key": subkey_name,
                    })
                    winreg.CloseKey(subkey)
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except OSError:
            continue
    
    programs.sort(key=lambda x: x["name"].lower())
    return programs

def _reg_val(key, name):
    try:
        val, _ = winreg.QueryValueEx(key, name)
        return str(val).strip() if val else None
    except:
        return None

def _parse_size(val):
    if not val:
        return 0
    try:
        return round(int(val) / 1024, 1)  # KB to MB
    except:
        return 0

def uninstall_program(name: str, quiet: bool = True):
    """
    Uninstalls a program by finding its uninstall command in the registry.
    If quiet=True, tries the QuietUninstallString first.
    """
    if not _WIN:
        return {"error": "Solo disponible en Windows."}
    
    programs = list_installed_programs()
    match = None
    for p in programs:
        if p["name"].lower() == name.lower():
            match = p
            break
    
    if not match:
        # Fuzzy match
        for p in programs:
            if name.lower() in p["name"].lower():
                match = p
                break
    
    if not match:
        return {"error": f"Programa '{name}' no encontrado."}
    
    cmd = match.get("quiet_uninstall") if quiet else None
    if not cmd:
        cmd = match.get("uninstall_cmd")
    
    if not cmd:
        return {"error": f"No se encontró comando de desinstalación para '{match['name']}'."}
    
    # Some uninstall strings need msiexec parsing
    if cmd.lower().startswith("msiexec"):
        if "/i" in cmd.lower():
            cmd = cmd.replace("/I", "/X").replace("/i", "/X")
        if quiet and "/quiet" not in cmd.lower():
            cmd += " /quiet /norestart"
    
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        return {
            "ok": r.returncode == 0,
            "program": match["name"],
            "stdout": r.stdout[:1000],
            "stderr": r.stderr[:500],
            "returncode": r.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Tiempo de espera agotado (120s)."}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def search_programs(query: str):
    """Search installed programs by partial name."""
    programs = list_installed_programs()
    q = query.lower()
    return [p for p in programs if q in p["name"].lower() or q in (p["publisher"] or "").lower()]

def _list_linux_packages():
    """Fallback for Linux systems."""
    try:
        r = subprocess.run("dpkg --list 2>/dev/null || rpm -qa 2>/dev/null",
                           shell=True, capture_output=True, text=True, timeout=15)
        lines = r.stdout.strip().splitlines()
        packages = []
        for line in lines[:500]:
            parts = line.split()
            if len(parts) >= 3 and parts[0] == "ii":
                packages.append({
                    "name": parts[1],
                    "version": parts[2],
                    "publisher": "—",
                    "size_mb": 0,
                    "uninstall_cmd": f"apt remove {parts[1]}",
                })
        return packages
    except:
        return []
