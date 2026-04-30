import os
import platform
import psutil
import socket
import time
from datetime import datetime
from config import APP_NAME, ENABLE_POWER_ACTIONS_ENV

def bytes_fmt(n: float) -> str:
    try:
        n = float(n)
    except Exception:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    idx = 0
    while n >= 1024 and idx < len(units) - 1:
        n /= 1024
        idx += 1
    return f"{n:.1f} {units[idx]}" if idx else f"{int(n)} {units[idx]}"

def pct(x: float) -> float:
    try:
        return round(float(x), 2)
    except Exception:
        return 0.0

def disk_io_rates() -> dict:
    try:
        first = psutil.disk_io_counters()
        net_first = psutil.net_io_counters()
        time.sleep(0.1)
        second = psutil.disk_io_counters()
        net_second = psutil.net_io_counters()
        if not first or not second:
            return {}
        factor = 10.0
        return {
            "disk_read_rate": bytes_fmt((second.read_bytes - first.read_bytes) * factor),
            "disk_write_rate": bytes_fmt((second.write_bytes - first.write_bytes) * factor),
            "net_sent_rate": bytes_fmt((net_second.bytes_sent - net_first.bytes_sent) * factor),
            "net_recv_rate": bytes_fmt((net_second.bytes_recv - net_first.bytes_recv) * factor),
        }
    except:
        return {}

def collect_system_info():
    vm = psutil.virtual_memory()
    sm = psutil.swap_memory()
    boot = datetime.fromtimestamp(psutil.boot_time()).isoformat(timespec="seconds")
    cpu_freq = psutil.cpu_freq()
    
    # Advanced: Temps (may require admin/specific hardware)
    temps = {}
    try:
        if hasattr(psutil, "sensors_temperatures"):
            st = psutil.sensors_temperatures()
            for name, entries in st.items():
                temps[name] = [e.current for e in entries]
    except:
        pass

    # Advanced: Users
    users = []
    try:
        users = [u._asdict() for u in psutil.users()]
    except:
        pass

    partitions = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            partitions.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total": bytes_fmt(usage.total),
                "used": bytes_fmt(usage.used),
                "free": bytes_fmt(usage.free),
                "percent": pct(usage.percent),
                "is_system": part.mountpoint.upper() in ["C:\\", "/"]
            })
        except:
            continue

    load = os.getloadavg() if hasattr(os, "getloadavg") else None
    
    return {
        "app_name": APP_NAME,
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "boot_time": boot,
        "uptime_seconds": int(time.time() - psutil.boot_time()),
        "cpu": {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "percent": pct(psutil.cpu_percent(interval=0.1)),
            "per_cpu": [pct(x) for x in psutil.cpu_percent(interval=0.1, percpu=True)],
            "freq_current": round(cpu_freq.current, 2) if cpu_freq else None,
            "freq_max": round(cpu_freq.max, 2) if cpu_freq else None,
            "load": load,
            "temperatures": temps
        },
        "memory": {
            "total": bytes_fmt(vm.total),
            "available": bytes_fmt(vm.available),
            "used": bytes_fmt(vm.used),
            "percent": pct(vm.percent),
            "swap_total": bytes_fmt(sm.total),
            "swap_used": bytes_fmt(sm.used),
            "swap_percent": pct(sm.percent),
        },
        "disk": {
            "partitions": partitions,
            **disk_io_rates(),
        },
        "users": users,
        "power_actions_enabled": ENABLE_POWER_ACTIONS_ENV,
    }
