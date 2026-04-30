const csrf = window.SPV.csrf;
const state = { processes: [], system: null, ports: {ports: [], managed: [], proxies: []}, history: { cpu: [], ram: [], disk: [] } };

const $ = (id) => document.getElementById(id);

function api(path, opts = {}) {
  opts.headers = Object.assign({
    "Content-Type": "application/json",
    "X-CSRF-Token": csrf
  }, opts.headers || {});
  return fetch(path, opts).then(async r => {
    const text = await r.text();
    let data;
    try { data = JSON.parse(text); } catch { data = { raw: text }; }
    if (!r.ok) throw new Error(data.error || data.raw || r.statusText);
    return data;
  });
}

function pct(n){ return `${Number(n || 0).toFixed(1)}%`; }

function pushHist(key, val) {
  const arr = state.history[key];
  arr.push(Number(val || 0));
  while (arr.length > 60) arr.shift();
}

function drawChart(id, values) {
  const c = $(id);
  const ctx = c.getContext("2d");
  const w = c.width = c.clientWidth * devicePixelRatio;
  const h = c.height = c.clientHeight * devicePixelRatio;
  ctx.clearRect(0,0,w,h);
  ctx.lineWidth = 2 * devicePixelRatio;
  ctx.beginPath();
  if (!values.length) return;
  values.forEach((v,i) => {
    const x = values.length === 1 ? 0 : i * (w/(values.length-1));
    const y = h - (Math.max(0, Math.min(100, v))/100) * h;
    if (i === 0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
  });
  ctx.stroke();
}

function renderSystem(data) {
  state.system = data;
  $("cpuPct").textContent = pct(data.cpu.percent);
  $("ramPct").textContent = pct(data.memory.percent);
  const diskMax = Math.max(0, ...data.disk.partitions.map(p => Number(p.percent || 0)));
  $("diskPct").textContent = pct(diskMax);
  $("powerStatus").textContent = data.power_actions_enabled ? "power actions ON" : "modo seguro";
  $("powerStatus").style.background = data.power_actions_enabled ? "#111" : "#fafafa";
  $("powerStatus").style.color = data.power_actions_enabled ? "#fff" : "#111";

  pushHist("cpu", data.cpu.percent);
  pushHist("ram", data.memory.percent);
  pushHist("disk", diskMax);
  drawChart("cpuChart", state.history.cpu);
  drawChart("ramChart", state.history.ram);
  drawChart("diskChart", state.history.disk);

  $("systemInfo").innerHTML = [
    ["Host", data.hostname],
    ["Sistema", `${data.platform} · ${data.machine}`],
    ["CPU", `${data.cpu.physical_cores || "?"} físicos / ${data.cpu.logical_cores || "?"} lógicos`],
    ["Frecuencia", data.cpu.freq_current ? `${data.cpu.freq_current} MHz` : "N/D"],
    ["RAM", `${data.memory.used} / ${data.memory.total}`],
    ["Swap", `${data.memory.swap_used} / ${data.memory.swap_total}`],
    ["Boot", data.boot_time],
    ["Python", data.python],
  ].map(([k,v]) => `<div><span>${escapeHtml(k)}</span><strong>${escapeHtml(v)}</strong></div>`).join("");

  $("diskList").innerHTML = data.disk.partitions.map(p => `
    <div class="disk">
      <strong>${escapeHtml(p.mountpoint)}</strong>
      <p class="muted">${escapeHtml(p.device)} · ${escapeHtml(p.fstype)} · ${p.used}/${p.total}</p>
      <div class="bar"><i style="width:${Number(p.percent||0)}%"></i></div>
    </div>
  `).join("");
}

function renderProcesses() {
  const q = $("search").value.trim().toLowerCase();
  const rf = $("riskFilter").value;
  let rows = state.processes.filter(p => {
    const hay = [
      p.pid, p.name, p.username, p.status, p.exe, (p.cmdline || []).join(" ")
    ].join(" ").toLowerCase();
    return (!q || hay.includes(q)) && (!rf || p.risk_label === rf);
  });
  const risky = state.processes.filter(p => ["medium","high","critical"].includes(p.risk_label)).length;
  $("riskCount").textContent = risky;

  $("processRows").innerHTML = rows.map(p => `
    <tr>
      <td><span class="risk ${p.risk_label}" title="${escapeHtml((p.risk_reasons||[]).join(" · "))}">${p.risk_score} ${p.risk_label}</span></td>
      <td>${p.pid}</td>
      <td>
        <div class="proc-name">${escapeHtml(p.name || "(sin nombre)")}${p.protected ? " · protegido" : ""}</div>
        <div class="path" title="${escapeHtml(p.exe || "")}">${escapeHtml(p.exe || (p.cmdline||[]).join(" ") || "N/D")}</div>
      </td>
      <td>${pct(p.cpu_percent)}</td>
      <td>${pct(p.memory_percent)}<div class="muted">${escapeHtml(p.memory_rss || "")}</div></td>
      <td>${escapeHtml(p.username || "")}</td>
      <td>${escapeHtml(p.status || "")}</td>
      <td>${p.connections_count || 0}</td>
      <td class="actions">
        <button class="btn ghost mini" onclick="showProcess(${p.pid})">Info</button>
        <button class="btn ghost mini" ${p.protected ? "disabled" : ""} onclick="terminateProcess(${p.pid}, '${escapeJs(p.name || "")}')">Terminar</button>
        <button class="btn danger mini" ${p.protected ? "disabled" : ""} onclick="killProcess(${p.pid}, '${escapeJs(p.name || "")}')">Kill</button>
      </td>
    </tr>
  `).join("");
}

async function refreshSystem(){
  try { renderSystem(await api("/api/system")); }
  catch(e){ console.error(e); }
}

async function refreshProcesses(){
  try {
    const data = await api("/api/processes");
    state.processes = data.processes || [];
    renderProcesses();
  } catch(e){ console.error(e); }
}

async function refreshJobs(){
  try {
    const data = await api("/api/jobs");
    $("jobs").innerHTML = (data.jobs || []).map(j => `
      <div class="job">
        <div class="job-head">
          <strong>${escapeHtml(j.kind)} · ${escapeHtml(j.status)}</strong>
          <span class="muted">${escapeHtml(j.updated_at || "")}</span>
        </div>
        <div class="progress"><i style="width:${Number(j.progress||0)}%"></i></div>
        <div class="muted">${escapeHtml(j.message || "")}${j.error ? " · " + escapeHtml(j.error) : ""}</div>
        ${j.result && Object.keys(j.result).length ? `<pre class="console">${escapeHtml(JSON.stringify(j.result, null, 2))}</pre>` : ""}
      </div>
    `).join("") || `<p class="muted">Sin jobs recientes.</p>`;
  } catch(e){ console.error(e); }
}

async function refreshAll(){
  await Promise.all([refreshSystem(), refreshProcesses(), refreshJobs(), refreshPorts()]);
}

async function showProcess(pid){
  try {
    const data = await api(`/api/process/${pid}`);
    $("modalTitle").textContent = `${data.name || "Proceso"} · PID ${pid}`;
    $("modalBody").textContent = JSON.stringify(data, null, 2);
    $("modal").showModal();
  } catch(e){ alert(e.message); }
}

async function terminateProcess(pid, name){
  const c = prompt(`Escribe TERMINAR para finalizar PID ${pid} (${name}).`);
  if (c !== "TERMINAR") return;
  try {
    const data = await api(`/api/process/${pid}/terminate`, {method:"POST", body: JSON.stringify({confirm:"TERMINAR"})});
    alert(JSON.stringify(data, null, 2));
    refreshProcesses();
  } catch(e){ alert(e.message); }
}

async function killProcess(pid, name){
  const c = prompt(`Acción fuerte. Escribe MATAR para kill PID ${pid} (${name}).`);
  if (c !== "MATAR") return;
  try {
    const data = await api(`/api/process/${pid}/kill`, {method:"POST", body: JSON.stringify({confirm:"MATAR"})});
    alert(JSON.stringify(data, null, 2));
    refreshProcesses();
  } catch(e){ alert(e.message); }
}

function out(x){
  $("toolOutput").textContent = typeof x === "string" ? x : JSON.stringify(x, null, 2);
}

async function scanCleanup(){
  try {
    const data = await api("/api/cleanup/scan", {
      method:"POST",
      body: JSON.stringify({min_age_hours: Number($("cleanAge").value || 24)})
    });
    out(data);
  } catch(e){ out(e.message); }
}

async function runCleanup(){
  const c = prompt("Escribe LIMPIAR para borrar temporales seguros detectados.");
  if (c !== "LIMPIAR") return;
  try {
    const data = await api("/api/cleanup/run", {
      method:"POST",
      body: JSON.stringify({confirm:"LIMPIAR", min_age_hours: Number($("cleanAge").value || 24)})
    });
    out(data);
    setTimeout(refreshJobs, 800);
  } catch(e){ out(e.message); }
}

async function memOptimize(){
  try {
    const data = await api("/api/memory/optimize", {method:"POST", body: JSON.stringify({})});
    out(data);
    setTimeout(refreshJobs, 800);
  } catch(e){ out(e.message); }
}

async function diskOptimize(){
  const phrase = "OPTIMIZAR";
  const c = prompt(`Escribe ${phrase} para ejecutar análisis/optimización de disco según plataforma.`);
  if (c !== phrase) return;
  try {
    const data = await api("/api/disk/optimize", {
      method:"POST",
      body: JSON.stringify({
        confirm: phrase,
        drive: $("driveInput").value,
        mode: $("diskMode").value
      })
    });
    out(data);
    setTimeout(refreshJobs, 800);
  } catch(e){ out(e.message); }
}


async function scanDesktop(){
  try {
    const data = await api("/api/desktop-junk/scan", {
      method:"POST",
      body: JSON.stringify({min_age_hours: Number($("desktopAge").value || 72)})
    });
    out(data);
  } catch(e){ out(e.message); }
}

async function runDesktop(){
  const c = prompt("Escribe DESKTOP para mover basura inteligente del Desktop a cuarentena.");
  if (c !== "DESKTOP") return;
  try {
    const data = await api("/api/desktop-junk/run", {
      method:"POST",
      body: JSON.stringify({confirm:"DESKTOP", min_age_hours: Number($("desktopAge").value || 72)})
    });
    out(data);
    setTimeout(refreshJobs, 800);
  } catch(e){ out(e.message); }
}

function renderPortNotice(data){
  const box = $("portNotice");
  if (!data || !data.message) { box.classList.add("hidden"); return; }
  const url = data.open_url || (data.launched && data.launched.url) || "";
  box.classList.remove("hidden");
  box.innerHTML = `<div><strong>${escapeHtml(data.message)}</strong><p class="muted">Preferido: ${escapeHtml(data.preferred_port)} · Asignado: ${escapeHtml(data.assigned_port)}</p></div>${url ? `<a class="btn" target="_blank" href="${escapeHtml(url)}">Abrir</a>` : ""}`;
  try {
    if ("Notification" in window) {
      const send = () => {
        const n = new Notification("Port Protect", { body: data.message, tag: "spv-port-protect" });
        n.onclick = () => { if (url) window.open(url, "_blank"); };
      };
      if (Notification.permission === "granted") send();
      else if (Notification.permission !== "denied") Notification.requestPermission().then(p => { if (p === "granted") send(); });
    }
  } catch(e) { console.debug(e); }
}

async function refreshPorts(){
  try {
    const data = await api("/api/ports");
    state.ports = data;
    renderPorts();
  } catch(e){ console.error(e); }
}

function renderPorts(){
  const q = ($("portSearch")?.value || "").trim().toLowerCase();
  const ports = (state.ports.ports || []).filter(p => {
    const hay = [p.port, p.pid, p.process, p.exe, p.status, p.ip].join(" ").toLowerCase();
    return !q || hay.includes(q);
  });
  $("portRows").innerHTML = ports.map(p => `
    <tr>
      <td><strong>${p.port}</strong><div class="muted"><a target="_blank" href="${escapeHtml(p.url)}">abrir</a></div></td>
      <td>${escapeHtml(p.ip)}</td>
      <td>${escapeHtml(p.status || "")}${p.is_listen ? " · listen" : ""}</td>
      <td>${escapeHtml(p.pid || "")}</td>
      <td><div class="proc-name">${escapeHtml(p.process || "N/D")}</div></td>
      <td><div class="path" title="${escapeHtml(p.exe || "")}">${escapeHtml(p.exe || (p.cmdline||[]).join(" ") || "")}</div></td>
      <td class="actions">${p.pid ? `<button class="btn danger mini" onclick="stopPortOwner(${p.pid}, ${p.port})">Detener</button>` : ""}</td>
    </tr>
  `).join("");

  $("managedPorts").innerHTML = (state.ports.managed || []).map(m => `
    <div class="job">
      <div class="job-head"><strong>PID ${escapeHtml(m.pid)} · puerto ${escapeHtml(m.port)}</strong><span class="pill">${m.running ? "running" : "stopped"}</span></div>
      <div class="muted">${escapeHtml(m.command)}</div>
      <div class="port-open"><a class="btn ghost mini" target="_blank" href="${escapeHtml(m.url)}">Abrir</a><button class="btn danger mini" onclick="stopManaged('${escapeJs(m.id)}')">Detener</button></div>
    </div>
  `).join("") || `<p class="muted">Sin apps lanzadas desde SPV.</p>`;

  $("proxyPorts").innerHTML = (state.ports.proxies || []).map(p => `
    <div class="job">
      <div class="job-head"><strong>${escapeHtml(p.listen_port)} → ${escapeHtml(p.target_port)}</strong><span class="pill">${p.active ? "active" : "stopped"}</span></div>
      <div class="muted">${escapeHtml(p.url)} → ${escapeHtml(p.target_url)} ${p.error ? " · " + escapeHtml(p.error) : ""}</div>
      <div class="port-open"><a class="btn ghost mini" target="_blank" href="${escapeHtml(p.url)}">Abrir</a><button class="btn danger mini" onclick="stopProxy('${escapeJs(p.id)}')">Detener</button></div>
    </div>
  `).join("") || `<p class="muted">Sin proxies activos.</p>`;
}

async function findFreePort(){
  try {
    const start = Number($("preferredPort").value || 5000);
    const data = await api(`/api/ports/free?start=${encodeURIComponent(start)}`);
    renderPortNotice({message:`Puerto libre encontrado: ${data.port}`, preferred_port:start, assigned_port:data.port, open_url:data.url});
    $("preferredPort").value = data.port;
  } catch(e){ alert(e.message); }
}

async function launchPort(){
  const c = prompt("Escribe LANZAR para ejecutar el comando con PORT automático.");
  if (c !== "LANZAR") return;
  try {
    const data = await api("/api/ports/launch", {
      method:"POST",
      body: JSON.stringify({
        confirm:"LANZAR",
        preferred_port: Number($("preferredPort").value || 5000),
        command: $("launchCommand").value,
        cwd: $("launchCwd").value || null
      })
    });
    renderPortNotice(data);
    refreshPorts();
  } catch(e){ alert(e.message); }
}

async function protectOnly(){
  const command = ($("launchCommand").value || "").trim();
  const confirm = command ? prompt("Escribe PROTEGER para lanzar con resolución de puerto.") : null;
  if (command && confirm !== "PROTEGER") return;
  try {
    const payload = {
      preferred_port: Number($("preferredPort").value || 5000),
      command,
      cwd: $("launchCwd").value || null
    };
    if (command) payload.confirm = "PROTEGER";
    const data = await api("/api/ports/protect", {method:"POST", body: JSON.stringify(payload)});
    renderPortNotice(data);
    refreshPorts();
  } catch(e){ alert(e.message); }
}

async function stopManaged(id){
  const c = prompt("Escribe DETENER para parar esta app lanzada por SPV.");
  if (c !== "DETENER") return;
  try {
    await api("/api/ports/managed/stop", {method:"POST", body: JSON.stringify({confirm:"DETENER", managed_id:id})});
    refreshPorts();
  } catch(e){ alert(e.message); }
}

async function stopProxy(id){
  const c = prompt("Escribe DETENER para parar este proxy.");
  if (c !== "DETENER") return;
  try {
    await api("/api/ports/proxy/stop", {method:"POST", body: JSON.stringify({confirm:"DETENER", proxy_id:id})});
    refreshPorts();
  } catch(e){ alert(e.message); }
}

async function stopPortOwner(pid, port){
  const c = prompt(`Escribe DETENER para terminar el proceso PID ${pid} que usa el puerto ${port}.`);
  if (c !== "DETENER") return;
  try {
    await api("/api/ports/owner/stop", {method:"POST", body: JSON.stringify({confirm:"DETENER", pid})});
    refreshPorts();
    refreshProcesses();
  } catch(e){ alert(e.message); }
}

function escapeHtml(v){
  return String(v ?? "").replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
}
function escapeJs(v){
  return String(v ?? "").replace(/\\/g,"\\\\").replace(/'/g,"\\'");
}

$("refreshNow").addEventListener("click", refreshAll);
$("search").addEventListener("input", renderProcesses);
$("riskFilter").addEventListener("change", renderProcesses);
$("closeModal").addEventListener("click", () => $("modal").close());
$("scanCleanup").addEventListener("click", scanCleanup);
$("runCleanup").addEventListener("click", runCleanup);
$("memOptimize").addEventListener("click", memOptimize);
$("diskOptimize").addEventListener("click", diskOptimize);
$("scanDesktop").addEventListener("click", scanDesktop);
$("runDesktop").addEventListener("click", runDesktop);
$("refreshPorts").addEventListener("click", refreshPorts);
$("portSearch").addEventListener("input", renderPorts);
$("findFreePort").addEventListener("click", findFreePort);
$("launchPort").addEventListener("click", launchPort);
$("protectOnly").addEventListener("click", protectOnly);

refreshAll();
setInterval(refreshSystem, 2500);
setInterval(refreshProcesses, 4500);
setInterval(refreshJobs, 3500);
setInterval(refreshPorts, 6000);
