"""
firewall_manager.py
Manage Windows Firewall via netsh / PowerShell.
All operations log to audit and require power mode.
"""
import subprocess
import platform
import re

_WIN = platform.system().lower() == "windows"

def _run(cmd: str, ps: bool = False):
    if ps:
        cmd = f'powershell -NoProfile -Command "{cmd}"'
    r = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    return {"stdout": r.stdout.strip(), "stderr": r.stderr.strip(), "ok": r.returncode == 0}

# ------------------------------------------------------------------
# Profile control
# ------------------------------------------------------------------
def get_firewall_status():
    """Returns firewall state for Domain/Private/Public profiles."""
    if not _WIN:
        return {"error": "Solo Windows."}
    r = _run("netsh advfirewall show allprofiles state")
    profiles = {}
    for line in r["stdout"].splitlines():
        if "State" in line:
            parts = line.split()
            if len(parts) >= 2:
                profiles[len(profiles)] = parts[-1]
    names = ["Domain", "Private", "Public"]
    result = {}
    idx = 0
    for line in r["stdout"].splitlines():
        if "State" in line:
            val = line.split()[-1]
            if idx < len(names):
                result[names[idx]] = val
                idx += 1
    return result

def set_firewall_profile(profile: str, state: str):
    """Enable or disable a firewall profile. profile: Domain/Private/Public/All, state: ON/OFF"""
    if not _WIN:
        return {"error": "Solo Windows."}
    profile = profile.lower()
    state = state.upper()
    if state not in ("ON", "OFF"):
        return {"error": "Estado debe ser ON u OFF."}
    valid_profiles = ("domain", "private", "public", "all")
    if profile not in valid_profiles:
        return {"error": f"Perfil inválido. Usa: {valid_profiles}"}
    r = _run(f"netsh advfirewall set {profile}profile state {state}")
    return {"ok": r["ok"], "message": r["stdout"] or r["stderr"]}

# ------------------------------------------------------------------
# Rules
# ------------------------------------------------------------------
def list_firewall_rules(direction: str = "in", protocol: str = "", enabled_only: bool = False):
    """List firewall rules filtered by direction (in/out) and optional protocol."""
    if not _WIN:
        return []
    direction = direction.lower()
    cmd = f'netsh advfirewall firewall show rule name=all dir={direction} verbose'
    r = _run(cmd)
    rules = []
    current = {}
    for line in r["stdout"].splitlines():
        line = line.strip()
        if not line:
            if current:
                rules.append(current)
                current = {}
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip().lower().replace(" ", "_")
            val = val.strip()
            current[key] = val
    if current:
        rules.append(current)

    if enabled_only:
        rules = [r for r in rules if r.get("enabled", "").lower() == "yes"]
    if protocol:
        rules = [r for r in rules if r.get("protocol", "").lower() == protocol.lower()]

    return rules[:200]  # cap for safety

def add_firewall_rule(name: str, direction: str, action: str, protocol: str,
                      localport: str = "", remoteip: str = "", program: str = ""):
    """Add a new firewall rule."""
    if not _WIN:
        return {"error": "Solo Windows."}

    direction = direction.lower()
    action = action.lower()
    protocol = protocol.lower()

    if direction not in ("in", "out"):
        return {"error": "Dirección inválida (in/out)."}
    if action not in ("allow", "block"):
        return {"error": "Acción inválida (allow/block)."}

    cmd = (f'netsh advfirewall firewall add rule name="{name}" '
           f'dir={direction} action={action} protocol={protocol} enable=yes')
    if localport:
        cmd += f" localport={localport}"
    if remoteip:
        cmd += f" remoteip={remoteip}"
    if program and program != "any":
        cmd += f' program="{program}"'

    r = _run(cmd)
    return {"ok": r["ok"], "message": r["stdout"] or r["stderr"]}

def delete_firewall_rule(name: str):
    """Delete a firewall rule by name."""
    if not _WIN:
        return {"error": "Solo Windows."}
    r = _run(f'netsh advfirewall firewall delete rule name="{name}"')
    return {"ok": r["ok"], "message": r["stdout"] or r["stderr"]}

def toggle_firewall_rule(name: str, enable: bool):
    """Enable or disable a rule by name."""
    if not _WIN:
        return {"error": "Solo Windows."}
    state = "yes" if enable else "no"
    r = _run(f'netsh advfirewall firewall set rule name="{name}" new enable={state}')
    return {"ok": r["ok"], "message": r["stdout"] or r["stderr"]}

def block_ip(ip: str, direction: str = "in"):
    """Quickly block an IP address inbound or outbound."""
    name = f"SPV_BLOCK_{ip.replace('.', '_')}_{direction.upper()}"
    return add_firewall_rule(name, direction, "block", "any", remoteip=ip)

def unblock_ip(ip: str, direction: str = "in"):
    name = f"SPV_BLOCK_{ip.replace('.', '_')}_{direction.upper()}"
    return delete_firewall_rule(name)

# ------------------------------------------------------------------
# Network stats
# ------------------------------------------------------------------
def get_network_stats():
    """Returns per-interface TX/RX counters via psutil."""
    try:
        import psutil
        io = psutil.net_io_counters(pernic=True)
        result = {}
        for nic, s in io.items():
            result[nic] = {
                "bytes_sent": s.bytes_sent,
                "bytes_recv": s.bytes_recv,
                "packets_sent": s.packets_sent,
                "packets_recv": s.packets_recv,
                "errin": s.errin,
                "errout": s.errout,
                "dropin": s.dropin,
                "dropout": s.dropout,
            }
        return result
    except Exception as e:
        return {"error": str(e)}

def get_active_connections():
    """Returns active TCP/UDP connections with process names."""
    try:
        import psutil
        conns = []
        for c in psutil.net_connections(kind="inet"):
            try:
                proc = psutil.Process(c.pid).name() if c.pid else "?"
            except:
                proc = "?"
            conns.append({
                "pid": c.pid,
                "process": proc,
                "proto": "TCP" if c.type == 1 else "UDP",
                "laddr": f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "",
                "raddr": f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "",
                "status": c.status or "NONE",
            })
        return conns
    except Exception as e:
        return []

def ping_host(host: str, count: int = 4):
    """Ping a host and return parsed results."""
    system = platform.system().lower()
    if system == "windows":
        cmd = f"ping -n {count} {host}"
    else:
        cmd = f"ping -c {count} {host}"
    r = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=20)
    return {"raw": r.stdout[-2000:], "ok": r.returncode == 0}

def traceroute(host: str):
    """Run traceroute/tracert."""
    system = platform.system().lower()
    cmd = f"tracert -d -h 15 {host}" if system == "windows" else f"traceroute -n -m 15 {host}"
    r = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=60)
    return {"raw": r.stdout[-3000:], "ok": r.returncode == 0}

def get_dns_servers():
    """Get configured DNS servers (Windows)."""
    if not _WIN:
        return []
    r = _run("netsh interface ip show dns")
    servers = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', r["stdout"])
    return list(set(servers))

def flush_dns():
    """Flush the DNS resolver cache."""
    if _WIN:
        r = _run("ipconfig /flushdns")
    else:
        r = _run("systemd-resolve --flush-caches 2>/dev/null || resolvectl flush-caches 2>/dev/null")
    return {"ok": r["ok"], "message": r["stdout"]}
