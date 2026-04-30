import os
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from system_info import bytes_fmt

ARCHIVE_EXTS = {".zip", ".rar", ".7z", ".tar", ".gz", ".tgz", ".bz2", ".xz"}
INSTALLER_EXTS = {".msi", ".msix", ".dmg", ".pkg", ".deb", ".rpm", ".apk", ".exe"}
INSTALLER_WORDS = {"setup", "installer", "install", "instalador", "wizard", "bootstrap", "launcher", "update", "updater"}
PROTECTED_NAMES = {"desktop.ini", ".ds_store", "thumbs.db"}

def get_desktop_roots() -> List[Path]:
    home = Path.home()
    candidates = [home / "Desktop", home / "Escritorio"]
    one_drive = home / "OneDrive"
    if one_drive.exists():
        candidates.extend([one_drive / "Desktop", one_drive / "Escritorio"])
    
    roots = []
    for c in candidates:
        if c.exists() and c.is_dir():
            roots.append(c.resolve())
    return list(set(roots))

def scan_desktop_junk(min_age_days: int = 7) -> List[Dict[str, Any]]:
    roots = get_desktop_roots()
    items = []
    now = datetime.now().timestamp()
    cutoff = now - (min_age_days * 86400)
    
    for root in roots:
        try:
            for path in root.iterdir():
                if path.name.lower() in PROTECTED_NAMES: continue
                
                st = path.stat()
                is_file = path.is_file()
                
                # Basic classification
                kind = "unknown"
                score = 0
                reasons = []
                
                ext = path.suffix.lower()
                name_l = path.name.lower()
                
                if is_file:
                    if ext in ARCHIVE_EXTS:
                        kind = "archive"
                        score += 30
                        reasons.append("Archivo comprimido")
                    elif ext in INSTALLER_EXTS:
                        kind = "installer"
                        score += 50
                        reasons.append("Instalador detectable por extensión")
                    
                    if any(w in name_l for w in INSTALLER_WORDS):
                        score += 40
                        reasons.append("Nombre contiene palabras de instalador")
                        
                    if st.st_size == 0:
                        kind = "empty_file"
                        score += 100
                        reasons.append("Archivo vacío")
                else: # Directory
                    try:
                        if not any(path.iterdir()):
                            kind = "empty_folder"
                            score += 100
                            reasons.append("Carpeta vacía")
                    except:
                        continue
                
                if st.st_mtime < cutoff:
                    score += 20
                    reasons.append(f"Antigüedad > {min_age_days} días")
                
                if score > 0:
                    items.append({
                        "path": str(path),
                        "name": path.name,
                        "kind": kind,
                        "score": min(100, score),
                        "reasons": reasons,
                        "size": st.st_size if is_file else 0,
                        "size_fmt": bytes_fmt(st.st_size) if is_file else "0 B",
                        "modified": datetime.fromtimestamp(st.st_mtime).isoformat()
                    })
        except:
            continue
            
    return sorted(items, key=lambda x: x["score"], reverse=True)
