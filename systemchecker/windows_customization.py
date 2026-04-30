"""
windows_customization.py
Handles changing wallpapers, checking for Windows updates (10 to 11), and basic system configs.
"""
import ctypes
import os
import platform
import subprocess

_WIN = platform.system().lower() == "windows"

def change_wallpaper(image_path: str):
    """Change the desktop wallpaper on Windows."""
    if not _WIN:
        return {"ok": False, "error": "Solo soportado en Windows."}
    
    if not os.path.exists(image_path):
        return {"ok": False, "error": f"La imagen {image_path} no existe."}
    
    try:
        # SPI_SETDESKWALLPAPER = 20, SPIF_UPDATEINIFILE = 1, SPIF_SENDWININICHANGE = 2
        result = ctypes.windll.user32.SystemParametersInfoW(20, 0, image_path, 3)
        if result:
            return {"ok": True, "message": "Fondo de pantalla actualizado correctamente."}
        else:
            return {"ok": False, "error": "Fallo al cambiar el fondo de pantalla (API retornó 0)."}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def change_password(username: str, new_password: str):
    """Change user password. Requires Admin privileges."""
    if not _WIN:
        return {"ok": False, "error": "Solo soportado en Windows."}
    
    # Simple net user command
    # Note: If password has spaces, quote it. Wait, subprocess handles it if we pass it as a string without shell, but with shell we need quotes.
    safe_user = f'"{username}"'
    safe_pass = f'"{new_password}"'
    
    cmd = f"net user {safe_user} {safe_pass}"
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if r.returncode == 0:
        return {"ok": True, "message": f"Contraseña actualizada para {username}."}
    else:
        return {"ok": False, "error": r.stderr.strip() or r.stdout.strip()}

def check_win11_upgrade():
    """
    Check if we are on Windows 10 and provide link/status for Windows 11 upgrade.
    """
    if not _WIN:
        return {"ok": False, "error": "Solo soportado en Windows."}
    
    import platform
    release = platform.release()
    if release == "10":
        # Windows 11 also returns "10" in python's platform module sometimes, let's verify build number
        version = platform.version()
        try:
            build = int(version.split('.')[2])
            if build >= 22000:
                return {"is_win11": True, "message": "Ya estás en Windows 11."}
        except:
            pass
            
        return {
            "is_win11": False,
            "message": "Estás en Windows 10. Puedes actualizar a Windows 11 usando el Asistente de Instalación.",
            "assistant_url": "https://go.microsoft.com/fwlink/?linkid=2156295"
        }
    
    return {"is_win11": release == "11", "message": f"Windows versión detectada: {release}"}

def trigger_windows_update():
    """Launch Windows Update settings."""
    if not _WIN:
        return {"ok": False}
    subprocess.run("start ms-settings:windowsupdate-action", shell=True)
    return {"ok": True, "message": "Abriendo Windows Update..."}
