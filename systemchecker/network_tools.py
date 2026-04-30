import socket
import requests
import time
import platform
import subprocess
import psutil

def test_dns(host="google.com"):
    try:
        start = time.time()
        ip = socket.gethostbyname(host)
        return {"status": "ok", "ip": ip, "latency_ms": round((time.time() - start) * 1000, 2)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def test_http(url="https://www.google.com", timeout=5):
    try:
        start = time.time()
        r = requests.get(url, timeout=timeout)
        return {
            "status": "ok" if r.status_code < 400 else "warning",
            "code": r.status_code,
            "latency_ms": round((time.time() - start) * 1000, 2)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def test_tcp(host, port, timeout=3):
    try:
        start = time.time()
        with socket.create_connection((host, port), timeout=timeout):
            return {"status": "ok", "latency_ms": round((time.time() - start) * 1000, 2)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_network_interfaces():
    interfaces = []
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    
    for name, snic in stats.items():
        iface = {
            "name": name,
            "is_up": snic.isup,
            "speed": snic.speed,
            "mtu": snic.mtu,
            "addresses": []
        }
        if name in addrs:
            for addr in addrs[name]:
                iface["addresses"].append({
                    "family": str(addr.family),
                    "address": addr.address,
                    "netmask": addr.netmask
                })
        interfaces.append(iface)
    return interfaces

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"
