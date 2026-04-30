import subprocess
import threading
import time
import os
from ports import find_free_port
from settings import get_setting

_managed_apps = {}
_apps_lock = threading.Lock()

def launch_app_protected(name, command, preferred_port=None):
    start = get_setting("ports.default_port_range_start", 3000)
    end = get_setting("ports.default_port_range_end", 9000)
    
    port = find_free_port(start, end, [preferred_port] if preferred_port else None)
    if not port:
        return None, "No free ports available"
    
    # Replace placeholder in command
    final_cmd = command.replace("{PORT}", str(port))
    
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["FLASK_RUN_PORT"] = str(port)
    env["SPV_ASSIGNED_PORT"] = str(port)
    
    try:
        # Launching as a subprocess
        proc = subprocess.Popen(
            final_cmd,
            shell=True,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        app_info = {
            "id": name,
            "pid": proc.pid,
            "port": port,
            "command": final_cmd,
            "status": "running",
            "started_at": time.time(),
            "url": f"http://127.0.0.1:{port}"
        }
        
        with _apps_lock:
            _managed_apps[name] = {
                "proc": proc,
                "info": app_info
            }
            
        return app_info, None
    except Exception as e:
        return None, str(e)

def stop_managed_app(name):
    with _apps_lock:
        if name in _managed_apps:
            app = _managed_apps[name]
            app["proc"].terminate()
            app["info"]["status"] = "stopped"
            return True
    return False

def list_managed_apps():
    with _apps_lock:
        # Refresh status
        for name, app in _managed_apps.items():
            if app["proc"].poll() is not None:
                app["info"]["status"] = "exited"
        return [app["info"] for app in _managed_apps.values()]
