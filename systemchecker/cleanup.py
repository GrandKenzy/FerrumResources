import os
import shutil
import time
import json
import uuid
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from config import QUARANTINE_DIR, APP_DIR
from system_info import bytes_fmt

def allowed_cleanup_roots():
    roots = [Path(tempfile.gettempdir()), APP_DIR / "cache"]
    user_home = Path.home()
    candidates = [
        user_home / ".cache",
        user_home / "AppData" / "Local" / "Temp",
    ]
    for c in candidates:
        if c.exists():
            roots.append(c)
    return [r.resolve() for r in roots if r.exists()]

def is_safe_path(path, roots):
    try:
        resolved = Path(path).resolve()
        for root in roots:
            if resolved == root or resolved.is_relative_to(root):
                return True
    except:
        pass
    return False

def scan_safe_cleanup(min_age_hours=24):
    roots = allowed_cleanup_roots()
    cutoff = time.time() - (min_age_hours * 3600)
    files = []
    total_size = 0
    
    for root in roots:
        try:
            for item in root.rglob("*"):
                if item.is_file():
                    try:
                        st = item.stat()
                        if st.st_mtime < cutoff:
                            files.append({
                                "path": str(item),
                                "size": st.st_size,
                                "size_fmt": bytes_fmt(st.st_size),
                                "modified": datetime.fromtimestamp(st.st_mtime).isoformat()
                            })
                            total_size += st.st_size
                    except:
                        continue
                if len(files) > 5000: break # Limit scan
        except:
            continue
            
    return {
        "files": files,
        "total_size": total_size,
        "total_size_fmt": bytes_fmt(total_size),
        "count": len(files)
    }

def quarantine_files(file_paths, reason="Cleanup"):
    manifest_id = uuid.uuid4().hex[:12]
    batch_dir = QUARANTINE_DIR / manifest_id
    batch_dir.mkdir(exist_ok=True)
    
    items = []
    success_count = 0
    reclaimed = 0
    
    for p in file_paths:
        path = Path(p)
        if not path.exists(): continue
        
        try:
            q_name = uuid.uuid4().hex
            q_path = batch_dir / q_name
            size = path.stat().st_size
            shutil.move(str(path), str(q_path))
            
            items.append({
                "original_path": str(path),
                "quarantine_path": str(q_path),
                "size": size,
                "reason": reason
            })
            success_count += 1
            reclaimed += size
        except Exception as e:
            print(f"Failed to quarantine {p}: {e}")
            
    manifest = {
        "id": manifest_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "items": items
    }
    
    with open(batch_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    return {
        "manifest_id": manifest_id,
        "success_count": success_count,
        "reclaimed_bytes": reclaimed,
        "reclaimed_fmt": bytes_fmt(reclaimed)
    }

def restore_quarantine(manifest_id):
    batch_dir = QUARANTINE_DIR / manifest_id
    manifest_path = batch_dir / "manifest.json"
    if not manifest_path.exists():
        return False
        
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    for item in manifest["items"]:
        try:
            orig = Path(item["original_path"])
            q_path = Path(item["quarantine_path"])
            if q_path.exists():
                orig.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(q_path), str(orig))
        except:
            continue
            
    shutil.rmtree(batch_dir)
    return True

def delete_permanently(manifest_id):
    # Security: Ensure manifest_id is a valid hex string to prevent path traversal
    if not all(c in "0123456789abcdef" for c in manifest_id):
        return False
        
    batch_dir = (QUARANTINE_DIR / manifest_id).resolve()
    
    # Security: Ensure batch_dir is indeed inside QUARANTINE_DIR
    if not str(batch_dir).startswith(str(QUARANTINE_DIR.resolve())):
        return False
        
    if batch_dir.exists() and batch_dir.is_dir():
        # Double check it contains a manifest.json
        if not (batch_dir / "manifest.json").exists():
            return False
            
        shutil.rmtree(batch_dir)
        return True
    return False

def list_quarantine():
    batches = []
    for d in QUARANTINE_DIR.iterdir():
        if d.is_dir() and (d / "manifest.json").exists():
            try:
                with open(d / "manifest.json", "r", encoding="utf-8") as f:
                    batches.append(json.load(f))
            except:
                continue
    return sorted(batches, key=lambda x: x["created_at"], reverse=True)
