import argparse
import sys
import json
import os
import platform
from pathlib import Path

# Add current dir to path to import modules
sys.path.append(str(Path(__file__).parent))

import config
import security
import settings
import disk_manager
import pc_health
import windows_activation
import firewall_manager
import network_tools
import processes

def print_banner():
    print(r"""
   _____ ______      __  ____  ____  ____ 
  / ___// __ \ \    / / |__  ||_  _||_  _|
  \__ \/ /_/ /\ \  / /   __| |  | |    | |  
 ___/ / ____/  \ \/ /   |__  |  | |    | |  
/____/_/        \__/    |____| |___|  |___| 
    System Process Viewer - CLI v3.0
    """)

def handle_disk(args):
    if args.list:
        import psutil
        parts = psutil.disk_partitions()
        print(f"{'Device':<10} {'Mount':<15} {'FS':<10} {'Used %':<10}")
        print("-" * 50)
        for p in parts:
            try:
                usage = psutil.disk_usage(p.mountpoint)
                print(f"{p.device:<10} {p.mountpoint:<15} {p.fstype:<10} {usage.percent}%")
            except:
                print(f"{p.device:<10} {p.mountpoint:<15} {p.fstype:<10} LOCKED")
    
    if args.clean:
        if not args.mount:
            print("Error: Se requiere --mount <ruta> para limpiar.")
            return
        print(f"Iniciando limpieza segura en {args.mount}...")
        res = disk_manager.safe_clean_disk(args.mount, job_update=lambda **kw: print(f"  > {kw.get('message','...')}"))
        print(f"Resultado: {res}")

    if args.defrag:
        if not args.mount:
            print("Error: Se requiere --mount <ruta> para desfragmentar.")
            return
        print(f"Desfragmentando {args.mount}...")
        res = disk_manager.defragment_disk(args.mount, job_update=lambda **kw: print(f"  > {kw.get('message','...')}"))
        print("Hecho.")

def handle_health(args):
    print("Iniciando escaneo de salud del sistema...")
    report = pc_health.full_health_scan(job_update=lambda **kw: print(f"  [*] {kw.get('message','...')}"))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("\n--- RESUMEN DE SALUD ---")
        for key, val in report.items():
            status = "OK" if "error" not in str(val).lower() else "ERROR"
            print(f"[{status}] {key}")

def handle_activation(args):
    status = windows_activation.get_activation_status()
    print(f"Estado: {status['license_status']}")
    print(f"Activado: {status['activated']}")
    
    if args.auto:
        print("Intentando activación automática con claves GVLK...")
        res = windows_activation.auto_activate()
        print(f"Resultado: {res}")

def handle_network(args):
    if args.firewall:
        status = firewall_manager.get_firewall_status()
        print("--- ESTADO DEL FIREWALL ---")
        for p, s in status.items():
            print(f"{p}: {s}")
    
    if args.stats:
        stats = firewall_manager.get_network_stats()
        print("--- ESTADÍSTICAS DE RED ---")
        for nic, s in list(stats.items())[:5]:
            print(f"{nic}: TX={s['bytes_sent']/1e6:.1f}MB, RX={s['bytes_recv']/1e6:.1f}MB")

def handle_os(args):
    import os_recommender
    if args.recommend:
        res = os_recommender.recommend_os()
        print("--- RECOMENDACIONES DE SO ---")
        for r in res['recommendations'][:3]:
            print(f"[{r['rating']}] {r['name']} - {r['category']}")
            print(f"  Pros: {', '.join(r['pros'][:2])}")

def handle_programs(args):
    import program_manager
    if args.list:
        progs = program_manager.list_installed_programs()
        print(f"{'Nombre':<40} {'Versión':<15} {'Tamaño (MB)':<10}")
        print("-" * 65)
        for p in progs:
            print(f"{p['name'][:38]:<40} {p['version'][:13]:<15} {p['size_mb']:<10}")
    
    if args.uninstall:
        print(f"Intentando desinstalar: {args.uninstall}")
        res = program_manager.uninstall_program(args.uninstall, quiet=True)
        print(f"Resultado: {res}")

def handle_drivers(args):
    import driver_manager
    if args.list:
        drivers = driver_manager.list_drivers()
        print(f"{'Published Name':<20} {'Original Name':<20} {'Provider':<20}")
        print("-" * 65)
        for d in drivers:
            print(f"{d.get('published_name', '')[:18]:<20} {d.get('original_name', '')[:18]:<20} {d.get('provider_name', '')[:18]:<20}")
    if args.devices:
        devs = driver_manager.list_devices()
        print(f"{'Status':<10} {'Name':<50}")
        print("-" * 65)
        for d in devs:
            print(f"{d.get('Status', '')[:8]:<10} {d.get('FriendlyName', '')[:48]:<50}")

def handle_scanner(args):
    import virustotal_scanner
    if args.file:
        print(f"Escaneando archivo localmente: {args.file}")
        res = virustotal_scanner.local_scan_file(args.file)
        print(json.dumps(res, indent=2))
        
        if args.vt:
            print("\nEnviando a VirusTotal...")
            vt_res = virustotal_scanner.scan_file_vt(args.file)
            print(json.dumps(vt_res, indent=2))

def main():
    parser = argparse.ArgumentParser(description="SPV 3.1 CLI - System Management Tool")
    subparsers = parser.add_subparsers(dest="command")

    # Disk
    disk_p = subparsers.add_parser("disk", help="Gestión de discos")
    disk_p.add_argument("--list", action="store_true", help="Listar particiones")
    disk_p.add_argument("--clean", action="store_true", help="Limpieza segura")
    disk_p.add_argument("--defrag", action="store_true", help="Desfragmentar")
    disk_p.add_argument("--mount", type=str, help="Punto de montaje (ej. C: o /)")

    # Health
    health_p = subparsers.add_parser("health", help="Salud del sistema")
    health_p.add_argument("--json", action="store_true", help="Salida en JSON")

    # Activation
    act_p = subparsers.add_parser("activation", help="Activación de Windows")
    act_p.add_argument("--auto", action="store_true", help="Intentar activación GVLK")

    # Network
    net_p = subparsers.add_parser("network", help="Herramientas de red")
    net_p.add_argument("--firewall", action="store_true", help="Ver estado firewall")
    net_p.add_argument("--stats", action="store_true", help="Ver estadísticas")

    # OS Recommender
    os_p = subparsers.add_parser("os", help="Recomendador de SO")
    os_p.add_argument("--recommend", action="store_true", help="Recomendar SO")

    # Programs
    prog_p = subparsers.add_parser("programs", help="Gestión de programas")
    prog_p.add_argument("--list", action="store_true", help="Listar instalados")
    prog_p.add_argument("--uninstall", type=str, help="Desinstalar programa por nombre")

    # Drivers
    drv_p = subparsers.add_parser("drivers", help="Gestión de drivers")
    drv_p.add_argument("--list", action="store_true", help="Listar drivers de terceros")
    drv_p.add_argument("--devices", action="store_true", help="Listar dispositivos PnP")

    # Scanner
    scan_p = subparsers.add_parser("scanner", help="Antivirus y escáner")
    scan_p.add_argument("--file", type=str, help="Ruta del archivo a escanear")
    scan_p.add_argument("--vt", action="store_true", help="Usar API de VirusTotal (requiere key en settings)")

    args = parser.parse_args()

    if not args.command:
        print_banner()
        parser.print_help()
        return

    if args.command == "disk": handle_disk(args)
    elif args.command == "health": handle_health(args)
    elif args.command == "activation": handle_activation(args)
    elif args.command == "network": handle_network(args)
    elif args.command == "os": handle_os(args)
    elif args.command == "programs": handle_programs(args)
    elif args.command == "drivers": handle_drivers(args)
    elif args.command == "scanner": handle_scanner(args)

if __name__ == "__main__":
    main()
