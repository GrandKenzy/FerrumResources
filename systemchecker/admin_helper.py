"""
admin_helper.py
Robust privilege detection and elevation helpers for SPV.

This module is designed to work in all common launch modes:
- python app.py
- python -m app
- spv ui                # pip console_scripts launcher
- spv-ui                # direct UI console_scripts launcher
- editable installs
- normal wheel installs

On Windows it uses UAC through ShellExecuteW(..., "runas", ...).
On Linux/macOS it tries pkexec first and sudo as fallback.
"""
from __future__ import annotations

import ctypes
import os
import platform
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


WINDOWS_SHELLEXECUTE_ERRORS = {
    0: "El sistema no tiene memoria o recursos suficientes.",
    2: "Archivo no encontrado.",
    3: "Ruta no encontrada.",
    5: "Acceso denegado o UAC cancelado por el usuario.",
    8: "Memoria insuficiente.",
    26: "Error de uso compartido.",
    27: "La asociación de archivo está incompleta o es inválida.",
    28: "Tiempo de espera agotado.",
    29: "DDE falló.",
    30: "DDE ocupado.",
    31: "No hay aplicación asociada para abrir este archivo.",
    32: "DLL no encontrada.",
}


@dataclass(frozen=True)
class LaunchCommand:
    executable: str
    args: List[str]
    cwd: str
    mode: str

    def display(self) -> str:
        if platform.system() == "Windows":
            return " ".join([self.executable, subprocess.list2cmdline(self.args)]).strip()
        return " ".join([self.executable, *self.args]).strip()


def is_admin() -> bool:
    """Return True when the current process has administrator/root privileges."""
    system = platform.system()

    if system == "Windows":
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    geteuid = getattr(os, "geteuid", None)
    if geteuid is None:
        return False
    try:
        return geteuid() == 0
    except Exception:
        return False


def get_admin_status() -> dict:
    """Small status payload useful for Flask/CLI diagnostics."""
    return {
        "is_admin": is_admin(),
        "platform": platform.system(),
        "python": sys.executable,
        "argv": list(sys.argv),
        "cwd": os.getcwd(),
        "can_elevate": can_elevate(),
    }


def can_elevate() -> bool:
    """Return whether this platform has a known elevation path."""
    system = platform.system()
    if system == "Windows":
        return True
    return bool(shutil.which("pkexec") or shutil.which("sudo"))


def _as_existing_path(value: str) -> Optional[Path]:
    try:
        p = Path(value).expanduser()
        if p.exists():
            return p.resolve()
    except Exception:
        return None
    return None


def _is_python_file(path: Path) -> bool:
    return path.suffix.lower() in {".py", ".pyw"}


def _is_direct_executable(path: Path) -> bool:
    if platform.system() == "Windows":
        return path.suffix.lower() in {".exe", ".cmd", ".bat", ".com"}
    return os.access(str(path), os.X_OK) and not _is_python_file(path)


def _normalize_argv(argv: Optional[Iterable[str]] = None) -> List[str]:
    raw = list(argv if argv is not None else sys.argv)
    return raw if raw else [sys.executable]


def _fallback_spv_launcher_args(current_args: List[str]) -> Optional[LaunchCommand]:
    """
    Build a fallback command using the installed `spv` launcher.

    This is important when the current process was started by a pip-generated
    console_scripts executable and Python cannot safely re-run sys.argv[0] as a
    script. If no subcommand is present, default to `ui`.
    """
    spv = shutil.which("spv")
    if not spv:
        return None

    args = list(current_args)
    if not args:
        args = ["ui"]
    elif args[0].lower() not in {"ui", "disk", "health", "activation", "network", "os", "programs", "drivers", "scanner"}:
        # A web-triggered elevation should relaunch the UI, not an arbitrary unknown command.
        args = ["ui", *args]

    return LaunchCommand(
        executable=spv,
        args=args,
        cwd=os.getcwd(),
        mode="spv-launcher-fallback",
    )


def build_launch_command(argv: Optional[Iterable[str]] = None) -> LaunchCommand:
    """
    Resolve the correct command to relaunch the current SPV process elevated.

    The previous implementation always executed `python.exe "sys.argv[0]" ...`.
    That fails when `sys.argv[0]` is a pip-generated `spv.exe` launcher. This
    resolver detects that and runs the launcher directly instead.
    """
    raw_argv = _normalize_argv(argv)
    first = raw_argv[0]
    args = list(raw_argv[1:])
    cwd = os.getcwd()

    first_path = _as_existing_path(first)

    # Case 1: pip/venv executable launcher, e.g. ...\Scripts\spv.exe.
    if first_path and _is_direct_executable(first_path):
        return LaunchCommand(str(first_path), args, cwd, "direct-launcher")

    # Case 2: normal Python script, e.g. app.py or cli.py.
    if first_path and _is_python_file(first_path):
        return LaunchCommand(sys.executable, [str(first_path), *args], cwd, "python-script")

    # Case 3: module-like execution fallback. Prefer installed spv launcher.
    fallback = _fallback_spv_launcher_args(args)
    if fallback:
        return fallback

    # Case 4: last resort: start the Flask app module.
    return LaunchCommand(sys.executable, ["-m", "app", *args], cwd, "python-module-fallback")


def _schedule_exit(delay: float) -> None:
    def _exit() -> None:
        os._exit(0)

    timer = threading.Timer(max(0.0, delay), _exit)
    timer.daemon = True
    timer.start()


def restart_as_admin(
    argv: Optional[Iterable[str]] = None,
    *,
    exit_current: bool = True,
    exit_delay: float = 1.25,
) -> dict:
    """
    Relaunch SPV with elevated privileges.

    Returns a JSON-safe dict. When called from Flask, keep `exit_current=True` so
    the non-elevated server releases the port shortly after the response is sent.
    """
    if is_admin():
        return {
            "ok": True,
            "already_admin": True,
            "message": "SPV ya se está ejecutando como Administrador.",
            "status": get_admin_status(),
        }

    system = platform.system()
    command = build_launch_command(argv)

    if system == "Windows":
        try:
            params = subprocess.list2cmdline(command.args)
            ret = ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                command.executable,
                params,
                command.cwd,
                1,
            )
            ret = int(ret)

            if ret > 32:
                if exit_current:
                    _schedule_exit(exit_delay)
                return {
                    "ok": True,
                    "restarting": True,
                    "message": "Solicitud UAC enviada. La instancia actual se cerrará para liberar el puerto.",
                    "command": command.display(),
                    "mode": command.mode,
                }

            return {
                "ok": False,
                "message": WINDOWS_SHELLEXECUTE_ERRORS.get(ret, f"ShellExecuteW falló con código {ret}."),
                "code": ret,
                "command": command.display(),
                "mode": command.mode,
            }
        except Exception as exc:
            return {
                "ok": False,
                "message": f"Error al elevar privilegios: {type(exc).__name__}: {exc}",
                "command": command.display(),
                "mode": command.mode,
            }

    if system in {"Linux", "Darwin"}:
        launcher = shutil.which("pkexec") or shutil.which("sudo")
        if not launcher:
            return {
                "ok": False,
                "message": "No se encontró pkexec ni sudo para elevar privilegios.",
                "command": command.display(),
                "mode": command.mode,
            }

        try:
            subprocess.Popen([launcher, command.executable, *command.args], cwd=command.cwd)
            if exit_current:
                _schedule_exit(exit_delay)
            return {
                "ok": True,
                "restarting": True,
                "message": f"Elevación solicitada usando {Path(launcher).name}.",
                "command": command.display(),
                "mode": command.mode,
            }
        except Exception as exc:
            return {
                "ok": False,
                "message": f"No se pudo elevar privilegios: {type(exc).__name__}: {exc}",
                "command": command.display(),
                "mode": command.mode,
            }

    return {
        "ok": False,
        "message": f"Plataforma no soportada para elevación: {system}.",
        "command": command.display(),
        "mode": command.mode,
    }


def ensure_admin_or_relaunch(argv: Optional[Iterable[str]] = None) -> dict:
    """CLI helper: relaunch elevated when needed, otherwise report admin status."""
    if is_admin():
        return {"ok": True, "already_admin": True, "message": "Ya estás en modo Administrador."}
    return restart_as_admin(argv=argv, exit_current=True, exit_delay=0.25)
