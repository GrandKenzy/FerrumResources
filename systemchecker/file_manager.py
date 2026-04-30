import os
import shutil
import zipfile
import subprocess
from pathlib import Path

def list_directory(path: str):
    p = Path(path)
    if not p.exists() or not p.is_dir():
        return {"error": "Directorio no encontrado."}
    
    items = []
    try:
        for entry in p.iterdir():
            try:
                stat = entry.stat()
                items.append({
                    "name": entry.name,
                    "path": str(entry.resolve()),
                    "is_dir": entry.is_dir(),
                    "size": stat.st_size if not entry.is_dir() else 0,
                    "modified": stat.st_mtime
                })
            except Exception:
                pass
    except Exception as e:
        return {"error": str(e)}
    
    items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    return {"path": str(p.resolve()), "items": items}

def move_item(src: str, dst_dir: str):
    if not os.path.exists(src):
        return {"error": "Origen no encontrado."}
    if not os.path.exists(dst_dir):
        return {"error": "Destino no encontrado."}
    try:
        shutil.move(src, os.path.join(dst_dir, os.path.basename(src)))
        return {"ok": True}
    except Exception as e:
        return {"error": str(e)}

def extract_archive(archive_path: str, dest_dir: str = None):
    """
    Extract zip natively.
    For .rar and .7z, attempts to find 7z.exe or WinRAR.exe and uses them.
    """
    p = Path(archive_path)
    if not p.exists() or not p.is_file():
        return {"error": "Archivo comprimido no encontrado."}
    
    if not dest_dir:
        dest_dir = str(p.parent / p.stem)
    
    os.makedirs(dest_dir, exist_ok=True)
    ext = p.suffix.lower()
    
    if ext == ".zip":
        try:
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(dest_dir)
            return {"ok": True, "dest": dest_dir}
        except Exception as e:
            return {"error": str(e)}
            
    elif ext in [".7z", ".rar", ".tar", ".gz"]:
        # Look for 7z.exe
        seven_z = r"C:\Program Files\7-Zip\7z.exe"
        winrar = r"C:\Program Files\WinRAR\WinRAR.exe"
        
        if os.path.exists(seven_z):
            cmd = f'"{seven_z}" x "{archive_path}" -o"{dest_dir}" -y'
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if r.returncode == 0:
                return {"ok": True, "dest": dest_dir}
            return {"error": r.stderr or r.stdout}
            
        elif os.path.exists(winrar) and ext == ".rar":
            cmd = f'"{winrar}" x "{archive_path}" * "{dest_dir}\\"'
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if r.returncode == 0:
                return {"ok": True, "dest": dest_dir}
            return {"error": r.stderr or r.stdout}
            
        else:
            return {"error": f"No se encontró 7-Zip en {seven_z} para extraer {ext}."}
            
    return {"error": f"Formato no soportado: {ext}"}

def open_with(file_path: str, app_name: str = "7z"):
    if not os.path.exists(file_path):
        return {"error": "Archivo no encontrado"}
        
    app_map = {
        "7z": r"C:\Program Files\7-Zip\7zFM.exe",
        "winrar": r"C:\Program Files\WinRAR\WinRAR.exe",
        "notepad": "notepad.exe",
        "explorer": "explorer.exe"
    }
    
    exe = app_map.get(app_name.lower())
    if not exe:
        return {"error": "Aplicación no configurada."}
    
    try:
        if exe == "explorer.exe":
            # Select the file in explorer
            subprocess.Popen(f'explorer /select,"{file_path}"')
        else:
            subprocess.Popen([exe, file_path])
        return {"ok": True}
    except Exception as e:
        return {"error": str(e)}
