import os
import sys
from pathlib import Path

def validate():
    print("=== System Process Viewer 2.0 Validation ===")
    
    files_to_check = [
        "app.py", "config.py", "settings.py", "security.py", "audit.py",
        "system_info.py", "processes.py", "alerts.py", "cleanup.py",
        "desktop_cleaner.py", "ports.py", "port_protect.py", "network_tools.py",
        "scheduler.py", "notifier.py", "reports.py"
    ]
    
    missing = []
    for f in files_to_check:
        if not Path(f).exists():
            missing.append(f)
            
    if missing:
        print(f"ERROR: Missing modules: {', '.join(missing)}")
    else:
        print("OK: All modules found.")
        
    # Check imports
    try:
        import flask
        import psutil
        import requests
        print("OK: Core dependencies (flask, psutil, requests) found.")
    except ImportError as e:
        print(f"ERROR: Missing dependency: {e}")
        
    # Test settings load
    try:
        import settings
        s = settings.load_settings()
        if s:
            print("OK: Settings module functional.")
    except Exception as e:
        print(f"ERROR: Settings load failed: {e}")
        
    # Test system info
    try:
        import system_info
        info = system_info.collect_system_info()
        if info:
            print(f"OK: System info collection functional (Platform: {info['platform']})")
    except Exception as e:
        print(f"ERROR: System info collection failed: {e}")

    print("=== Validation Complete ===")

if __name__ == "__main__":
    validate()
