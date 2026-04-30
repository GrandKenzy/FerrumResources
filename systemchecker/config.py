import os
import secrets
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Default Environment Variables
HOST = os.getenv("SPV_HOST", "127.0.0.1")
PORT = int(os.getenv("SPV_PORT", "5057"))
# Power actions can be enabled via env or later via settings (if permitted by env)
ENABLE_POWER_ACTIONS_ENV = os.getenv("ENABLE_POWER_ACTIONS", "false").lower() in {"1", "true", "yes", "on"}
SECRET_KEY = os.getenv("SPV_SECRET_KEY") or secrets.token_hex(32)
APP_NAME = "System Process Viewer 2.0"

# Paths to data files
SETTINGS_FILE = DATA_DIR / "settings.json"
SECURITY_RULES_FILE = DATA_DIR / "security_rules.json"
SCHEDULER_FILE = DATA_DIR / "scheduler.json"
JOBS_FILE = DATA_DIR / "jobs.jsonl"
AUDIT_FILE = DATA_DIR / "audit.jsonl"
ALERTS_FILE = DATA_DIR / "alerts.jsonl"
NOTIFICATIONS_FILE = DATA_DIR / "notifications.jsonl"
QUARANTINE_DIR = DATA_DIR / "quarantine"
QUARANTINE_DIR.mkdir(exist_ok=True)
REPORTS_DIR = DATA_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
