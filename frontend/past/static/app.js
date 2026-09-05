const POLL_MS = 4000;
const CATEGORIES = ["STOPPAGE", "OVERHEATING", "LEAK", "MECHANICAL", "ELECTRICAL", "QUALITY", "OTHER"];
const SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
const STATUSES = ["NEW", "ACKNOWLEDGED", "UNDER_REPAIR", "RESOLVED"];

let pollTimer = null;
let lastIncidentSignature = "";

const app = document.getElementById("app");
const pageTitle = document.getElementById("page-title");
const pageSub = document.getElementById("page-sub");
const clock = document.getElementById("clock");

setInterval(() => {
  clock.textContent = new Date().toLocaleString();
}, 1000);

window.addEventListener("hashchange", render);
render();

function route() {
  const hash = (location.hash || "#/dashboard").replace(/^#/, "");
  const parts = hash.split("/").filter(Boolean);
  return { name: parts[0] || "dashboard", id: parts[1] ? Number(parts[1]) : null };
}

async function render() {
  clearInterval(pollTimer);
  const r = route();
  document.querySelectorAll("nav a").forEach((link) => {
    const key = link.dataset.route;
    link.classList.toggle("active", r.name === key || (key === "incidents" && r.name === "incident"));
  });
  if (r.name === "incident" && r.id) return showIncident(r.id);
  if (r.name === "equipment" && r.id) return showEquipment(r.id);
  if (r.name === "incidents") return showInbox();
  if (r.name === "equipment") return showEquipmentList();
  return showDashboard();
}

async function api(path, options) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options && options.headers) },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}

function fmtTZS(value) {
  if (value == null || value === "") return "—";
  return "TZS " + Number(value).toLocaleString("en-TZ");
}

function fmtMinutes(value) {
  if (value == null) return "—";
  const hours = Math.floor(Number(value) / 60);
  const minutes = Number(value) % 60;
  if (hours && minutes) return `${hours}h ${minutes}m`;
  if (hours) return `${hours}h`;
  return `${minutes} min`;
}

function fmtTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z");
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z");
  return d.toLocaleDateString([], { day: "2-digit", month: "short" });
}

function equipmentLabel(incident) {
  if (incident.equipment) return `${incident.equipment.code} — ${incident.equipment.name}`;
  return "Unassigned";
}

function isFresh(iso) {
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z");
  return Date.now() - d.getTime() < 60000;
}

function setHeader(title, sub) {
  pageTitle.textContent = title;
  pageSub.textContent = sub;
}

async function showDashboard() {
  setHeader("Dashboard", "Incoming SMS reports become plant incidents.");
  await refreshDashboard();
  pollTimer = setInterval(refreshDashboard, POLL_MS);
}

async function refreshDashboard() {
  const [summary, incidents] = await Promise.all([
    api("/api/dashboard/summary"),
    api("/api/dashboard/recent-incidents"),
  ]);
  const signature = incidents.map((item) => item.id).join(",");
  const flash = lastIncidentSignature && signature !== lastIncidentSignature;
  lastIncidentSignature = signature;
  document.getElementById("live-label").textContent = flash ? "New SMS received" : "Listening for SMS";

  app.innerHTML = `
    <div class="kpis">
      ${kpi("Total Equipment", summary.total_equipment)}
      ${kpi("New Incidents", summary.new_incidents, summary.new_incidents > 0)}
      ${kpi("Open Incidents", summary.open_incidents)}
      ${kpi("Under Repair", summary.under_repair)}
      ${kpi("Resolved Today", summary.resolved_today)}
      ${kpi("Incidents This Month", summary.incidents_this_month)}
      ${kpi("Maintenance Cost", fmtTZS(summary.maintenance_cost))}
      ${kpi("Total Downtime", fmtMinutes(summary.total_downtime_minutes))}
    </div>
    <div class="layout">
      <div class="panel">
        <h2>Incoming Incident Feed</h2>
        <div class="feed">
          ${incidents.length ? incidents.map((item) => incidentCard(item)).join("") : `<div class="empty">No incidents yet. Send an SMS to the Africa's Talking number.</div>`}
        </div>
      </div>
      <div>
        <div class="panel" style="margin-bottom:16px">
          <h2>Maintenance Intelligence</h2>
          ${
            summary.insights.length
              ? summary.insights.map((text) => `<div class="insight">${escapeHtml(text)}</div>`).join("")
              : `<div class="empty">No recurring-failure warnings in the last 30 days.</div>`
          }
        </div>
        <div class="panel" style="margin-bottom:16px">
          <h2>Most Frequent Failures</h2>
          ${summary.failing_equipment.slice(0, 6).map((row) => `
            <div class="stat-row">
              <a href="#/equipment/${row.equipment_id}"><span class="code">${escapeHtml(row.code)}</span> ${escapeHtml(row.name)}</a>
              <div class="muted">${row.incident_count} incidents · ${fmtTZS(row.total_repair_cost)} · ${fmtMinutes(row.total_downtime_minutes)}</div>
            </div>
          `).join("")}
        </div>
        <div class="panel">
          <h2>Recurring Categories</h2>
          ${summary.recurring_categories.map((row) => `
            <div class="stat-row">${escapeHtml(row.category)} <span class="muted">${row.count}</span></div>
          `).join("")}
        </div>
      </div>
    </div>
  `;
}

function kpi(label, value, alert) {
  return `<div class="kpi ${alert ? "alert" : ""}"><span>${label}</span><strong>${value}</strong></div>`;
}

function incidentCard(item) {
  return `
    <a class="incident-card ${isFresh(item.reported_at) ? "fresh" : ""}" href="#/incident/${item.id}">
      <div><span class="badge ${item.status}">${item.status.replace("_", " ")}</span></div>
      <div>
        <div class="code">${escapeHtml(equipmentLabel(item))}</div>
        <p class="quote">“${escapeHtml(item.original_message)}”</p>
        <div class="meta">
          <span>From ${escapeHtml(item.sender_phone)}</span>
          <span>Channel ${escapeHtml(item.channel)}</span>
        </div>
      </div>
      <div class="muted">${fmtTime(item.reported_at)}</div>
    </a>
  `;
}

async function showInbox() {
  setHeader("Incident Inbox", "Every SMS report, newest first.");
  const current = new URLSearchParams(location.hash.split("?")[1] || "");
  const selected = current.get("status") || "";
  await refreshInbox(selected);
  pollTimer = setInterval(() => refreshInbox(selected), POLL_MS);
}

async function refreshInbox(selected) {
  const path = selected ? `/api/incidents?status=${encodeURIComponent(selected)}` : "/api/incidents";
  const incidents = await api(path);
  app.innerHTML = `
    <div class="filters">
      ${["", ...STATUSES].map((status) => `
        <button class="${selected === status ? "active" : ""}" data-status="${status}">${status || "ALL"}</button>
      `).join("")}
    </div>
    <div class="panel feed">
      ${incidents.length ? incidents.map(incidentCard).join("") : `<div class="empty">No incidents in this view.</div>`}
    </div>
  `;
  app.querySelectorAll(".filters button").forEach((button) => {
    button.addEventListener("click", () => {
      const status = button.dataset.status;
      showInboxWith(status);
    });
  });
}

async function showInboxWith(status) {
  clearInterval(pollTimer);
  setHeader("Incident Inbox", "Every SMS report, newest first.");
  await refreshInbox(status);
  pollTimer = setInterval(() => refreshInbox(status), POLL_MS);
}

async function showIncident(id) {
  setHeader("Incident Detail", "Classify, repair, and close the SMS report.");
  const [incident, equipment] = await Promise.all([api(`/api/incidents/${id}`), api("/api/equipment")]);
  app.innerHTML = `
    <div class="detail">
      <div class="panel">
        <h2>Original SMS</h2>
        <div style="padding:16px">
          <div class="sms-block">${escapeHtml(incident.original_message)}</div>
          <div class="meta" style="margin-top:12px">
            <span>From ${escapeHtml(incident.sender_phone)}</span>
            <span>To ${escapeHtml(incident.recipient_number || "—")}</span>
            <span>Channel ${escapeHtml(incident.channel)}</span>
            <span>Reported ${fmtDate(incident.reported_at)} ${fmtTime(incident.reported_at)}</span>
          </div>
        </div>
      </div>
      <div class="panel">
        <h2>Manage Incident</h2>
        <form class="form" id="incident-form">
          <label>Equipment
            <select name="equipment_id">
              <option value="">Unassigned</option>
              ${equipment.map((item) => `
                <option value="${item.id}" ${incident.equipment_id === item.id ? "selected" : ""}>${item.code} — ${item.name}</option>
              `).join("")}
            </select>
          </label>
          <label>Category
            <select name="category">
              <option value="">Unclassified</option>
              ${CATEGORIES.map((item) => `<option ${incident.category === item ? "selected" : ""}>${item}</option>`).join("")}
            </select>
          </label>
          <label>Severity
            <select name="severity">
              ${SEVERITIES.map((item) => `<option ${incident.severity === item ? "selected" : ""}>${item}</option>`).join("")}
            </select>
          </label>
          <label>Status
            <select name="status">
              ${STATUSES.map((item) => `<option ${incident.status === item ? "selected" : ""}>${item}</option>`).join("")}
            </select>
          </label>
          <label>Repair notes
            <textarea name="repair_notes">${escapeHtml(incident.repair_notes || "")}</textarea>
          </label>
          <label>Repair cost (TZS)
            <input name="repair_cost" type="number" min="0" step="1" value="${incident.repair_cost ?? ""}" />
          </label>
          <label>Downtime (minutes)
            <input name="downtime_minutes" type="number" min="0" step="1" value="${incident.downtime_minutes ?? ""}" />
          </label>
          <button class="btn btn-primary" type="submit">Save changes</button>
          <div class="muted" id="save-msg"></div>
        </form>
      </div>
    </div>
  `;
  document.getElementById("incident-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    const payload = {
      equipment_id: form.get("equipment_id") ? Number(form.get("equipment_id")) : null,
      category: form.get("category") || null,
      severity: form.get("severity"),
      status: form.get("status"),
      repair_notes: form.get("repair_notes") || null,
      repair_cost: form.get("repair_cost") === "" ? null : Number(form.get("repair_cost")),
      downtime_minutes: form.get("downtime_minutes") === "" ? null : Number(form.get("downtime_minutes")),
    };
    await api(`/api/incidents/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
    document.getElementById("save-msg").textContent = "Saved.";
    showIncident(id);
  });
}

async function showEquipmentList() {
  setHeader("Equipment", "Plant assets and their SMS incident history.");
  const rows = await api("/api/equipment");
  app.innerHTML = `
    <div class="panel">
      <table class="table">
        <thead>
          <tr><th>Code</th><th>Name</th><th>Location</th><th>Incidents</th><th>Open</th><th>Repair cost</th><th>Downtime</th></tr>
        </thead>
        <tbody>
            ${rows.map((item) => `
            <tr>
              <td><a class="code" href="#/equipment/${item.id}">${escapeHtml(item.code)}</a></td>
              <td>${escapeHtml(item.name)}</td>
              <td>${escapeHtml(item.location)}</td>
              <td>${item.incident_count}</td>
              <td>${item.open_count}</td>
              <td>${fmtTZS(item.total_repair_cost)}</td>
              <td>${fmtMinutes(item.total_downtime_minutes)}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

async function showEquipment(id) {
  const [item, incidents] = await Promise.all([
    api(`/api/equipment/${id}`),
    api(`/api/equipment/${id}/incidents`),
  ]);
  setHeader(`${item.code} — ${item.name}`, `${item.equipment_type} · ${item.location}`);
  app.innerHTML = `
    <div class="panel" style="margin-bottom:16px">
      <div class="eq-hero">
        <div><span>Incidents</span><strong>${item.incident_count}</strong></div>
        <div><span>Open</span><strong>${item.open_count}</strong></div>
        <div><span>Total repair cost</span><strong>${fmtTZS(item.total_repair_cost)}</strong></div>
        <div><span>Total downtime</span><strong>${fmtMinutes(item.total_downtime_minutes)}</strong></div>
      </div>
    </div>
    <div class="panel">
      <h2>History</h2>
      ${incidents.length ? `
        <table class="table">
          <thead><tr><th>Date</th><th>Message</th><th>Channel</th><th>Status</th><th>Cost</th></tr></thead>
          <tbody>
            ${incidents.map((row) => `
              <tr>
                <td><a href="#/incident/${row.id}">${fmtDate(row.reported_at)}</a></td>
                <td>${escapeHtml(row.original_message)}</td>
                <td>${escapeHtml(row.channel)}</td>
                <td><span class="badge ${row.status}">${row.status.replace("_", " ")}</span></td>
                <td>${fmtTZS(row.repair_cost)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      ` : `<div class="empty">No incidents recorded for this asset.</div>`}
    </div>
  `;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}
