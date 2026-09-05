import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, endpoints } from '../api';
import { fmtDate, fmtTime, equipmentLabel } from '../format';
import { StatusChip, SeverityChip, Loading, ErrorNote } from '../components/ui';

const CATEGORIES = ['STOPPAGE', 'OVERHEATING', 'LEAK', 'MECHANICAL', 'ELECTRICAL', 'QUALITY', 'OTHER'];
const SEVERITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
const STATUSES = ['NEW', 'ACKNOWLEDGED', 'UNDER_REPAIR', 'RESOLVED'];

export default function IncidentDetailPage() {
  const { id } = useParams();
  const [incident, setIncident] = useState(null);
  const [equipment, setEquipment] = useState([]);
  const [error, setError] = useState(null);
  const [saveMsg, setSaveMsg] = useState(null);
  const [form, setForm] = useState({
    equipment_id: '',
    category: '',
    severity: 'MEDIUM',
    status: 'NEW',
    repair_notes: '',
    repair_cost: '',
    downtime_minutes: '',
  });

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.get(endpoints.incident(id)), api.get(endpoints.equipment)])
      .then(([inc, eq]) => {
        if (cancelled) return;
        setIncident(inc);
        setEquipment(eq);
        setForm({
          equipment_id: inc.equipment_id ?? '',
          category: inc.category ?? '',
          severity: inc.severity,
          status: inc.status,
          repair_notes: inc.repair_notes || '',
          repair_cost: inc.repair_cost ?? '',
          downtime_minutes: inc.downtime_minutes ?? '',
        });
        setError(null);
      })
      .catch((err) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) return <ErrorNote>Backend unreachable at /api — is FastAPI running on :8000? ({error})</ErrorNote>;
  if (!incident) return <Loading />;

  function set(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    setSaveMsg(null);
    const payload = {
      equipment_id: form.equipment_id === '' ? null : Number(form.equipment_id),
      category: form.category === '' ? null : form.category,
      severity: form.severity,
      status: form.status,
      repair_notes: form.repair_notes || null,
      repair_cost: form.repair_cost === '' ? null : Number(form.repair_cost),
      downtime_minutes: form.downtime_minutes === '' ? null : Number(form.downtime_minutes),
    };
    try {
      const updated = await api.patch(endpoints.incident(id), payload);
      setSaveMsg({ ok: true, text: 'Saved.' });
      setIncident(updated);
    } catch (err) {
      setSaveMsg({ ok: false, text: `Save failed: ${err.message}` });
    }
  }

  return (
    <div>
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 gap-3">
        <div>
          <h1 className="fs-3 mb-1">{equipmentLabel(incident)}</h1>
          <p className="mb-0">Classify, repair, and close the SMS report</p>
        </div>
        <div>
          <Link to="/incidents" className="btn btn-outline-secondary"><i className="ti ti-arrow-left"></i> Back to inbox</Link>
        </div>
      </div>

      <div className="mb-3">
        <StatusChip status={incident.status} /> <SeverityChip severity={incident.severity} />
      </div>

      <div className="row g-3">
        <div className="col-lg-5">
          <div className="card h-100">
            <div className="card-header bg-white px-4 py-3"><h4 className="mb-0 h5">Original SMS</h4></div>
            <div className="card-body p-4">
              <div className="border rounded-2 bg-light p-3 mb-3">“{incident.original_message}”</div>
              <div className="small text-secondary d-flex flex-column gap-2">
                <span><i className="ti ti-phone me-1"></i> From <strong>{incident.sender_phone}</strong></span>
                <span><i className="ti ti-arrow-narrow-right me-1"></i> To <strong>{incident.recipient_number || '—'}</strong></span>
                <span><i className="ti ti-message me-1"></i> Channel <strong>{incident.channel}</strong></span>
                <span><i className="ti ti-clock me-1"></i> Reported <strong>{fmtDate(incident.reported_at)} {fmtTime(incident.reported_at)}</strong></span>
              </div>
            </div>
          </div>
        </div>
        <div className="col-lg-7">
          <div className="card">
            <div className="card-header bg-white px-4 py-3"><h4 className="mb-0 h5">Manage Incident</h4></div>
            <div className="card-body p-4">
              <form onSubmit={onSubmit}>
                <div className="row">
                  <div className="col-md-6 mb-3">
                    <label className="form-label">Equipment</label>
                    <select className="form-select" value={form.equipment_id} onChange={(e) => set('equipment_id', e.target.value)}>
                      <option value="">Unassigned</option>
                      {equipment.map((item) => (
                        <option key={item.id} value={item.id}>{item.code} — {item.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="col-md-6 mb-3">
                    <label className="form-label">Category</label>
                    <select className="form-select" value={form.category} onChange={(e) => set('category', e.target.value)}>
                      <option value="">Unclassified</option>
                      {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
                    </select>
                  </div>
                </div>
                <div className="row">
                  <div className="col-md-6 mb-3">
                    <label className="form-label">Severity</label>
                    <select className="form-select" value={form.severity} onChange={(e) => set('severity', e.target.value)}>
                      {SEVERITIES.map((s) => <option key={s}>{s}</option>)}
                    </select>
                  </div>
                  <div className="col-md-6 mb-3">
                    <label className="form-label">Status</label>
                    <select className="form-select" value={form.status} onChange={(e) => set('status', e.target.value)}>
                      {STATUSES.map((s) => <option key={s}>{s}</option>)}
                    </select>
                  </div>
                </div>
                <div className="mb-3">
                  <label className="form-label">Repair notes</label>
                  <textarea className="form-control" rows="3" placeholder="What was repaired?"
                    value={form.repair_notes} onChange={(e) => set('repair_notes', e.target.value)}></textarea>
                </div>
                <div className="row">
                  <div className="col-md-6 mb-3">
                    <label className="form-label">Repair cost (TZS)</label>
                    <input type="number" className="form-control" min="0" step="1" placeholder="0"
                      value={form.repair_cost} onChange={(e) => set('repair_cost', e.target.value)} />
                  </div>
                  <div className="col-md-6 mb-3">
                    <label className="form-label">Downtime (minutes)</label>
                    <input type="number" className="form-control" min="0" step="1" placeholder="0"
                      value={form.downtime_minutes} onChange={(e) => set('downtime_minutes', e.target.value)} />
                  </div>
                </div>
                <div className="d-flex gap-2 align-items-center">
                  <button type="submit" className="btn btn-primary"><i className="ti ti-device-floppy"></i> Save changes</button>
                  {saveMsg && (
                    <span className={`small ${saveMsg.ok ? 'text-success' : 'text-danger'}`}>{saveMsg.text}</span>
                  )}
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}