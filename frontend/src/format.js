export function fmtTZS(value) {
  if (value == null || value === '') return '—';
  return 'TZS ' + Number(value).toLocaleString('en-TZ');
}

export function fmtMinutes(value) {
  if (value == null) return '—';
  const hours = Math.floor(Number(value) / 60);
  const minutes = Number(value) % 60;
  if (hours && minutes) return `${hours}h ${minutes}m`;
  if (hours) return `${hours}h`;
  return `${minutes} min`;
}

export function toDate(iso) {
  if (!iso) return null;
  return new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z');
}

export function fmtTime(iso) {
  const d = toDate(iso);
  if (!d) return '—';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function fmtDate(iso) {
  const d = toDate(iso);
  if (!d) return '—';
  return d.toLocaleDateString([], { day: '2-digit', month: 'short' });
}

export function isFresh(iso) {
  const d = toDate(iso);
  return d && Date.now() - d.getTime() < 60000;
}

export function equipmentLabel(incident) {
  if (incident && incident.equipment) return `${incident.equipment.code} — ${incident.equipment.name}`;
  return 'Unassigned';
}