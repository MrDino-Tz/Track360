import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, endpoints } from '../api';
import { fmtTZS, fmtMinutes } from '../format';
import { EqChip, Loading, ErrorNote } from '../components/ui';

export default function EquipmentListPage() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');

  useEffect(() => {
    let cancelled = false;
    api.get(endpoints.equipment)
      .then((data) => {
        if (!cancelled) {
          setRows(data);
          setError(null);
          setLoading(false);
        }
      })
      .catch((err) => !cancelled && (setError(err.message), setLoading(false)));
    return () => {
      cancelled = true;
    };
  }, []);

  const q = query.toLowerCase();
  const filtered = rows.filter((r) =>
    [r.code, r.name, r.equipment_type, r.location].some((v) => (v || '').toLowerCase().includes(q))
  );

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h1 className="fs-3 mb-1">Equipment</h1>
          <p className="mb-0">Plant assets and their SMS incident history</p>
        </div>
        <span className="small text-secondary">{rows.length} assets</span>
      </div>

      {error && <ErrorNote>Backend unreachable at /api — is FastAPI running on :8000? ({error})</ErrorNote>}

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
                : <tr><td colSpan="9" className="text-center text-secondary py-4">No equipment matches “{query}”.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}