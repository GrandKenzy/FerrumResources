"""
admin_helper.py
Allows the Flask app to restart itself with Administrator privileges.
Uses Windows UAC elevation via ShellExecute.
"""
import sys
import os
import platform
import ctypes
import subprocess

def is_admin():
    """Check if the current process has Administrator privileges."""
    if platform.system() != "Windows":
        return os.geteuid() == 0
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def restart_as_admin():
    """
    Restart the current Python script with Administrator privileges.
    On Windows uses UAC elevation (ShellExecute with 'runas').
    Returns dict with status.
    """
    if is_admin():
        return {"ok": True, "message": "Ya estás ejecutando como Administrador."}

    system = platform.system()

    if system == "Windows":
        try:
            # Get the python executable and the main script
            python_exe = sys.executable
            script = os.path.abspath(sys.argv[0])
            args = " ".join(sys.argv[1:])
            params = f'"{script}" {args}'

            # ShellExecute with 'runas' triggers UAC
            ret = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", python_exe, params, None, 1
            )
            # ShellExecute returns > 32 on success
            if ret > 32:
                # Exit this non-elevated instance
                os._exit(0)
            else:
                return {"ok": False, "message": f"UAC denegado o error (código {ret})."}
        except Exception as e:
            return {"ok": False, "message": f"Error al elevar: {str(e)}"}
    else:
        # Linux/macOS: try pkexec or sudo
        try:
            python_exe = sys.executable
            script = os.path.abspath(sys.argv[0])
            args = sys.argv[1:]
            cmd = ["pkexec", python_exe, script] + args
            subprocess.Popen(cmd)
            os._exit(0)
        except Exception as e:
            return {"ok": False, "message": f"No se pudo elevar: {str(e)}"}

    return {"ok": False, "message": "Plataforma no soportada para elevación."}
