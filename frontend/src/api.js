async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    let body;
    try {
      body = await res.text();
    } catch {
      body = res.statusText;
    }
    throw new Error(body || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get: (path) => request(path),
  post: (path, data) => request(path, { method: 'POST', body: JSON.stringify(data) }),
  patch: (path, data) => request(path, { method: 'PATCH', body: JSON.stringify(data) }),
  raw: (path, init = {}) => fetch(path, init),
};

export const endpoints = {
  summary: '/api/dashboard/summary',
  recentIncidents: '/api/dashboard/recent-incidents',
  channel: '/api/dashboard/channel',
  incidents: (status) => (status ? `/api/incidents?status=${encodeURIComponent(status)}` : '/api/incidents'),
  incident: (id) => `/api/incidents/${id}`,
  equipment: '/api/equipment',
  equipmentItem: (id) => `/api/equipment/${id}`,
  equipmentIncidents: (id) => `/api/equipment/${id}/incidents`,
  equipmentExport: '/api/equipment/export.csv',
  equipmentBulk: '/api/equipment/bulk',
};