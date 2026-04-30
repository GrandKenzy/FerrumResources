import os
import sys
import sysconfig
import secrets
import threading
import webbrowser
from pathlib import Path
from flask import Flask, jsonify, render_template, request, session, abort, send_from_directory, redirect, url_for

import config
import settings
import security
import audit
import notifier
import system_info
import processes
import alerts
import cleanup
import desktop_cleaner
import ports
import port_protect
import network_tools
import firewall_manager
import scheduler
import reports
import disk_manager
import windows_activation
import pc_health
import jobs
import os_recommender
import admin_helper
import program_manager
import driver_manager
import virustotal_scanner
import file_manager
import terminal_manager
import windows_customization

def _find_asset_dir(name: str) -> str:
    """Locate Flask templates/static after editable install, wheel install or direct repo run."""
    module_dir = Path(__file__).resolve().parent
    candidates = [
        module_dir / name,
        Path.cwd() / name,
        Path(sys.prefix) / name,
        Path(sysconfig.get_paths().get("data", sys.prefix)) / name,
        Path(sysconfig.get_paths().get("purelib", module_dir)) / name,
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return str(module_dir / name)


app = Flask(
    __name__,
    template_folder=_find_asset_dir("templates"),
    static_folder=_find_asset_dir("static"),
)
app.secret_key = config.SECRET_KEY

# Ensure data is loaded
settings.load_settings()
security.load_security_rules()
scheduler.load_tasks()
scheduler.start_scheduler()

@app.context_processor
def inject_globals():
    """Inject common variables into every template."""
    return {
        "settings": settings,
        "require_confirm": settings.get_setting("security.require_confirm_phrase", True),
        "power_enabled": security.is_power_actions_enabled(),
    }

# -- Middlewares --

@app.before_request
def before_req():
    security.init_session()

# -- HTML Routes --

@app.route('/')
def dashboard():
    sys_info = system_info.collect_system_info()
    procs = processes.collect_processes()[:8]
    active_alerts = alerts.get_active_alerts()
    return render_template('dashboard.html',
                           system=sys_info,
                           top_procs=procs,
                           alerts=active_alerts,
                           power_enabled=security.is_power_actions_enabled(),
                           active_page='dashboard')

@app.route('/processes')
def processes_page():
    return render_template('processes.html',
                           active_page='processes',
                           power_enabled=security.is_power_actions_enabled())

@app.route('/performance')
def performance_page():
    return render_template('performance.html',
                           active_page='performance',
                           system=system_info.collect_system_info(),
                           power_enabled=security.is_power_actions_enabled())

@app.route('/ports')
def ports_page():
    return render_template('ports.html',
                           active_page='ports',
                           power_enabled=security.is_power_actions_enabled())

@app.route('/cleanup')
def cleanup_page():
    return render_template('cleanup.html',
                           active_page='cleanup',
                           power_enabled=security.is_power_actions_enabled())

@app.route('/disk')
def disk_page():
    phys = disk_manager.list_physical_disks()
    return render_template('disk.html',
                           active_page='disk',
                           system=system_info.collect_system_info(),
                           physical_disks=phys,
                           power_enabled=security.is_power_actions_enabled())

@app.route('/network')
def network_page():
    return render_template('network.html',
                           active_page='network',
                           power_enabled=security.is_power_actions_enabled())

@app.route('/firewall')
def firewall_page():
    return render_template('firewall.html',
                           active_page='firewall',
                           power_enabled=security.is_power_actions_enabled())

@app.route('/scheduler')
def scheduler_page():
    return render_template('scheduler.html',
                           active_page='scheduler',
                           tasks=scheduler.load_tasks(),
                           power_enabled=security.is_power_actions_enabled())

@app.route('/reports')
def reports_page():
    return render_template('reports.html',
                           active_page='reports',
                           reports=reports.list_reports(),
                           power_enabled=security.is_power_actions_enabled())

@app.route('/settings')
def settings_page():
    return render_template('settings.html',
                           active_page='settings',
                           settings=settings.load_settings(),
                           power_enabled=security.is_power_actions_enabled())

@app.route('/health')
def health_page():
    return render_template('health.html',
                           active_page='health',
                           power_enabled=security.is_power_actions_enabled())

@app.route('/jobs')
def jobs_page():
    return render_template('jobs_queue.html',
                           active_page='jobs',
                           power_enabled=security.is_power_actions_enabled())

@app.route('/activation')
def activation_page():
    status = windows_activation.get_activation_status()
    edition, key = windows_activation.get_matching_key()
    available = windows_activation.list_available_keys()
    return render_template('activation.html',
                           active_page='activation',
                           activation_status=status,
                           detected_edition=edition,
                           suggested_key=key,
                           available_keys=available,
                           power_enabled=security.is_power_actions_enabled())

# -- API: Core --

@app.route('/api/system')
def api_system():
    return jsonify(system_info.collect_system_info())

@app.route('/api/processes')
def api_processes():
    return jsonify(processes.collect_processes())

@app.route('/api/processes/<int:pid>')
def api_process_detail(pid):
    return jsonify(processes.process_detail(pid))

@app.route('/api/processes/<int:pid>/kill', methods=['POST'])
def api_process_kill(pid):
    security.require_power("CONFIRMAR")
    try:
        import psutil
        p = psutil.Process(pid)
        name = p.name()
        p.kill()
        audit.log_audit("kill_process", f"PID {pid} ({name})")
        return jsonify({"message": f"Proceso {name} ({pid}) terminado."})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/processes/<int:pid>/terminate', methods=['POST'])
def api_process_terminate(pid):
    security.require_power("TERMINAR")
    try:
        import psutil
        p = psutil.Process(pid)
        name = p.name()
        p.terminate()
        audit.log_audit("terminate_process", f"PID {pid} ({name})")
        return jsonify({"message": f"Señal de terminación enviada a {name} ({pid})."})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# -- API: Settings --

@app.route('/api/settings', methods=['POST'])
def api_save_settings():
    security.require_csrf()
    data = request.json
    settings.save_settings(data)
    audit.log_audit("update_settings", "all")
    return jsonify({"message": "Settings guardados"})

@app.route('/api/settings/reset', methods=['POST'])
def api_reset_settings():
    security.require_csrf()
    settings.reset_settings()
    audit.log_audit("reset_settings", "all")
    return jsonify({"message": "Settings restaurados"})

@app.route('/api/settings/theme', methods=['POST'])
def api_save_theme():
    data = request.json
    theme = data.get("theme", "light")
    settings.set_setting("ui.theme", theme)
    return jsonify({"message": f"Tema {theme} guardado"})

# -- API: Cleanup --

@app.route('/api/cleanup/scan')
def api_cleanup_scan():
    age = settings.get_setting("cleanup.clean_temp_min_age_hours", 24)
    return jsonify(cleanup.scan_safe_cleanup(age))

@app.route('/api/cleanup/desktop/scan')
def api_cleanup_desktop_scan():
    age = settings.get_setting("cleanup.desktop_junk_min_age_days", 7)
    return jsonify(desktop_cleaner.scan_desktop_junk(age))

@app.route('/api/cleanup/quarantine', methods=['POST'])
def api_cleanup_quarantine():
    security.require_power()
    data = request.json
    res = cleanup.quarantine_files(data.get("paths", []), data.get("reason", "Manual Cleanup"))
    audit.log_audit("cleanup_quarantine", f"{res['success_count']} files", "ok", res)
    return jsonify(res)

@app.route('/api/cleanup/quarantine/list')
def api_cleanup_quarantine_list():
    return jsonify(cleanup.list_quarantine())

@app.route('/api/cleanup/quarantine/<id>/restore', methods=['POST'])
def api_cleanup_restore(id):
    security.require_csrf()
    if cleanup.restore_quarantine(id):
        audit.log_audit("restore_quarantine", id)
        return jsonify({"message": "Restaurado con éxito"})
    return jsonify({"error": "No se pudo restaurar"}), 400

@app.route('/api/cleanup/quarantine/<id>/delete', methods=['POST'])
def api_cleanup_delete(id):
    security.require_power()
    if cleanup.delete_permanently(id):
        audit.log_audit("delete_quarantine", id)
        return jsonify({"message": "Eliminado permanentemente"})
    return jsonify({"error": "No se pudo eliminar"}), 400

# -- API: Notifications --

@app.route('/api/notifications')
def api_notifications_list():
    return jsonify(notifier.get_notifications())

@app.route('/api/notifications/unread')
def api_notifications_unread():
    return jsonify(notifier.get_notifications(unread_only=True))

@app.route('/api/notifications/<id>/read', methods=['POST'])
def api_notifications_mark_read(id):
    security.require_csrf()
    notifier.mark_as_read(id)
    return jsonify({"message": "Notificación leída"})

# -- API: Reports --

@app.route('/api/reports/generate', methods=['POST'])
def api_reports_generate():
    security.require_csrf()
    res = reports.generate_report()
    audit.log_audit("generate_report", res["id"])
    return jsonify(res)

# -- API: Network --

@app.route('/api/network/test', methods=['POST'])
def api_network_test():
    security.require_csrf()
    data = request.json
    target = data.get("target", "google.com")
    res = {
        "dns": network_tools.test_dns(target),
        "http": network_tools.test_http(f"https://{target}"),
        "local_ip": network_tools.get_local_ip()
    }
    return jsonify(res)

@app.route('/api/network/interfaces')
def api_network_interfaces():
    return jsonify(network_tools.get_network_interfaces())

@app.route('/api/network/stats')
def api_network_stats():
    return jsonify(firewall_manager.get_network_stats())

@app.route('/api/network/connections')
def api_network_connections():
    return jsonify(firewall_manager.get_active_connections())

@app.route('/api/network/ping', methods=['POST'])
def api_network_ping():
    security.require_csrf()
    data = request.json
    host = data.get("host", "8.8.8.8")
    return jsonify(firewall_manager.ping_host(host))

@app.route('/api/network/traceroute', methods=['POST'])
def api_network_traceroute():
    security.require_csrf()
    data = request.json
    host = data.get("host", "8.8.8.8")
    def target(job_id, h):
        jobs.update_job(job_id, progress=20, message=f"Trazando ruta a {h}...")
        result = firewall_manager.traceroute(h)
        return result
    job_id = jobs.run_in_background("traceroute", target, host)
    return jsonify({"job_id": job_id})

@app.route('/api/network/flush_dns', methods=['POST'])
def api_flush_dns():
    security.require_power()
    result = firewall_manager.flush_dns()
    audit.log_audit("flush_dns", "")
    return jsonify(result)

# -- API: Firewall --

@app.route('/api/firewall/status')
def api_firewall_status():
    return jsonify(firewall_manager.get_firewall_status())

@app.route('/api/firewall/rules')
def api_firewall_rules():
    direction = request.args.get("direction", "in")
    enabled_only = request.args.get("enabled_only", "false").lower() == "true"
    return jsonify(firewall_manager.list_firewall_rules(direction=direction, enabled_only=enabled_only))

@app.route('/api/firewall/rules/add', methods=['POST'])
def api_firewall_rule_add():
    security.require_power()
    data = request.json
    result = firewall_manager.add_firewall_rule(
        name=data.get("name"),
        direction=data.get("direction", "in"),
        action=data.get("action", "allow"),
        protocol=data.get("protocol", "tcp"),
        localport=data.get("localport", ""),
        remoteip=data.get("remoteip", ""),
        program=data.get("program", "")
    )
    audit.log_audit("firewall_rule_add", data.get("name"))
    return jsonify(result)

@app.route('/api/firewall/rules/delete', methods=['POST'])
def api_firewall_rule_delete():
    security.require_power()
    data = request.json
    result = firewall_manager.delete_firewall_rule(data.get("name"))
    audit.log_audit("firewall_rule_delete", data.get("name"))
    return jsonify(result)

@app.route('/api/firewall/rules/toggle', methods=['POST'])
def api_firewall_rule_toggle():
    security.require_power()
    data = request.json
    result = firewall_manager.toggle_firewall_rule(data.get("name"), data.get("enable", True))
    return jsonify(result)

@app.route('/api/firewall/profile', methods=['POST'])
def api_firewall_profile():
    security.require_power()
    data = request.json
    result = firewall_manager.set_firewall_profile(data.get("profile", "all"), data.get("state", "ON"))
    audit.log_audit("firewall_profile_change", f"{data.get('profile')}={data.get('state')}")
    return jsonify(result)

@app.route('/api/firewall/block_ip', methods=['POST'])
def api_firewall_block_ip():
    security.require_power()
    data = request.json
    ip = data.get("ip")
    direction = data.get("direction", "in")
    result = firewall_manager.block_ip(ip, direction)
    audit.log_audit("firewall_block_ip", f"{ip} {direction}")
    return jsonify(result)

@app.route('/api/firewall/unblock_ip', methods=['POST'])
def api_firewall_unblock_ip():
    security.require_power()
    data = request.json
    ip = data.get("ip")
    direction = data.get("direction", "in")
    result = firewall_manager.unblock_ip(ip, direction)
    audit.log_audit("firewall_unblock_ip", f"{ip} {direction}")
    return jsonify(result)

# -- API: Ports --

@app.route('/api/ports')
def api_ports_list():
    return jsonify(ports.list_active_ports())

# -- API: Jobs --

@app.route('/api/jobs')
def api_jobs_list():
    return jsonify(jobs.list_active_jobs())

@app.route('/api/jobs/<id>')
def api_job_status(id):
    job = jobs.get_job(id)
    if job:
        from dataclasses import asdict
        return jsonify(asdict(job))
    return jsonify({"error": "Job no encontrado"}), 404

@app.route('/api/jobs/<id>/cancel', methods=['POST'])
def api_job_cancel(id):
    security.require_csrf()
    jobs.update_job(id, status="cancelled", message="Cancelado por el usuario")
    return jsonify({"message": "Job cancelado"})

# -- API: Disk --

@app.route('/api/disk/clean', methods=['POST'])
def api_disk_clean():
    security.require_power()
    data = request.json
    mount = data.get("mountpoint")

    def target(job_id, m):
        def upd(**kw): jobs.update_job(job_id, **kw)
        return disk_manager.safe_clean_disk(m, job_update=upd)

    job_id = jobs.run_in_background("disk_safe_clean", target, mount)
    audit.log_audit("disk_clean_start", mount)
    return jsonify({"job_id": job_id})

@app.route('/api/disk/defrag', methods=['POST'])
def api_disk_defrag():
    security.require_power()
    data = request.json
    mount = data.get("mountpoint")

    def target(job_id, m):
        def upd(**kw): jobs.update_job(job_id, **kw)
        return disk_manager.defragment_disk(m, job_update=upd)

    job_id = jobs.run_in_background("disk_defrag", target, mount)
    audit.log_audit("disk_defrag_start", mount)
    return jsonify({"job_id": job_id})

@app.route('/api/disk/unlock', methods=['POST'])
def api_disk_unlock():
    security.require_power()
    data = request.json
    mount = data.get("mountpoint")
    password = data.get("password", "")
    recovery_key = data.get("recovery_key", "")
    result = disk_manager.unlock_disk(mount, password, recovery_key)
    audit.log_audit("disk_unlock", mount)
    return jsonify(result)

@app.route('/api/disk/create_partition', methods=['POST'])
def api_disk_create_partition():
    security.require_power()
    data = request.json
    disk_num = data.get("disk_number", 0)
    size_mb = data.get("size_mb", 1024)
    label = data.get("label", "Nueva")
    fs = data.get("fs", "NTFS")

    def target(job_id, dn, sm, lb, f):
        jobs.update_job(job_id, progress=30, message="Creando partición...")
        result = disk_manager.create_partition(dn, sm, lb, f)
        return result

    job_id = jobs.run_in_background("create_partition", target, disk_num, size_mb, label, fs)
    audit.log_audit("disk_create_partition", f"disk={disk_num} size={size_mb}MB")
    return jsonify({"job_id": job_id})

@app.route('/api/disk/physical')
def api_disk_physical():
    return jsonify(disk_manager.list_physical_disks())

@app.route('/api/disk/bitlocker/<drive>')
def api_disk_bitlocker(drive):
    return jsonify(disk_manager.get_bitlocker_status(drive))

# -- API: Scheduler --

@app.route('/api/scheduler/run/<id>', methods=['POST'])
def api_scheduler_run(id):
    security.require_csrf()
    if scheduler.run_task_now(id):
        audit.log_audit("scheduler_run_manual", id)
        return jsonify({"message": "Tarea iniciada"})
    return jsonify({"error": "Tarea no encontrada"}), 404

@app.route('/api/scheduler/delete/<id>', methods=['POST'])
def api_scheduler_delete(id):
    security.require_power()
    tasks = scheduler.load_tasks()
    new_tasks = [t for t in tasks if t["id"] != id]
    if len(new_tasks) < len(tasks):
        scheduler._tasks = new_tasks
        scheduler.save_tasks()
        audit.log_audit("scheduler_delete", id)
        return jsonify({"message": "Tarea eliminada"})
    return jsonify({"error": "Tarea no encontrada"}), 404

# -- API: Windows Activation --

@app.route('/api/activation/status')
def api_activation_status():
    return jsonify(windows_activation.get_activation_status())

@app.route('/api/activation/auto', methods=['POST'])
def api_activation_auto():
    security.require_power()

    def target(job_id):
        jobs.update_job(job_id, progress=20, message="Detectando edición de Windows...")
        result = windows_activation.auto_activate()
        return result

    job_id = jobs.run_in_background("win_activation", target)
    audit.log_audit("windows_activation_auto", "")
    return jsonify({"job_id": job_id})

@app.route('/api/activation/manual', methods=['POST'])
def api_activation_manual():
    security.require_power()
    data = request.json
    key = data.get("key", "").strip()
    if not key:
        return jsonify({"error": "Se requiere una clave de producto."}), 400

    def target(job_id, k):
        jobs.update_job(job_id, progress=30, message="Instalando clave de producto...")
        result = windows_activation.activate_with_key(k)
        return result

    job_id = jobs.run_in_background("win_activation_manual", target, key)
    audit.log_audit("windows_activation_manual", "key=***")
    return jsonify({"job_id": job_id})

@app.route('/api/activation/keys')
def api_activation_keys():
    return jsonify(windows_activation.list_available_keys())

# -- API: PC Health --

@app.route('/api/health/scan', methods=['POST'])
def api_health_scan():
    security.require_csrf()

    def target(job_id):
        def upd(**kw): jobs.update_job(job_id, **kw)
        return pc_health.full_health_scan(job_update=upd)

    job_id = jobs.run_in_background("health_scan", target)
    audit.log_audit("health_full_scan", "")
    return jsonify({"job_id": job_id})

@app.route('/api/health/sfc', methods=['POST'])
def api_health_sfc():
    security.require_power()

    def target(job_id):
        def upd(**kw): jobs.update_job(job_id, **kw)
        return pc_health.check_system_files(job_update=upd)

    job_id = jobs.run_in_background("sfc_scan", target)
    audit.log_audit("health_sfc", "")
    return jsonify({"job_id": job_id})

@app.route('/api/health/dism', methods=['POST'])
def api_health_dism():
    security.require_power()

    def target(job_id):
        def upd(**kw): jobs.update_job(job_id, **kw)
        return pc_health.repair_system_image(job_update=upd)

    job_id = jobs.run_in_background("dism_repair", target)
    audit.log_audit("health_dism", "")
    return jsonify({"job_id": job_id})

@app.route('/api/health/winsock', methods=['POST'])
def api_health_winsock():
    security.require_power()

    def target(job_id):
        def upd(**kw): jobs.update_job(job_id, **kw)
        return pc_health.fix_winsock(job_update=upd)

    job_id = jobs.run_in_background("winsock_fix", target)
    audit.log_audit("health_winsock", "")
    return jsonify({"job_id": job_id})

@app.route('/api/health/clear_logs', methods=['POST'])
def api_health_clear_logs():
    security.require_power()

    def target(job_id):
        def upd(**kw): jobs.update_job(job_id, **kw)
        return pc_health.clear_event_logs(job_update=upd)

    job_id = jobs.run_in_background("clear_event_logs", target)
    audit.log_audit("health_clear_logs", "")
    return jsonify({"job_id": job_id})

@app.route('/api/health/startup')
def api_health_startup():
    return jsonify(pc_health.optimize_startup())

# -- HTML: Terminal --

@app.route('/terminal')
def terminal_page():
    return render_template('terminal.html',
                           active_page='terminal',
                           power_enabled=security.is_power_actions_enabled())

# -- HTML: File Explorer --

@app.route('/explorer')
def explorer_page():
    return render_template('explorer.html',
                           active_page='explorer',
                           power_enabled=security.is_power_actions_enabled())

# -- HTML: Customization (System Config) --

@app.route('/customization')
def customization_page():
    return render_template('customization.html',
                           active_page='customization',
                           power_enabled=security.is_power_actions_enabled())

# -- HTML: OS Recommender --

@app.route('/os-recommend')
def os_recommend_page():
    data = os_recommender.recommend_os()
    evaluation = os_recommender.evaluate_current_os()
    return render_template('os_recommend.html',
                           active_page='os_recommend',
                           specs=data['specs'],
                           recommendations=data['recommendations'],
                           evaluation=evaluation,
                           power_enabled=security.is_power_actions_enabled())

# -- HTML: Programs --

@app.route('/programs')
def programs_page():
    return render_template('programs.html',
                           active_page='programs',
                           power_enabled=security.is_power_actions_enabled())

# -- HTML: Drivers --

@app.route('/drivers')
def drivers_page():
    return render_template('drivers.html',
                           active_page='drivers',
                           power_enabled=security.is_power_actions_enabled())

# -- HTML: VirusTotal / Security Scanner --

@app.route('/scanner')
def scanner_page():
    has_key = bool(virustotal_scanner._get_api_key())
    return render_template('scanner.html',
                           active_page='scanner',
                           has_vt_key=has_key,
                           power_enabled=security.is_power_actions_enabled())

# -- API: Admin --

@app.route('/api/admin/status')
def api_admin_status():
    return jsonify(admin_helper.get_admin_status())

@app.route('/api/admin/elevate', methods=['POST'])
def api_admin_elevate():
    security.require_csrf()
    result = admin_helper.restart_as_admin(exit_current=True, exit_delay=1.5)
    return jsonify(result), (200 if result.get("ok") else 400)

# -- API: OS Recommender --

@app.route('/api/os-recommend')
def api_os_recommend():
    return jsonify(os_recommender.recommend_os())

# -- API: Programs --

@app.route('/api/programs')
def api_programs_list():
    return jsonify(program_manager.list_installed_programs())

@app.route('/api/programs/search')
def api_programs_search():
    q = request.args.get('q', '')
    return jsonify(program_manager.search_programs(q))

@app.route('/api/programs/uninstall', methods=['POST'])
def api_programs_uninstall():
    security.require_power()
    data = request.json
    name = data.get('name', '')
    quiet = data.get('quiet', True)

    def target(job_id, n, q):
        jobs.update_job(job_id, progress=30, message=f"Desinstalando {n}...")
        return program_manager.uninstall_program(n, q)

    job_id = jobs.run_in_background("uninstall_program", target, name, quiet)
    audit.log_audit("program_uninstall", name)
    return jsonify({"job_id": job_id})

# -- API: Drivers --

@app.route('/api/drivers')
def api_drivers_list():
    return jsonify(driver_manager.list_drivers())

@app.route('/api/drivers/devices')
def api_drivers_devices():
    return jsonify(driver_manager.list_devices())

@app.route('/api/drivers/install', methods=['POST'])
def api_drivers_install():
    security.require_power()
    data = request.json
    inf = data.get('inf_path', '')

    def target(job_id, p):
        jobs.update_job(job_id, progress=40, message=f"Instalando driver {p}...")
        return driver_manager.install_driver(p)

    job_id = jobs.run_in_background("install_driver", target, inf)
    audit.log_audit("driver_install", inf)
    return jsonify({"job_id": job_id})

@app.route('/api/drivers/remove', methods=['POST'])
def api_drivers_remove():
    security.require_power()
    data = request.json
    name = data.get('name', '')
    force = data.get('force', False)
    result = driver_manager.remove_driver(name, force)
    audit.log_audit("driver_remove", name)
    return jsonify(result)

@app.route('/api/drivers/scan', methods=['POST'])
def api_drivers_scan_hw():
    security.require_csrf()
    return jsonify(driver_manager.scan_hardware_changes())

@app.route('/api/drivers/export', methods=['POST'])
def api_drivers_export():
    security.require_power()
    data = request.json
    out_dir = data.get('output_dir', str(config.DATA_DIR / 'driver_backup'))

    def target(job_id, d):
        jobs.update_job(job_id, progress=20, message="Exportando drivers...")
        return driver_manager.export_drivers(d)

    job_id = jobs.run_in_background("export_drivers", target, out_dir)
    return jsonify({"job_id": job_id})

# -- API: VirusTotal / Scanner --

@app.route('/api/scanner/file', methods=['POST'])
def api_scanner_file():
    security.require_csrf()
    data = request.json
    path = data.get('path', '')
    use_vt = data.get('use_vt', False)

    if use_vt:
        return jsonify(virustotal_scanner.scan_file_vt(path))
    else:
        return jsonify(virustotal_scanner.local_scan_file(path))

@app.route('/api/scanner/url', methods=['POST'])
def api_scanner_url():
    security.require_csrf()
    data = request.json
    url = data.get('url', '')
    return jsonify(virustotal_scanner.scan_url_vt(url))

@app.route('/api/scanner/hash', methods=['POST'])
def api_scanner_hash():
    security.require_csrf()
    data = request.json
    h = data.get('hash', '')
    return jsonify(virustotal_scanner.lookup_hash_vt(h))

@app.route('/api/scanner/dir', methods=['POST'])
def api_scanner_dir():
    security.require_csrf()
    data = request.json
    path = data.get('path', '')

    def target(job_id, p):
        jobs.update_job(job_id, progress=10, message=f"Escaneando {p}...")
        return virustotal_scanner.local_scan_directory(p)

    job_id = jobs.run_in_background("scan_directory", target, path)
    return jsonify({"job_id": job_id})

# -- API: Terminal --

@app.route('/api/terminal/start', methods=['POST'])
def api_terminal_start():
    security.require_csrf()
    data = request.json
    shell = data.get('shell', 'powershell')
    sid = terminal_manager.create_session(shell)
    return jsonify({"session_id": sid})

@app.route('/api/terminal/write', methods=['POST'])
def api_terminal_write():
    security.require_csrf()
    data = request.json
    sid = data.get('session_id', '')
    cmd = data.get('command', '')
    if terminal_manager.write_to_session(sid, cmd):
        return jsonify({"ok": True})
    return jsonify({"error": "Sesión no encontrada o inactiva"}), 404

@app.route('/api/terminal/read', methods=['POST'])
def api_terminal_read():
    # Only block CSRF if really needed, but it's a polling route so maybe not to spam errors
    # security.require_csrf() is better though
    data = request.json
    sid = data.get('session_id', '')
    out = terminal_manager.read_from_session(sid)
    return jsonify({"output": out})

# -- API: File Explorer --

@app.route('/api/explorer/list', methods=['POST'])
def api_explorer_list():
    security.require_csrf()
    data = request.json
    return jsonify(file_manager.list_directory(data.get('path', 'C:\\')))

@app.route('/api/explorer/move', methods=['POST'])
def api_explorer_move():
    security.require_power()
    data = request.json
    src = data.get('src')
    dst = data.get('dst')
    return jsonify(file_manager.move_item(src, dst))

@app.route('/api/explorer/extract', methods=['POST'])
def api_explorer_extract():
    security.require_power()
    data = request.json
    return jsonify(file_manager.extract_archive(data.get('path')))

@app.route('/api/explorer/openwith', methods=['POST'])
def api_explorer_openwith():
    security.require_csrf()
    data = request.json
    return jsonify(file_manager.open_with(data.get('path'), data.get('app', '7z')))

# -- API: Windows Customization --

@app.route('/api/system/wallpaper', methods=['POST'])
def api_system_wallpaper():
    security.require_csrf()
    data = request.json
    return jsonify(windows_customization.change_wallpaper(data.get('path', '')))

@app.route('/api/system/password', methods=['POST'])
def api_system_password():
    security.require_power()
    data = request.json
    return jsonify(windows_customization.change_password(data.get('username', ''), data.get('password', '')))

@app.route('/api/system/win11')
def api_system_win11():
    return jsonify(windows_customization.check_win11_upgrade())

@app.route('/api/system/update', methods=['POST'])
def api_system_update():
    security.require_csrf()
    return jsonify(windows_customization.trigger_windows_update())

# -- Error handling --

@app.errorhandler(Exception)
def handle_global_exception(e):
    audit.log_audit("system_error", str(type(e).__name__), "error", {"message": str(e)})
    if request.path.startswith('/api/'):
        return jsonify({"error": f"{type(e).__name__}: {str(e)}"}), 500
    return render_template('base.html', title="Error", content=f"Ocurrió un error inesperado: {str(e)}"), 500

def main(open_browser: bool = True, debug: bool | None = None):
    """Start the Flask UI used by `spv ui` and `spv-ui`."""
    if debug is None:
        debug = os.getenv("SPV_DEBUG", "false").lower() in {"1", "true", "yes", "on"}

    url = f"http://{config.HOST}:{config.PORT}"
    print(f"Iniciando {config.APP_NAME} en {url}")

    # Avoid opening two tabs when Flask reloader is enabled.
    if open_browser and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    app.run(host=config.HOST, port=config.PORT, debug=debug)


if __name__ == '__main__':
    main()
