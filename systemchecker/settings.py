import json
import logging
from config import SETTINGS_FILE

DEFAULT_SETTINGS = {
    "server": {
        "host": "127.0.0.1",
        "port": 5057,
        "refresh_interval_ms": 3000
    },
    "security": {
        "vt_api_key": "",
        "enable_power_actions": False,
        "enable_power_actions_ui_visible": True,
        "require_confirm_phrase": True,
        "session_timeout_minutes": 60,
        "allow_kill_process": True,
        "allow_disk_optimize": True,
        "allow_desktop_cleaner": True,
        "allow_port_terminate": True
    },
    "cleanup": {
        "clean_temp_min_age_hours": 24,
        "desktop_junk_min_age_days": 7,
        "max_cleanup_size_mb": 500,
        "quarantine_retention_days": 30,
        "auto_empty_quarantine": False
    },
    "processes": {
        "high_cpu_threshold": 70,
        "high_ram_threshold": 80,
        "high_disk_io_threshold_mb": 50,
        "high_connections_threshold": 50,
        "suspicious_score_threshold": 50,
        "sustained_usage_seconds": 15
    },
    "ports": {
        "default_port_range_start": 3000,
        "default_port_range_end": 9000,
        "preferred_ports": [3000, 5000, 5173, 8000, 8080],
        "auto_open_browser": True,
        "enable_os_notifications": True
    },
    "ui": {
        "theme": "light",
        "density": "comfortable",
        "auto_refresh": True,
        "show_advanced_metrics": True,
        "chart_history_seconds": 60
    }
}

_current_settings = {}

def load_settings():
    global _current_settings
    if not SETTINGS_FILE.exists():
        _current_settings = dict(DEFAULT_SETTINGS)
        save_settings()
        return _current_settings
    
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Simple merge to ensure all keys exist
            _current_settings = merge_defaults(DEFAULT_SETTINGS, data)
    except Exception as e:
        logging.error(f"Error loading settings: {e}")
        _current_settings = dict(DEFAULT_SETTINGS)
    
    return _current_settings

def merge_defaults(defaults, data):
    merged = dict(defaults)
    for k, v in data.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = merge_defaults(merged[k], v)
        else:
            merged[k] = v
    return merged

def save_settings(data=None):
    global _current_settings
    if data:
        _current_settings = data
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(_current_settings, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Error saving settings: {e}")

def get_setting(path, default=None):
    """Path can be 'server.port' etc."""
    parts = path.split(".")
    val = load_settings()
    for part in parts:
        if isinstance(val, dict) and part in val:
            val = val[part]
        else:
            return default
    return val

def set_setting(path, value):
    parts = path.split(".")
    data = load_settings()
    ref = data
    for part in parts[:-1]:
        if part not in ref:
            ref[part] = {}
        ref = ref[part]
    ref[parts[-1]] = value
    save_settings(data)

def reset_settings():
    global _current_settings
    _current_settings = dict(DEFAULT_SETTINGS)
    save_settings()
    return _current_settings

def validate_settings(data):
    # Simple validation could be added here
    return True
