/**
 * core.js — SPV 3.0 Global JS
 * Handles: modal, apiCall, notifications, theme, toast alerts
 */

// ─────────────────────────────────────────
// MODAL — smart confirmation
// ─────────────────────────────────────────
let _modalResolver = null;

/**
 * showModal(title, message, confirmPhrase, onConfirm)
 * confirmPhrase: string to type, or null/false to skip phrase.
 * The modal checks the global SPV_REQUIRE_CONFIRM setting.
 */
function showModal(title, message, confirmPhrase, onConfirm) {
    const overlay = document.getElementById('global-modal-overlay');
    const titleEl = document.getElementById('modal-title');
    const msgEl = document.getElementById('modal-message');
    const inputContainer = document.getElementById('modal-confirm-input-container');
    const phraseEl = document.getElementById('confirm-phrase-bold');
    const input = document.getElementById('modal-confirm-input');
    const actionBtn = document.getElementById('modal-btn-action');

    titleEl.innerText = title;
    msgEl.innerText = message;
    input.value = '';

    // Check if server-side require_confirm is enabled
    // We read it from a hidden meta tag set in base.html
    const serverRequiresConfirm = (document.querySelector('meta[name="require-confirm"]')?.content === 'true');
    const showInput = confirmPhrase && serverRequiresConfirm;

    if (showInput) {
        inputContainer.style.display = 'block';
        if (phraseEl) phraseEl.textContent = confirmPhrase;
        input.placeholder = confirmPhrase;
    } else {
        inputContainer.style.display = 'none';
    }

    actionBtn.onclick = () => {
        if (showInput && input.value.trim().toUpperCase() !== confirmPhrase.toUpperCase()) {
            showToast(`Escribe "${confirmPhrase}" para confirmar.`, 'error');
            return;
        }
        onConfirm(showInput ? input.value.trim() : confirmPhrase || '');
        closeModal();
    };

    overlay.style.display = 'flex';
    if (showInput) setTimeout(() => input.focus(), 100);
}

function closeModal() {
    document.getElementById('global-modal-overlay').style.display = 'none';
}

// Close modal on overlay click
document.getElementById('global-modal-overlay')?.addEventListener('click', function(e) {
    if (e.target === this) closeModal();
});

// ─────────────────────────────────────────
// TOAST NOTIFICATIONS
// ─────────────────────────────────────────
function showToast(message, type = 'info', duration = 4000) {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position:fixed;bottom:2rem;right:2rem;z-index:9999;display:flex;flex-direction:column;gap:0.5rem;';
        document.body.appendChild(container);
    }

    const icons = { info: 'fa-info-circle', success: 'fa-check-circle', error: 'fa-exclamation-circle', warning: 'fa-triangle-exclamation' };
    const colors = { info: '#3b82f6', success: '#22c55e', error: '#ef4444', warning: '#f59e0b' };

    const toast = document.createElement('div');
    toast.style.cssText = `
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-left: 4px solid ${colors[type] || colors.info};
        color: var(--text-color);
        padding: 0.9rem 1.2rem;
        border-radius: 12px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
        display: flex;
        align-items: center;
        gap: 0.75rem;
        font-size: 0.88rem;
        max-width: 360px;
        animation: toastIn 0.3s cubic-bezier(.175,.885,.32,1.275);
        cursor: pointer;
    `;
    toast.innerHTML = `<i class="fas ${icons[type] || icons.info}" style="color:${colors[type]};font-size:1rem;"></i><span>${message}</span>`;
    toast.onclick = () => toast.remove();
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'toastOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Inject toast keyframes once
if (!document.getElementById('toast-keyframes')) {
    const style = document.createElement('style');
    style.id = 'toast-keyframes';
    style.textContent = `
        @keyframes toastIn { from { opacity:0; transform:translateY(1rem) scale(0.9); } to { opacity:1; transform:none; } }
        @keyframes toastOut { from { opacity:1; transform:none; } to { opacity:0; transform:translateY(1rem) scale(0.9); } }
    `;
    document.head.appendChild(style);
}

// ─────────────────────────────────────────
// API CALL
// ─────────────────────────────────────────
async function apiCall(url, method = 'GET', body = null) {
    const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrf
        }
    };
    if (body) options.body = JSON.stringify(body);

    const response = await fetch(url, options);
    const contentType = response.headers.get("content-type") || '';

    if (!response.ok) {
        let errMsg = `Error ${response.status}`;
        if (contentType.includes("application/json")) {
            const data = await response.json();
            errMsg = data.error || data.message || errMsg;
        } else {
            errMsg = `Error ${response.status}: El servidor no devolvió JSON.`;
        }
        showToast(errMsg, 'error');
        throw new Error(errMsg);
    }

    if (contentType.includes("application/json")) {
        return await response.json();
    }
    return { message: "OK" };
}

// ─────────────────────────────────────────
// JOB POLLER — non-blocking
// ─────────────────────────────────────────
function pollJob(jobId, onDone, onError, onProgress) {
    let attempts = 0;
    const interval = setInterval(async () => {
        attempts++;
        if (attempts > 300) { // 10 min max
            clearInterval(interval);
            return;
        }
        try {
            const job = await apiCall(`/api/jobs/${jobId}`);
            if (onProgress) onProgress(job);
            if (job.status === 'done') {
                clearInterval(interval);
                if (onDone) onDone(job);
                showToast(`Tarea completada`, 'success');
            } else if (job.status === 'error') {
                clearInterval(interval);
                if (onError) onError(job);
                showToast(`Error en tarea: ${job.error}`, 'error');
            } else if (job.status === 'cancelled') {
                clearInterval(interval);
            }
        } catch (e) {
            clearInterval(interval);
        }
    }, 2000);
    return interval;
}

// ─────────────────────────────────────────
// NOTIFICATIONS
// ─────────────────────────────────────────
function toggleNotifications() {
    const panel = document.getElementById('notifications-panel');
    if (panel.style.display === 'flex') {
        panel.style.display = 'none';
    } else {
        loadNotifications();
        panel.style.display = 'flex';
    }
}

async function loadNotifications() {
    const list = document.getElementById('notif-list');
    list.innerHTML = '<div style="padding:1rem;text-align:center;color:#999;">Cargando...</div>';
    try {
        const data = await apiCall('/api/notifications');
        list.innerHTML = '';
        if (!data.length) {
            list.innerHTML = '<div style="padding:1rem;text-align:center;color:#999;">Sin notificaciones</div>';
            return;
        }
        data.forEach(n => {
            const div = document.createElement('div');
            div.className = `notif-item ${n.read ? 'read' : 'unread'}`;
            div.innerHTML = `
                <div style="font-weight:600;font-size:0.85rem;">${n.title}</div>
                <div style="font-size:0.8rem;color:var(--text-secondary);margin:4px 0;">${n.message}</div>
                <div style="font-size:0.7rem;color:#999;display:flex;justify-content:space-between;align-items:center;">
                    <span>${(n.time||'').replace('T',' ').split('.')[0]}</span>
                    ${!n.read ? `<button class="btn btn-sm" onclick="markRead('${n.id}',event)" style="padding:2px 8px;font-size:0.65rem;">Leída</button>` : ''}
                </div>`;
            if (n.url) { div.style.cursor = 'pointer'; div.onclick = () => window.location = n.url; }
            list.appendChild(div);
        });
    } catch (e) {}
}

async function markRead(id, event) {
    if (event) event.stopPropagation();
    await apiCall(`/api/notifications/${id}/read`, 'POST');
    loadNotifications();
    pollNotifications();
}

async function pollNotifications() {
    try {
        const data = await apiCall('/api/notifications/unread');
        const count = data.length;
        const el = document.getElementById('notif-count');
        if (el) {
            el.innerText = count;
            el.style.display = count > 0 ? 'flex' : 'none';
        }
    } catch (e) {}
}
setInterval(pollNotifications, 15000);
pollNotifications();

// ─────────────────────────────────────────
// ─────────────────────────────────────────
// THEME
// ─────────────────────────────────────────
function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.body.className = theme === 'dark' ? 'dark-theme' : '';
    localStorage.setItem('spv-theme', theme);
    const icon = document.getElementById('theme-icon');
    if (icon) icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    apiCall('/api/settings/theme', 'POST', { theme }).catch(() => {});
}

(function initTheme() {
    const saved = localStorage.getItem('spv-theme') || 'dark';
    setTheme(saved);
})();

// ─────────────────────────────────────────
// ADMIN ELEVATION
// ─────────────────────────────────────────
async function checkAdminStatus() {
    try {
        const res = await apiCall('/api/admin/status');
        const badge = document.getElementById('admin-badge');
        const btn = document.getElementById('btn-elevate');
        if (badge && btn) {
            if (res.is_admin) {
                badge.style.display = 'inline-flex';
                badge.className = 'badge badge-warning';
                badge.innerHTML = '<i class="fas fa-crown"></i> Admin';
                btn.style.display = 'none';
            } else {
                badge.style.display = 'none';
                btn.style.display = 'block';
            }
        }
    } catch (e) {}
}

async function elevateAdmin() {
    showModal('Elevar Privilegios', '¿Deseas reiniciar la aplicación como Administrador? (Aparecerá el prompt de UAC)', null, async () => {
        try {
            const res = await apiCall('/api/admin/elevate', 'POST');
            if (res.ok) {
                showToast(res.message || 'Reiniciando como administrador...', 'info');
                setTimeout(() => location.reload(), 4500);
            } else {
                showToast(res.message || 'No se pudo elevar privilegios.', 'error');
            }
        } catch (e) {
            showToast(e.message || 'Error al elevar privilegios', 'error');
        }
    });
}

checkAdminStatus();

