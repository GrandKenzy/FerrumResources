import json
import os
import platform
import subprocess
import uuid
from datetime import datetime, timezone
from config import NOTIFICATIONS_FILE
from settings import get_setting

def notify(title, message, url=None, severity="info"):
    entry = {
        "id": uuid.uuid4().hex[:12],
        "time": datetime.now(timezone.utc).isoformat(),
        "title": title,
        "message": message,
        "url": url,
        "severity": severity,
        "read": False
    }
    
    # Internal log
    try:
        with open(NOTIFICATIONS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except:
        pass
    
    # OS Notification
    if get_setting("ports.enable_os_notifications", True):
        try:
            _send_os_notification(title, message)
        except:
            pass
    
    return entry

def _send_os_notification(title, message):
    system = platform.system().lower()
    if system == "windows":
        # Simple PowerShell Toast
        # Note: This is a basic version, real toast needs a bit more script
        ps_script = f'[Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms"); $notify = New-Object System.Windows.Forms.NotifyIcon; $notify.Icon = [System.Drawing.SystemIcons]::Information; $notify.Visible = $true; $notify.ShowBalloonTip(5000, "{title}", "{message}", [System.Windows.Forms.ToolTipIcon]::Info);'
        subprocess.run(["powershell", "-Command", ps_script], capture_output=True)
    elif system == "linux":
        try:
            subprocess.run(["notify-send", title, message], capture_output=True)
        except FileNotFoundError:
            pass
    elif system == "darwin":
        subprocess.run(["osascript", "-e", f'display notification "{message}" with title "{title}"'], capture_output=True)

def get_notifications(limit=50, unread_only=False):
    if not NOTIFICATIONS_FILE.exists():
        return []
    notifications = []
    try:
        with open(NOTIFICATIONS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    n = json.loads(line)
                    if unread_only and n.get("read"):
                        continue
                    notifications.append(n)
        return notifications[-limit:][::-1]
    except:
        return []

def mark_as_read(notif_id):
    if not NOTIFICATIONS_FILE.exists():
        return
    temp_file = NOTIFICATIONS_FILE.with_suffix(".tmp")
    try:
        with open(NOTIFICATIONS_FILE, "r", encoding="utf-8") as f, \
             open(temp_file, "w", encoding="utf-8") as out:
            for line in f:
                if line.strip():
                    n = json.loads(line)
                    if n.get("id") == notif_id:
                        n["read"] = True
                    out.write(json.dumps(n, ensure_ascii=False) + "\n")
        temp_file.replace(NOTIFICATIONS_FILE)
    except:
        if temp_file.exists():
            temp_file.unlink()
