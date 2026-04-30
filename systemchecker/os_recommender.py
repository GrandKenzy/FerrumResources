"""
os_recommender.py
Analyzes system specs and recommends optimal operating systems.
"""
import platform
import psutil
import struct

def get_system_specs():
    """Collect current system specs for recommendation."""
    ram_gb = round(psutil.virtual_memory().total / 1e9, 1)
    cpu_count = psutil.cpu_count(logical=True)
    cpu_freq = psutil.cpu_freq()
    freq_ghz = round(cpu_freq.max / 1000, 2) if cpu_freq and cpu_freq.max else 0
    disk_total_gb = 0
    for p in psutil.disk_partitions():
        try:
            u = psutil.disk_usage(p.mountpoint)
            disk_total_gb += u.total / 1e9
        except:
            pass
    disk_total_gb = round(disk_total_gb, 1)
    arch = platform.machine()
    bits = struct.calcsize("P") * 8
    current_os = platform.platform()
    
    return {
        "ram_gb": ram_gb,
        "cpu_cores": cpu_count,
        "cpu_freq_ghz": freq_ghz,
        "disk_gb": disk_total_gb,
        "arch": arch,
        "bits": bits,
        "current_os": current_os,
    }

# ── OS Database ──
OS_DATABASE = [
    {
        "name": "Windows 11 Pro",
        "category": "General / Gaming",
        "min_ram": 4, "rec_ram": 8,
        "min_disk": 64,
        "min_cores": 2,
        "bits": 64,
        "description": "El sistema operativo más popular para escritorio. Soporte completo de juegos, software empresarial y hardware moderno. Requiere TPM 2.0 y Secure Boot.",
        "url": "https://www.microsoft.com/software-download/windows11",
        "pros": ["Compatibilidad universal de software", "Soporte DirectX 12 Ultimate", "Integración nativa con Xbox"],
        "cons": ["Uso elevado de RAM en idle (~3GB)", "Telemetría obligatoria", "Requiere TPM 2.0"],
    },
    {
        "name": "Windows 10 Pro",
        "category": "General / Legacy",
        "min_ram": 2, "rec_ram": 4,
        "min_disk": 32,
        "min_cores": 1,
        "bits": 64,
        "description": "Versión madura y estable de Windows. Ideal si tu hardware no soporta TPM 2.0 o si prefieres estabilidad sobre novedades.",
        "url": "https://www.microsoft.com/software-download/windows10",
        "pros": ["Amplia compatibilidad", "No requiere TPM 2.0", "Muy estable"],
        "cons": ["Fin de soporte en Oct 2025", "Sin actualizaciones de características"],
    },
    {
        "name": "Ubuntu 24.04 LTS",
        "category": "Desarrollo / Servidor",
        "min_ram": 2, "rec_ram": 4,
        "min_disk": 25,
        "min_cores": 1,
        "bits": 64,
        "description": "La distribución Linux más popular. Perfecta para desarrollo, servidores y uso general. Soporte a largo plazo de 5 años.",
        "url": "https://ubuntu.com/download/desktop",
        "pros": ["Gratuito", "Excelente para programación", "Bajo consumo de recursos"],
        "cons": ["Compatibilidad limitada con juegos AAA", "Curva de aprendizaje para nuevos usuarios"],
    },
    {
        "name": "Linux Mint 22",
        "category": "General / Migración desde Windows",
        "min_ram": 2, "rec_ram": 4,
        "min_disk": 20,
        "min_cores": 1,
        "bits": 64,
        "description": "La distribución ideal para usuarios que vienen de Windows. Interfaz familiar, estable y ligera.",
        "url": "https://linuxmint.com/download.php",
        "pros": ["Interfaz similar a Windows", "Muy estable", "Gratuito"],
        "cons": ["Menos soporte corporativo que Ubuntu", "Repositorios algo más limitados"],
    },
    {
        "name": "Fedora Workstation 41",
        "category": "Desarrollo Avanzado",
        "min_ram": 2, "rec_ram": 8,
        "min_disk": 20,
        "min_cores": 2,
        "bits": 64,
        "description": "Distribución de vanguardia respaldada por Red Hat. Trae las últimas tecnologías Linux con GNOME moderno.",
        "url": "https://fedoraproject.org/workstation/download",
        "pros": ["Software siempre actualizado", "Excelente GNOME", "Base de RHEL"],
        "cons": ["Ciclo de vida corto (13 meses)", "Cambios frecuentes"],
    },
    {
        "name": "Arch Linux",
        "category": "Avanzado / Personalización Total",
        "min_ram": 1, "rec_ram": 2,
        "min_disk": 10,
        "min_cores": 1,
        "bits": 64,
        "description": "Rolling release para usuarios avanzados. Máxima personalización y control total sobre el sistema.",
        "url": "https://archlinux.org/download/",
        "pros": ["Rolling release", "Wiki excepcional", "AUR masivo"],
        "cons": ["Instalación manual", "Requiere conocimiento avanzado de Linux"],
    },
    {
        "name": "Lubuntu 24.04",
        "category": "Hardware Antiguo / Ligero",
        "min_ram": 1, "rec_ram": 2,
        "min_disk": 10,
        "min_cores": 1,
        "bits": 64,
        "description": "Ubuntu ultra-ligero con escritorio LXQt. Revive PCs antiguas con hardware limitado.",
        "url": "https://lubuntu.me/downloads/",
        "pros": ["Extremadamente ligero (~300MB RAM)", "Funcional en PCs de 10+ años"],
        "cons": ["Estética básica", "Menos funcionalidades de escritorio"],
    },
    {
        "name": "Zorin OS 17",
        "category": "General / Estética Premium",
        "min_ram": 2, "rec_ram": 4,
        "min_disk": 20,
        "min_cores": 2,
        "bits": 64,
        "description": "Linux con la estética más pulida del mercado. Diseño premium tipo macOS/Windows con compatibilidad Wine integrada.",
        "url": "https://zorin.com/os/download/",
        "pros": ["Bellísimo diseño", "Layouts tipo Windows/macOS", "Wine preconfigurado"],
        "cons": ["Versión Pro es de pago", "Basado en Ubuntu LTS (no bleeding edge)"],
    },
    {
        "name": "Pop!_OS 22.04",
        "category": "Gaming en Linux / Desarrollo",
        "min_ram": 4, "rec_ram": 8,
        "min_disk": 20,
        "min_cores": 2,
        "bits": 64,
        "description": "Creada por System76 para productividad y gaming. Excelente soporte NVIDIA out-of-the-box.",
        "url": "https://pop.system76.com/",
        "pros": ["Soporte NVIDIA integrado", "Tiling automático", "Genial para gaming Linux"],
        "cons": ["Basado en Ubuntu más antiguo", "Comunidad más pequeña"],
    },
    {
        "name": "ChromeOS Flex",
        "category": "Navegación Web / Hardware Limitado",
        "min_ram": 2, "rec_ram": 4,
        "min_disk": 16,
        "min_cores": 1,
        "bits": 64,
        "description": "ChromeOS de Google para PCs existentes. Ideal si solo necesitas navegador, apps web y Android.",
        "url": "https://chromeenterprise.google/os/chromeosflex/",
        "pros": ["Ultra-rápido en hardware viejo", "Seguridad empresarial", "Apps Android"],
        "cons": ["Solo apps web/Android", "Sin software nativo de escritorio"],
    },
    {
        "name": "macOS (Hackintosh)",
        "category": "Creativos / Desarrollo Apple",
        "min_ram": 4, "rec_ram": 8,
        "min_disk": 50,
        "min_cores": 2,
        "bits": 64,
        "description": "macOS en hardware no-Apple. Solo viable con CPUs Intel compatibles. Uso educativo/experimental.",
        "url": "https://support.apple.com/macos",
        "pros": ["Ecosistema Apple", "Final Cut / Xcode", "Estética premium"],
        "cons": ["Legalidad gris", "Compatibilidad limitada", "Sin actualizaciones oficiales"],
    },
    {
        "name": "Debian 12 Bookworm",
        "category": "Servidor / Estabilidad Máxima",
        "min_ram": 1, "rec_ram": 2,
        "min_disk": 10,
        "min_cores": 1,
        "bits": 64,
        "description": "La distribución madre de Ubuntu. Máxima estabilidad para servidores y uso de producción.",
        "url": "https://www.debian.org/download",
        "pros": ["Extremadamente estable", "Base de muchas distros", "Ideal para servidores"],
        "cons": ["Software más antiguo", "Configuración manual de codecs/drivers"],
    },
]

def recommend_os(specs: dict = None):
    """Returns a ranked list of OS recommendations based on system specs."""
    if not specs:
        specs = get_system_specs()

    recommendations = []
    for os_info in OS_DATABASE:
        score = 0
        meets_minimum = True
        issues = []

        # Check minimum requirements
        if specs["ram_gb"] < os_info["min_ram"]:
            meets_minimum = False
            issues.append(f"RAM insuficiente (necesita {os_info['min_ram']}GB, tienes {specs['ram_gb']}GB)")
        if specs["disk_gb"] < os_info["min_disk"]:
            meets_minimum = False
            issues.append(f"Disco insuficiente (necesita {os_info['min_disk']}GB)")
        if specs["bits"] < os_info.get("bits", 64):
            meets_minimum = False
            issues.append("Requiere sistema de 64 bits")

        # Score calculation
        if meets_minimum:
            # RAM fit
            if specs["ram_gb"] >= os_info["rec_ram"]:
                score += 30
            elif specs["ram_gb"] >= os_info["min_ram"]:
                score += 15

            # CPU fit
            if specs["cpu_cores"] >= os_info.get("min_cores", 1) * 2:
                score += 25
            elif specs["cpu_cores"] >= os_info.get("min_cores", 1):
                score += 15

            # Disk space bonus
            if specs["disk_gb"] > os_info["min_disk"] * 3:
                score += 15
            elif specs["disk_gb"] > os_info["min_disk"] * 1.5:
                score += 10

            # Category bonuses based on specs
            if specs["ram_gb"] >= 16 and "Gaming" in os_info["category"]:
                score += 15
            if specs["ram_gb"] <= 4 and "Ligero" in os_info["category"]:
                score += 20
            if specs["cpu_cores"] >= 8 and "Desarrollo" in os_info["category"]:
                score += 10

        # Rating label
        if score >= 60:
            rating = "Excelente"
        elif score >= 40:
            rating = "Bueno"
        elif score >= 20:
            rating = "Aceptable"
        else:
            rating = "No recomendado" if not meets_minimum else "Mínimo"

        recommendations.append({
            **os_info,
            "score": score,
            "meets_minimum": meets_minimum,
            "rating": rating,
            "issues": issues,
        })

    recommendations.sort(key=lambda x: x["score"], reverse=True)
    return {"specs": specs, "recommendations": recommendations}

def evaluate_current_os(specs: dict = None):
    """Evaluates if the currently installed OS is optimal for this hardware."""
    if not specs:
        specs = get_system_specs()
    
    current = specs["current_os"].lower()
    verdict = "adecuado"
    notes = []

    if "windows 10" in current or "windows 11" in current:
        if specs["ram_gb"] < 4:
            verdict = "subóptimo"
            notes.append("Windows funciona mejor con 4+ GB de RAM. Considera una distribución Linux ligera.")
        elif specs["ram_gb"] >= 4 and specs["ram_gb"] < 8:
            notes.append("Tu sistema cumple los mínimos pero podría beneficiarse de más RAM.")
        else:
            notes.append("Tus especificaciones son suficientes para Windows.")
        
        if specs["disk_gb"] < 80:
            notes.append("Espacio en disco algo limitado para Windows; considera liberar espacio.")
    elif "linux" in current:
        notes.append("Linux es ideal para tus especificaciones actuales.")
    
    return {"verdict": verdict, "notes": notes, "current_os": specs["current_os"]}
