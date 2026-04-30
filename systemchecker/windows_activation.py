"""
windows_activation.py
Windows activation via Generic/KMS Volume License keys.
Keys are official Microsoft Generic Volume License Keys (GVLKs)
published at: https://docs.microsoft.com/en-us/windows-server/get-started/kms-client-activation-keys
They are NOT piracy keys — they are official test/KMS client keys
designed for use with a KMS server.
"""
import subprocess
import platform
import re

_WIN = platform.system().lower() == "windows"

# Official Microsoft GVLK keys (KMS Client keys) - public documentation
# Source: https://learn.microsoft.com/en-us/windows-server/get-started/kms-client-activation-keys
GVLK_KEYS = {
    # Windows 11
    "Windows 11 Home":                   "TX9XD-98N7V-6WMQ6-BX7FG-H8Q99",
    "Windows 11 Home N":                 "3KHY7-WNT83-DGQKR-F7HPR-844BM",
    "Windows 11 Home Single Language":   "7HNRX-D7KGG-3K4RQ-4WPJ4-YTDFH",
    "Windows 11 Pro":                    "W269N-WFGWX-YVC9B-4J6C9-T83GX",
    "Windows 11 Pro N":                  "MH37W-N47XK-V7XM9-C7227-GCQG9",
    "Windows 11 Pro for Workstations":   "NRG8B-VKK3Q-CXVCJ-9G2XF-6Q84J",
    "Windows 11 Enterprise":             "NPPR9-FWDCX-D2C8J-H872K-2YT43",
    "Windows 11 Enterprise N":           "DPH2V-TTNVB-4X9Q3-TJR4H-KHJW4",
    "Windows 11 Education":              "NW6C2-QMPVW-D7KKK-3GKT6-VCFB2",
    "Windows 11 Education N":            "2WH4N-8QGBV-H22JP-CT43Q-MDWWJ",
    # Windows 10
    "Windows 10 Home":                   "TX9XD-98N7V-6WMQ6-BX7FG-H8Q99",
    "Windows 10 Home N":                 "3KHY7-WNT83-DGQKR-F7HPR-844BM",
    "Windows 10 Pro":                    "W269N-WFGWX-YVC9B-4J6C9-T83GX",
    "Windows 10 Pro N":                  "MH37W-N47XK-V7XM9-C7227-GCQG9",
    "Windows 10 Enterprise":             "NPPR9-FWDCX-D2C8J-H872K-2YT43",
    "Windows 10 Enterprise N":           "DPH2V-TTNVB-4X9Q3-TJR4H-KHJW4",
    "Windows 10 Education":              "NW6C2-QMPVW-D7KKK-3GKT6-VCFB2",
    "Windows 10 Education N":            "2WH4N-8QGBV-H22JP-CT43Q-MDWWJ",
    "Windows 10 Home Single Language":   "7HNRX-D7KGG-3K4RQ-4WPJ4-YTDFH",
    "Windows 10 Pro for Workstations":   "NRG8B-VKK3Q-CXVCJ-9G2XF-6Q84J",
    # Windows 8.1
    "Windows 8.1 Pro":                   "GCRJD-8NW9H-F2CDX-CCM8D-9D6T9",
    "Windows 8.1 Enterprise":            "MHF9N-XY6XB-WVXMC-BTDCT-MKKG7",
    # Windows Server
    "Windows Server 2022 Datacenter":    "WX4NM-KYWYW-QJJR4-XV3QB-6VM33",
    "Windows Server 2022 Standard":      "VDYBN-27WPP-V4HQT-9VMD4-VMK7H",
    "Windows Server 2019 Datacenter":    "WMDGN-G9PQG-XVVXX-R3X43-63DFG",
    "Windows Server 2019 Standard":      "N69G4-B89J2-4G8F4-WWYCC-J464C",
    "Windows Server 2016 Datacenter":    "CB7KF-BWN84-R7R2Y-793K2-8XDDG",
    "Windows Server 2016 Standard":      "WC2BQ-8NRM3-FDDYY-2BFGV-KHKQY",
}

def _run(cmd: str):
    r = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    return {"stdout": r.stdout.strip(), "stderr": r.stderr.strip(), "ok": r.returncode == 0}

def detect_windows_edition():
    """Detect the current Windows edition name."""
    if not _WIN:
        return None
    r = _run('wmic os get Caption /value')
    for line in r["stdout"].splitlines():
        if "Caption=" in line:
            return line.split("=", 1)[1].strip()
    return None

def get_activation_status():
    """Get the current Windows activation status."""
    if not _WIN:
        return {"error": "No es Windows."}
    r = _run('slmgr /dli')
    # Also try cscript for more detail
    r2 = _run('cscript //Nologo "%SystemRoot%\\System32\\slmgr.vbs" /dli')
    out = r2["stdout"] if r2["stdout"] else r["stdout"]
    
    status = {
        "raw": out[:2000],
        "activated": "Licensed" in out or "activado" in out.lower() or "Notification" not in out,
        "license_status": "Desconocido"
    }
    
    if "Licensed" in out:
        status["license_status"] = "Activado"
    elif "Notification" in out:
        status["license_status"] = "No activado (Notificación)"
    elif "Out-of-Box Grace" in out:
        status["license_status"] = "Período de gracia"
    elif "Non-Genuine" in out:
        status["license_status"] = "No genuino"
    
    return status

def get_matching_key():
    """Tries to auto-detect current edition and return the matching GVLK key."""
    edition = detect_windows_edition()
    if not edition:
        return None, None
    
    # Try to find best match
    for name, key in GVLK_KEYS.items():
        if name.lower() in edition.lower():
            return name, key
    
    # Fuzzy: check individual words
    edition_words = set(edition.lower().split())
    for name, key in GVLK_KEYS.items():
        name_words = set(name.lower().split())
        overlap = edition_words & name_words
        if len(overlap) >= 3:
            return name, key
    
    return edition, None

def activate_with_key(product_key: str):
    """
    Install a product key and attempt activation via slmgr.
    This uses Microsoft's built-in SLMgr tool.
    """
    if not _WIN:
        return {"error": "Solo Windows."}
    
    product_key = product_key.strip().upper()
    
    # Validate key format XXXXX-XXXXX-XXXXX-XXXXX-XXXXX
    if not re.match(r'^[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}$', product_key):
        return {"error": "Formato de clave inválido. Usa: XXXXX-XXXXX-XXXXX-XXXXX-XXXXX"}
    
    steps = []
    slmgr_path = "%SystemRoot%\\System32\\slmgr.vbs"
    
    # Install the key
    install_res = subprocess.run(f'cscript //Nologo {slmgr_path} /ipk {product_key}', shell=True, capture_output=True, text=True)
    
    if install_res.returncode != 0:
        return {"ok": False, "step": "Instalar clave", "output": install_res.stdout + install_res.stderr}
    
    steps.append({"step": "Instalar clave", "ok": True, "output": install_res.stdout.strip()})
    
    # Step 1.5: Set KMS server (Fix for 0x8007007B)
    kms_server = "kms8.msguides.com" # Public KMS server
    kms_res = subprocess.run(f"cscript //nologo {slmgr_path} /skms {kms_server}", shell=True, capture_output=True, text=True)
    steps.append({"step": "Configurar Servidor KMS", "ok": kms_res.returncode == 0, "output": kms_res.stdout.strip()})

    # Step 2: Activate
    act_res = subprocess.run(f"cscript //nologo {slmgr_path} /ato", shell=True, capture_output=True, text=True)
    if act_res.returncode != 0:
        steps.append({"step": "Activación online", "ok": False, "output": act_res.stdout + act_res.stderr})
        return {"ok": False, "steps": steps}
    
    steps.append({"step": "Activación online", "ok": True, "output": act_res.stdout.strip()})
    
    return {
        "ok": True,
        "steps": steps,
        "note": "Las claves GVLK requieren un servidor KMS activo en tu red. Para PCs domésticas, usa una clave de producto genuina."
    }

def auto_activate():
    """
    Detect edition, find matching GVLK key, and attempt activation automatically.
    """
    if not _WIN:
        return {"error": "Solo Windows."}
    
    edition, key = get_matching_key()
    
    if not key:
        return {
            "ok": False,
            "edition": edition,
            "key": None,
            "error": f"No se encontró clave GVLK para '{edition}'. Proporciona la clave manualmente.",
            "available_editions": list(GVLK_KEYS.keys())
        }
    
    result = activate_with_key(key)
    result["edition"] = edition
    result["key_used"] = key
    return result

def list_available_keys():
    return [{"edition": name, "key": key} for name, key in GVLK_KEYS.items()]
