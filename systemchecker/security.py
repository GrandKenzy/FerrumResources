import json
import re
import secrets
from flask import session, request, abort
from config import SECURITY_RULES_FILE, ENABLE_POWER_ACTIONS_ENV
from settings import get_setting

DEFAULT_RULES = {
    "version": 1,
    "blacklist_exact": [
        "xmrig.exe", "xmrig", "xmr-stak.exe", "xmr-stak",
        "nanominer.exe", "nanominer", "mimikatz.exe", "mimikatz",
        "njrat.exe", "quasar.exe", "darkcomet.exe", "remcos.exe"
    ],
    "blacklist_contains": [
        "miner", "cryptonight", "monero", "keylogger", "stealer",
        "rat", "backdoor", "botnet", "coinhive"
    ],
    "suspicious_cmdline_patterns": [
        "(?i)-enc\\s+[a-z0-9+/=]{20,}",
        "(?i)encodedcommand",
        "(?i)invoke-webrequest\\s+http",
        "(?i)curl\\s+http.*\\|\\s*(sh|bash|powershell)",
        "(?i)wget\\s+http.*\\|\\s*(sh|bash|powershell)",
        "(?i)frombase64string",
        "(?i)\\bnohup\\b.*\\b/tmp/",
        "(?i)python\\s+-c\\s+.*socket",
        "(?i)powershell.*downloadstring",
        "(?i)reg\\s+add.*run"
    ],
    "known_good_names": [
        "system", "idle", "registry", "smss.exe", "csrss.exe", "wininit.exe",
        "services.exe", "lsass.exe", "svchost.exe", "explorer.exe", "dwm.exe",
        "taskmgr.exe", "conhost.exe", "fontdrvhost.exe", "searchindexer.exe",
        "python.exe", "python", "python3", "flask", "code.exe", "chrome.exe",
        "msedge.exe", "firefox.exe", "bash", "zsh", "sh", "systemd",
        "launchd", "kernel_task", "finder", "dock", "windowserver"
    ],
    "suspicious_paths": [
        "\\\\appdata\\\\local\\\\temp\\\\",
        "\\\\windows\\\\temp\\\\",
        "/tmp/",
        "/var/tmp/",
        "/dev/shm/"
    ],
    "protected_names": [
        "system", "idle", "registry", "smss.exe", "csrss.exe", "wininit.exe",
        "services.exe", "lsass.exe", "svchost.exe", "systemd", "launchd",
        "kernel_task"
    ]
}

def load_security_rules():
    if not SECURITY_RULES_FILE.exists():
        save_security_rules(DEFAULT_RULES)
        return DEFAULT_RULES
    try:
        with open(SECURITY_RULES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return DEFAULT_RULES

def save_security_rules(rules):
    with open(SECURITY_RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2, ensure_ascii=False)

def is_power_actions_enabled():
    """
    Checks if power actions (destructive/privileged) are enabled.
    Priority: 
    1. Environment Variable ENABLE_POWER_ACTIONS=true (Hard enable)
    2. Setting 'security.enable_power_actions' in settings.json
    """
    if ENABLE_POWER_ACTIONS_ENV:
        return True
    
    # Check if enabled via settings UI
    set_enabled = get_setting("security.enable_power_actions", False)
    if isinstance(set_enabled, str):
        return set_enabled.lower() == "true"
    return bool(set_enabled)

def require_csrf():
    token = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    if not token or token != session.get("csrf_token"):
        abort(403, "CSRF token invalid or missing")

def require_power(confirm_phrase=None):
    """
    Requires power mode to be enabled.
    If security.require_confirm_phrase is True, also checks
    that the request body contains the correct 'confirm' phrase.
    If require_confirm_phrase is False, no phrase is needed at all.
    """
    require_csrf()
    if not is_power_actions_enabled():
        abort(403, "Power actions are disabled (ENABLE_POWER_ACTIONS=false). Set the environment variable to enable.")

    # Read the setting; default True for safety
    req_confirm = get_setting("security.require_confirm_phrase", True)
    if isinstance(req_confirm, str):
        req_confirm = req_confirm.lower() == "true"

    # Only validate phrase when the setting is explicitly ON
    if req_confirm:
        data = request.get_json(silent=True) or {}
        if hasattr(request, 'form'):
            data = data or request.form
        provided = str(data.get("confirm", "")).strip().upper()
        expected = str(confirm_phrase or "CONFIRMAR").strip().upper()
        if provided != expected:
            abort(400, f"Debes confirmar la acción escribiendo: '{expected}'")

def init_session():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(24)
