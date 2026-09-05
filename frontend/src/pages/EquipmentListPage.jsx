import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, endpoints } from '../api';
import { fmtTZS, fmtMinutes } from '../format';
import { EqChip, Loading, ErrorNote } from '../components/ui';

const STATUSES = ['OPERATIONAL', 'DEGRADED', 'MAINTENANCE'];
const EMPTY_FORM = { code: '', name: '', equipment_type: '', location: '', status: 'OPERATIONAL' };

function overlayStyle() {
  return {
    position: 'fixed',
    inset: 0,
    background: 'rgba(15,23,42,0.55)',
    zIndex: 1055,
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'center',
    overflowY: 'auto',
  };
}

function panelStyle() {
  return {
    marginTop: '8vh',
    width: '100%',
    maxWidth: 520,
    background: '#fff',
    borderRadius: 12,
    boxShadow: '0 20px 40px rgba(15,23,42,0.3)',
  };
}

export default function EquipmentListPage() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saveError, setSaveError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef(null);

  async function load() {
    try {
      const data = await api.get(endpoints.equipment);
      setRows(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const q = query.toLowerCase();
  const filtered = rows.filter((r) =>
    [r.code, r.name, r.equipment_type, r.location].some((v) => (v || '').toLowerCase().includes(q))
  );

  async function handleAdd(e) {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);
    try {
      await api.post(endpoints.equipment, form);
      await load();
      setShowAdd(false);
      setForm(EMPTY_FORM);
    } catch (err) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleExport() {
    const res = await api.raw(endpoints.equipmentExport);
    if (!res.ok) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'equipment.csv';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  async function handleUploadFile(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    setUploading(true);
    setUploadResult(null);
    setUploadError(null);
    try {
      const body = await file.text();
      const res = await fetch(endpoints.equipmentBulk, {
        method: 'POST',
        headers: { 'Content-Type': 'text/csv' },
        body,
      });
      if (!res.ok) {
        let detail;
        try {
          detail = (await res.json()).detail;
        } catch {
          detail = res.statusText;
        }
        throw new Error(detail || res.statusText);
      }
      const result = await res.json();
      setUploadResult(result);
      await load();
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  }

  const input = (k) => ({
    value: form[k],
    onChange: (e) => setForm((f) => ({ ...f, [k]: e.target.value })),
  });

  return (
    <div>
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 gap-3">
        <div>
          <h1 className="fs-3 mb-1">Equipment</h1>
          <p className="mb-0">Plant assets and their SMS incident history</p>
        </div>
        <div className="d-flex gap-2 flex-wrap">
          <button className="btn btn-primary btn-sm" onClick={() => setShowAdd(true)}>
            <i className="ti ti-plus me-1"></i> Add equipment
          </button>
          <button className="btn btn-outline-secondary btn-sm" onClick={() => setShowUpload(true)}>
            <i className="ti ti-upload me-1"></i> Upload CSV
          </button>
          <button className="btn btn-outline-secondary btn-sm" onClick={handleExport}>
            <i className="ti ti-download me-1"></i> Export
          </button>
        </div>
      </div>

      {error && <ErrorNote>Backend unreachable at /api — is FastAPI running on :8000? ({error})</ErrorNote>}

      <div className="row row-cols-1 row-cols-sm-3 g-2 mb-3">
        <div className="col">
          <div className="card h-100 p-3">
            <span className="text-secondary small">Total assets</span>
            <h3 className="mb-0 fw-bold">{rows.length}</h3>
          </div>
        </div>
        <div className="col">
          <div className="card h-100 p-3">
            <span className="text-secondary small">Operational</span>
            <h3 className="mb-0 fw-bold">{rows.filter((r) => r.status === 'OPERATIONAL').length}</h3>
          </div>
        </div>
        <div className="col">
          <div className="card h-100 p-3">
            <span className="text-secondary small">In maintenance</span>
            <h3 className="mb-0 fw-bold">{rows.filter((r) => r.status !== 'OPERATIONAL').length}</h3>
          </div>
        </div>
      </div>

      <div className="d-flex gap-2 mb-3 flex-wrap justify-content-between">
        <input
          type="text"
          className="form-control"
          placeholder="Search by code, name, type or location…"
          style={{ maxWidth: 320 }}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      {loading ? (
        <Loading />
      ) : (
        <div className="card table-responsive">
          <table className="table mb-0 text-nowrap table-hover">
            <thead className="table-light border-light">
              <tr>
                <th>Code</th>
                <th>Name</th>
                <th>Type</th>
                <th>Location</th>
                <th>Status</th>
                <th>Incidents</th>
                <th>Open</th>
                <th>Repair cost</th>
                <th>Downtime</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length
                ? filtered.map((item) => (
                    <tr key={item.id} className="align-middle">
                      <td><Link className="fw-semibold" to={`/equipment/${item.id}`}>{item.code}</Link></td>
                      <td>{item.name}</td>
                      <td>{item.equipment_type}</td>
                      <td>{item.location}</td>
                      <td><EqChip status={item.status} /></td>
                      <td>{item.incident_count}</td>
                      <td>{item.open_count}</td>
                      <td>{fmtTZS(item.total_repair_cost)}</td>
                      <td>{fmtMinutes(item.total_downtime_minutes)}</td>
                    </tr>
                  ))
                : <tr><td colSpan="9" className="text-center text-secondary py-4">No equipment yet. Add one or upload a CSV.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {showAdd && (
        <div style={overlayStyle()} onClick={(e) => e.target === e.currentTarget && setShowAdd(false)}>
          <div style={panelStyle()} className="p-4">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <h4 className="mb-0 h5">Add equipment</h4>
              <button className="btn-close" onClick={() => setShowAdd(false)}></button>
            </div>
            <form onSubmit={handleAdd}>
              <div className="row g-3">
                <div className="col-12">
                  <label className="form-label">Code</label>
                  <input className="form-control" placeholder="e.g. M05" required {...input('code')} />
                </div>
                <div className="col-12">
                  <label className="form-label">Name</label>
                  <input className="form-control" placeholder="e.g. Lathe Machine" required {...input('name')} />
                </div>
                <div className="col-md-6">
                  <label className="form-label">Type</label>
                  <input className="form-control" placeholder="e.g. Lathe" required {...input('equipment_type')} />
                </div>
                <div className="col-md-6">
                  <label className="form-label">Location</label>
                  <input className="form-control" placeholder="e.g. Production Line B" required {...input('location')} />
                </div>
                <div className="col-12">
                  <label className="form-label">Status</label>
                  <select className="form-select" {...input('status')}>
                    {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </div>
              {saveError && <div className="text-danger small mt-3">{saveError}</div>}
              <div className="d-flex gap-2 mt-4 justify-content-end">
                <button type="button" className="btn btn-outline-secondary" onClick={() => setShowAdd(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Saving…' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showUpload && (
        <div style={overlayStyle()} onClick={(e) => e.target === e.currentTarget && setShowUpload(false)}>
          <div style={panelStyle()} className="p-4">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <h4 className="mb-0 h5">Upload equipment CSV</h4>
              <button className="btn-close" onClick={() => setShowUpload(false)}></button>
            </div>
            <div className="small text-secondary mb-3">
              Required columns: <code>code</code>, <code>name</code>, <code>equipment_type</code>, <code>location</code>.
              Optional: <code>status</code> (OPERATIONAL / DEGRADED / MAINTENANCE). Rows with an existing code are skipped.
            </div>
            <label className="btn btn-outline-primary d-block text-center">
              <i className="ti ti-upload me-1"></i> Choose CSV file
              <input ref={fileRef} type="file" accept=".csv,text/csv" hidden onChange={handleUploadFile} />
            </label>
            {uploading && <div className="text-secondary small mt-3">Uploading…</div>}
            {uploadResult && (
              <div className="mt-3 small">
                <div><strong>{uploadResult.created}</strong> added</div>
                <div><strong>{uploadResult.skipped}</strong> skipped (duplicate codes)</div>
                {uploadResult.errors && uploadResult.errors.length > 0 && (
                  <ul className="text-danger mb-0 mt-2 ps-4">
                    {uploadResult.errors.slice(0, 8).map((m, i) => <li key={i}>{m}</li>)}
                  </ul>
                )}
              </div>
            )}
            {uploadError && <div className="text-danger small mt-3">{uploadError}</div>}
            <div className="d-flex gap-2 mt-4 justify-content-end">
              <button className="btn btn-outline-secondary" onClick={() => setShowUpload(false)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}