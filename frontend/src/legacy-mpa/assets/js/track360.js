import ApexCharts from 'apexcharts';

const SHELL_HTML = `
  <div id="overlay" class="overlay"></div>
  <nav id="topbar" class="navbar bg-white border-bottom fixed-top topbar px-3">
    <div class="d-flex align-items-center">
      <button id="toggleBtn" class="d-none d-lg-inline-flex btn btn-light btn-icon btn-sm">
        <i class="ti ti-layout-sidebar-left-expand"></i>
      </button>
      <button id="mobileBtn" class="btn btn-light btn-icon btn-sm d-lg-none me-2">
        <i class="ti ti-layout-sidebar-left-expand"></i>
      </button>
    </div>
    <div class="d-flex align-items-center gap-3 flex-grow-1 flex-wrap">
      <span class="badge bg-success-subtle text-success border border-success d-inline-flex align-items-center gap-1">
        <i class="ti ti-message-circle"></i> SMS channel live
      </span>
      <span class="badge bg-primary-subtle text-primary border border-primary d-inline-flex align-items-center gap-1">
        <i class="ti ti-bolt"></i> <span id="live-label">Waiting for SMS</span>
      </span>
      <span class="ms-auto text-secondary small fw-medium d-none d-md-inline" id="clock"></span>
    </div>
  </nav>

  <aside id="sidebar" class="sidebar">
    <div class="logo-area">
      <a href="index.html" class="d-inline-flex align-items-center gap-2">
        <img src="./assets/images/logo-icon.svg" alt="Track360" width="24">
        <span class="logo-text fs-6 fw-bold text-dark">Track360</span>
      </a>
    </div>
    <ul class="nav flex-column">
      <li class="px-4 py-2"><small class="nav-text">Main</small></li>
      <li><a class="nav-link" data-nav="dashboard" href="index.html"><i class="ti ti-home"></i><span class="nav-text">Dashboard</span></a></li>
      <li><a class="nav-link" data-nav="inbox" href="reports.html"><i class="ti ti-inbox"></i><span class="nav-text">Incident Inbox</span></a></li>
      <li><a class="nav-link" data-nav="equipment" href="inventory.html"><i class="ti ti-box-seam"></i><span class="nav-text">Equipment</span></a></li>
      <li class="px-4 pt-4 pb-2"><small class="nav-text">System</small></li>
      <li><a class="nav-link" data-nav="notfound" href="404-error.html"><i class="ti ti-alert-circle"></i><span class="nav-text">404 Error</span></a></li>
      <li><a class="nav-link" data-nav="docs" href="docs.html"><i class="ti ti-file-text"></i><span class="nav-text">Docs</span></a></li>
    </ul>
    <div class="rail-foot px-4 pt-4 pb-3 small text-secondary">
      <p class="mb-0">Phone → Africa's Talking → webhook → incident</p>
    </div>
  </aside>
`;

function buildShell() {
  const mount = document.getElementById('app-shell');
  if (mount) {
    mount.innerHTML = SHELL_HTML;
  }
  setInterval(() => {
    const clock = document.getElementById('clock');
    if (clock) clock.textContent = new Date().toLocaleString();
  }, 1000);
}

async function api(path, options) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options && options.headers) },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function fmtTZS(value) {
  if (value == null || value === '') return '—';
  return 'TZS ' + Number(value).toLocaleString('en-TZ');
}

function fmtMinutes(value) {
  if (value == null) return '—';
  const hours = Math.floor(Number(value) / 60);
  const minutes = Number(value) % 60;
  if (hours && minutes) return `${hours}h ${minutes}m`;
  if (hours) return `${hours}h`;
  return `${minutes} min`;
}

function toDate(iso) {
  if (!iso) return null;
  return new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z');
}

function fmtTime(iso) {
  const d = toDate(iso);
  if (!d) return '—';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function fmtDate(iso) {
  const d = toDate(iso);
  if (!d) return '—';
  return d.toLocaleDateString([], { day: '2-digit', month: 'short' });
}

const STATUS_COLOR = {
  NEW: 'bg-danger',
  ACKNOWLEDGED: 'bg-warning text-dark',
  UNDER_REPAIR: 'bg-info text-dark',
  RESOLVED: 'bg-success',
};

const SEVERITY_COLOR = {
  LOW: 'bg-secondary',
  MEDIUM: 'bg-warning text-dark',
  HIGH: 'bg-danger',
  CRITICAL: 'bg-dark',
};

const EQ_STATUS_COLOR = {
  OPERATIONAL: 'bg-success',
  DEGRADED: 'bg-warning text-dark',
  MAINTENANCE: 'bg-info text-dark',
};

function chip(text, color) {
  return `<span class="badge ${color}">${escapeHtml(text).replace(/_/g, ' ')}</span>`;
}

function statusChip(status) {
  return chip(status, STATUS_COLOR[status] || 'bg-secondary');
}

function severityChip(severity) {
  return chip(severity, SEVERITY_COLOR[severity] || 'bg-secondary');
}

function eqChip(status) {
  return chip(status, EQ_STATUS_COLOR[status] || 'bg-secondary');
}

function equipmentLabel(incident) {
  if (incident && incident.equipment) return `${incident.equipment.code} — ${incident.equipment.name}`;
  return 'Unassigned';
}

function isFresh(iso) {
  const d = toDate(iso);
  return d && Date.now() - d.getTime() < 60000;
}

/* ---------------- Dashboard ---------------- */

let trendChart = null;
let statusChart = null;
let lastIncidentSignature = '';
const POLL_MS = 4000;

async function renderDashboard() {
  const [summary, incidents] = await Promise.all([
    api('/api/dashboard/summary'),
    api('/api/dashboard/recent-incidents'),
  ]);

  document.getElementById('kpi-total-equipment').textContent = summary.total_equipment;
  document.getElementById('kpi-new').textContent = summary.new_incidents;
  document.getElementById('kpi-open').textContent = summary.open_incidents;
  document.getElementById('kpi-under-repair').textContent = summary.under_repair;
  document.getElementById('kpi-resolved-today').textContent = summary.resolved_today;
  document.getElementById('kpi-month').textContent = summary.incidents_this_month;
  document.getElementById('kpi-cost').textContent = fmtTZS(summary.maintenance_cost);
  document.getElementById('kpi-downtime').textContent = fmtMinutes(summary.total_downtime_minutes);

  const signature = incidents.map((item) => item.id).join(',');
  const flash = lastIncidentSignature && signature !== lastIncidentSignature;
  lastIncidentSignature = signature;
  const label = document.getElementById('live-label');
  if (label) label.textContent = flash ? 'New SMS received' : 'Waiting for SMS';

  const feed = document.getElementById('feed');
  if (feed) {
    feed.innerHTML = incidents.length
      ? incidents.map(incidentCard).join('')
      : `<div class="empty text-secondary">No incidents yet. Send an SMS to the Africa's Talking number.</div>`;
  }

  const insights = document.getElementById('insights');
  if (insights) {
    insights.innerHTML = summary.insights.length
      ? summary.insights.map((text) => `
          <div class="d-flex gap-2 align-items-start mb-2">
            <i class="ti ti-alert-triangle text-danger mt-1"></i>
            <span>${escapeHtml(text)}</span>
          </div>`).join('')
      : `<div class="text-secondary">No recurring-failure warnings in the last 30 days.</div>`;
  }

  const failing = document.getElementById('failing');
  if (failing) {
    failing.innerHTML = (summary.failing_equipment || []).length
      ? (summary.failing_equipment || []).slice(0, 6).map((row) => `
        <div class="d-flex justify-content-between align-items-center border-bottom py-2">
          <a class="text-decoration-none" href="equipment.html?id=${row.equipment_id}">
            <span class="fw-semibold">${escapeHtml(row.code)}</span>
            <span class="text-secondary ms-2">${escapeHtml(row.name)}</span>
          </a>
          <span class="small text-secondary">${row.incident_count} · ${fmtTZS(row.total_repair_cost)} · ${fmtMinutes(row.total_downtime_minutes)}</span>
        </div>`).join('')
      : `<div class="text-secondary">No failure data yet.</div>`;
  }

  const categories = document.getElementById('categories');
  if (categories) {
    categories.innerHTML = (summary.recurring_categories || []).map((row) => `
        <div class="d-flex justify-content-between border-bottom py-2">
          <span>${escapeHtml(row.category)}</span>
          <span class="badge bg-primary-subtle text-primary">${row.count}</span>
        </div>`).join('')
      || `<div class="text-secondary">No data yet.</div>`;
  }

  renderTrend(incidents);
  renderStatusDonut(summary);
}

function incidentCard(item) {
  return `
    <div class="border rounded-2 p-3 mb-2 ${isFresh(item.reported_at) ? 'border-primary' : 'border-light'}" style="${isFresh(item.reported_at) ? 'border-width:1.5px' : ''}">
      <div class="d-flex justify-content-between align-items-start gap-2">
        <div>
          <span class="fw-semibold">${escapeHtml(equipmentLabel(item))}</span>
          <div class="mb-1">${statusChip(item.status)} ${severityChip(item.severity)}</div>
        </div>
        <span class="small text-secondary">${fmtTime(item.reported_at)}</span>
      </div>
      <p class="mb-1">“${escapeHtml(item.original_message)}”</p>
      <div class="small text-secondary d-flex gap-3 flex-wrap">
        <span><i class="ti ti-phone"></i> ${escapeHtml(item.sender_phone)}</span>
        <span><i class="ti ti-message"></i> ${escapeHtml(item.channel)}</span>
      </div>
      <a class="small text-primary text-decoration-none" href="create-product.html?id=${item.id}">Open incident <i class="ti ti-arrow-right"></i></a>
    </div>
  `;
}

function renderTrend(incidents) {
  const el = document.getElementById('incidentTrend');
  if (!el) return;
  const days = 14;
  const buckets = [];
  const labels = [];
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(start.getTime() - i * 86400000);
    labels.push(d.toLocaleDateString([], { day: '2-digit', month: 'short' }));
    buckets.push(0);
  }
  for (const item of incidents) {
    const d = toDate(item.reported_at);
    if (!d) continue;
    const idx = Math.floor((d.getTime() - start.getTime()) / 86400000);
    if (idx >= 0 && idx < days) buckets[days - 1 - Math.floor((start.getTime() - d.getTime()) / 86400000)] += 1;
  }
  if (!trendChart) {
    trendChart = new ApexCharts(el, {
      chart: { type: 'bar', height: 320, toolbar: { show: false } },
      colors: ['#E66239'],
      series: [{ name: 'Incidents', data: buckets }],
      plotOptions: { bar: { columnWidth: '55%', borderRadius: 3 } },
      dataLabels: { enabled: false },
      grid: { borderColor: '#e2e8f0' },
      xaxis: { categories: labels, axisBorder: { show: false } },
      yaxis: { labels: { formatter: (v) => Math.round(v) } },
    });
    trendChart.render();
  } else {
    trendChart.updateOptions({ xaxis: { categories: labels } });
    trendChart.updateSeries([{ name: 'Incidents', data: buckets }]);
  }
}

function renderStatusDonut(summary) {
  const el = document.getElementById('statusDonut');
  if (!el) return;
  const series = [
    summary.new_incidents,
    summary.open_incidents - summary.under_repair - summary.new_incidents < 0 ? 0 : summary.open_incidents - summary.under_repair - summary.new_incidents,
    summary.under_repair,
  ];
  const labels = ['NEW', 'ACKNOWLEDGED', 'UNDER_REPAIR'];
  if (!statusChart) {
    statusChart = new ApexCharts(el, {
      chart: { type: 'donut', height: 320 },
      series,
      labels,
      colors: ['#FB2C36', '#F0B100', '#00B8DB'],
      stroke: { width: 0 },
      dataLabels: { enabled: false },
      legend: { position: 'bottom' },
      plotOptions: { pie: { donut: { labels: { show: true, total: { show: true, label: 'Open' } } } } },
    });
    statusChart.render();
  } else {
    statusChart.updateOptions({ labels });
    statusChart.updateSeries(series);
  }
}

function startDashboardPolling() {
  renderDashboard();
  setInterval(renderDashboard, POLL_MS);
}

/* ---------------- Equipment list ---------------- */

async function renderEquipmentList() {
  const [rows] = await Promise.all([api('/api/equipment')]);
  const tbody = document.getElementById('equipment-body');
  const count = document.getElementById('equipment-count');
  if (count) count.textContent = `${rows.length} assets`;
  if (tbody) {
    tbody.innerHTML = rows.length
      ? rows.map((item) => `
          <tr class="align-middle">
            <td><a class="fw-semibold" href="equipment.html?id=${item.id}">${escapeHtml(item.code)}</a></td>
            <td>${escapeHtml(item.name)}</td>
            <td>${escapeHtml(item.equipment_type)}</td>
            <td>${escapeHtml(item.location)}</td>
            <td>${eqChip(item.status)}</td>
            <td>${item.incident_count}</td>
            <td>${item.open_count}</td>
            <td>${fmtTZS(item.total_repair_cost)}</td>
            <td>${fmtMinutes(item.total_downtime_minutes)}</td>
          </tr>`).join('')
      : `<tr><td colspan="9" class="text-center text-secondary py-4">No equipment registered.</td></tr>`;
  }
  const search = document.getElementById('equipment-search');
  if (search) {
    search.addEventListener('input', () => {
      const q = (search.value || '').toLowerCase();
      tbody.querySelectorAll('tr').forEach((row) => {
        row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  }
}

/* ---------------- Incident inbox ---------------- */

async function renderInbox(status) {
  const path = status ? `/api/incidents?status=${encodeURIComponent(status)}` : '/api/incidents';
  const incidents = await api(path);
  const tbody = document.getElementById('inbox-body');
  const count = document.getElementById('inbox-count');
  if (count) count.textContent = `${incidents.length} incidents`;
  if (tbody) {
    tbody.innerHTML = incidents.length
      ? incidents.map((item) => `
          <tr class="align-middle">
            <td class="text-secondary">${fmtDate(item.reported_at)} ${fmtTime(item.reported_at)}</td>
            <td><a class="fw-semibold text-decoration-none" href="equipment.html?id=${item.equipment_id}">${escapeHtml(equipmentLabel(item))}</a></td>
            <td class="text-secondary">“${escapeHtml(item.original_message)}”</td>
            <td>${severityChip(item.severity)}</td>
            <td>${statusChip(item.status)}</td>
            <td>
              <a class="btn btn-sm btn-outline-primary" href="create-product.html?id=${item.id}">
                <i class="ti ti-eye"></i> View
              </a>
            </td>
          </tr>`).join('')
      : `<tr><td colspan="6" class="text-center text-secondary py-4">No incidents in this view.</td></tr>`;
  }
}

function bindInboxFilters() {
  document.querySelectorAll('[data-status]').forEach((button) => {
    button.addEventListener('click', () => {
      const status = button.dataset.status;
      document.querySelectorAll('[data-status]').forEach((b) => b.classList.toggle('active', b === button));
      renderInbox(status || null);
    });
  });
}

/* ---------------- Incident detail / edit ---------------- */

const CATEGORIES = ['STOPPAGE', 'OVERHEATING', 'LEAK', 'MECHANICAL', 'ELECTRICAL', 'QUALITY', 'OTHER'];
const SEVERITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
const STATUSES = ['NEW', 'ACKNOWLEDGED', 'UNDER_REPAIR', 'RESOLVED'];

async function renderIncidentDetail(id) {
  const [incident, equipment] = await Promise.all([api(`/api/incidents/${id}`), api('/api/equipment')]);

  document.getElementById('inc-title').textContent = equipmentLabel(incident);
  document.getElementById('inc-sms').textContent = incident.original_message || '—';
  document.getElementById('inc-sender').textContent = incident.sender_phone || '—';
  document.getElementById('inc-recipient').textContent = incident.recipient_number || '—';
  document.getElementById('inc-channel').textContent = incident.channel || '—';
  document.getElementById('inc-reported').textContent = `${fmtDate(incident.reported_at)} ${fmtTime(incident.reported_at)}`;
  document.getElementById('inc-badges').innerHTML = `${statusChip(incident.status)} ${severityChip(incident.severity)}`;

  const form = document.getElementById('incident-form');
  const eqSelect = form.elements.equipment_id;
  eqSelect.innerHTML = `<option value="">Unassigned</option>` +
    equipment.map((item) => `<option value="${item.id}" ${incident.equipment_id === item.id ? 'selected' : ''}>${escapeHtml(item.code)} — ${escapeHtml(item.name)}</option>`).join('');

  const category = form.elements.category;
  category.innerHTML = `<option value="">Unclassified</option>` +
    CATEGORIES.map((c) => `<option ${incident.category === c ? 'selected' : ''}>${c}</option>`).join('');

  const severity = form.elements.severity;
  severity.innerHTML = SEVERITIES.map((s) => `<option ${incident.severity === s ? 'selected' : ''}>${s}</option>`).join('');

  const status = form.elements.status;
  status.innerHTML = STATUSES.map((s) => `<option ${incident.status === s ? 'selected' : ''}>${s}</option>`).join('');

  form.elements.repair_notes.value = incident.repair_notes || '';
  form.elements.repair_cost.value = incident.repair_cost ?? '';
  form.elements.downtime_minutes.value = incident.downtime_minutes ?? '';

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = {
      equipment_id: form.elements.equipment_id.value ? Number(form.elements.equipment_id.value) : null,
      category: form.elements.category.value || null,
      severity: form.elements.severity.value,
      status: form.elements.status.value,
      repair_notes: form.elements.repair_notes.value || null,
      repair_cost: form.elements.repair_cost.value === '' ? null : Number(form.elements.repair_cost.value),
      downtime_minutes: form.elements.downtime_minutes.value === '' ? null : Number(form.elements.downtime_minutes.value),
    };
    try {
      await api(`/api/incidents/${id}`, { method: 'PATCH', body: JSON.stringify(payload) });
      const msg = document.getElementById('save-msg');
      if (msg) msg.innerHTML = `<span class="text-success">Saved.</span>`;
      renderIncidentDetail(id);
    } catch (err) {
      const msg = document.getElementById('save-msg');
      if (msg) msg.innerHTML = `<span class="text-danger">Save failed: ${escapeHtml(err.message)}</span>`;
    }
  });
}

/* ---------------- Equipment detail / history ---------------- */

async function renderEquipmentDetail(id) {
  const [item, incidents] = await Promise.all([
    api(`/api/equipment/${id}`),
    api(`/api/equipment/${id}/incidents`),
  ]);

  document.getElementById('eq-header').innerHTML = `
    ${escapeHtml(item.code)} — ${escapeHtml(item.name)} ${eqChip(item.status)}
    <div class="small text-secondary fw-normal mt-1">${escapeHtml(item.equipment_type)} · ${escapeHtml(item.location)}</div>`;

  document.getElementById('eq-incidents').textContent = item.incident_count;
  document.getElementById('eq-open').textContent = item.open_count;
  document.getElementById('eq-cost').textContent = fmtTZS(item.total_repair_cost);
  document.getElementById('eq-downtime').textContent = fmtMinutes(item.total_downtime_minutes);

  const tbody = document.getElementById('eq-history');
  if (tbody) {
    tbody.innerHTML = incidents.length
      ? incidents.map((row) => `
          <tr class="align-middle">
            <td><a class="text-decoration-none" href="create-product.html?id=${row.id}">${fmtDate(row.reported_at)}</a></td>
            <td>“${escapeHtml(row.original_message)}”</td>
            <td>${escapeHtml(row.channel)}</td>
            <td>${statusChip(row.status)}</td>
            <td>${fmtTZS(row.repair_cost)}</td>
          </tr>`).join('')
      : `<tr><td colspan="5" class="text-center text-secondary py-4">No incidents recorded for this asset.</td></tr>`;
  }
}

/* ---------------- Page dispatch ---------------- */

const PAGES = {
  dashboard: () => startDashboardPolling(),
  equipment: () => renderEquipmentList(),
  inbox: () => {
    bindInboxFilters();
    renderInbox(null);
    setInterval(() => {
      const active = document.querySelector('[data-status].active');
      renderInbox(active && active.dataset.status ? active.dataset.status : null);
    }, POLL_MS);
  },
  incident: () => {
    const id = Number(new URLSearchParams(location.search).get('id'));
    if (id) renderIncidentDetail(id);
  },
  equipmentDetail: () => {
    const id = Number(new URLSearchParams(location.search).get('id'));
    if (id) renderEquipmentDetail(id);
  },
};

buildShell();

document.addEventListener('DOMContentLoaded', () => {
  const page = document.body.dataset.page;
  const renderPage = PAGES[page];
  if (renderPage) {
    renderPage().catch((err) => console.error(err));
  }
});