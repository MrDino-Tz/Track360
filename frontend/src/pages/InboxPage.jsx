import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, endpoints } from '../api';
import { fmtDate, fmtTime, equipmentLabel } from '../format';
import { StatusChip, SeverityChip, Loading, ErrorNote } from '../components/ui';

const STATUSES = ['NEW', 'ACKNOWLEDGED', 'UNDER_REPAIR', 'RESOLVED'];

export default function InboxPage() {
  const [status, setStatus] = useState('');
  const [incidents, setIncidents] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await api.get(endpoints.incidents(status || null));
        if (!cancelled) {
          setIncidents(data);
          setError(null);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      }
    }
    load();
    const timer = setInterval(load, 4000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [status]);

  async function handleSync() {
    setSyncing(true);
    setSyncMsg(null);
    try {
      const result = await api.post(endpoints.smsSync, {});
      setSyncMsg(`Synced ${result.imported ?? 0} new, ${result.prompted ?? 0} prompted, ${result.duplicates ?? 0} duplicate(s), ${result.errors ?? 0} error(s).`);
      const data = await api.get(endpoints.incidents(status || null));
      setIncidents(data);
    } catch (err) {
      setSyncMsg(`Sync failed: ${err.message}`);
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h1 className="fs-3 mb-1">Incident Inbox</h1>
          <p className="mb-0">Every SMS report, newest first</p>
        </div>
        <div className="d-flex align-items-center gap-2">
          <span className="small text-secondary">{incidents.length} incidents</span>
          <button className="btn btn-sm btn-primary" onClick={handleSync} disabled={syncing}>
            <i className={`ti ${syncing ? 'ti-loader ti-spin' : 'ti-refresh'}`}></i>&nbsp;Sync SMS
          </button>
        </div>
      </div>

      {syncMsg && (
        <div className={`alert py-2 ${syncMsg.startsWith('Sync failed') ? 'alert-danger' : 'alert-success'}`}>
          {syncMsg}
        </div>
      )}

      {error && <ErrorNote>Backend unreachable at /api — is FastAPI running on :8000? ({error})</ErrorNote>}

      <div className="mb-3 d-flex gap-2 flex-wrap">
        <button className={`btn btn-sm btn-outline-secondary ${status === '' ? 'active' : ''}`} onClick={() => setStatus('')}>
          ALL
        </button>
        {STATUSES.map((s) => (
          <button key={s} className={`btn btn-sm btn-outline-secondary ${status === s ? 'active' : ''}`} onClick={() => setStatus(s)}>
            {s}
          </button>
        ))}
      </div>

      {loading ? (
        <Loading />
      ) : (
        <div className="card table-responsive">
          <table className="table mb-0 text-nowrap table-hover">
            <thead className="table-light border-light">
              <tr>
                <th>Reported</th>
                <th>Equipment</th>
                <th>Message</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {incidents.length
                ? incidents.map((item) => (
                    <tr key={item.id} className="align-middle">
                      <td className="text-secondary">{fmtDate(item.reported_at)} {fmtTime(item.reported_at)}</td>
                      <td>
                        {item.equipment_id
                          ? <Link className="fw-semibold text-decoration-none" to={`/equipment/${item.equipment_id}`}>{equipmentLabel(item)}</Link>
                          : <span className="text-secondary">Unassigned</span>}
                      </td>
                      <td className="text-secondary">“{item.original_message}”</td>
                      <td><SeverityChip severity={item.severity} /></td>
                      <td><StatusChip status={item.status} /></td>
                      <td>
                        <Link className="btn btn-sm btn-outline-primary" to={`/incidents/${item.id}`}>
                          <i className="ti ti-eye"></i> View
                        </Link>
                      </td>
                    </tr>
                  ))
                : <tr><td colSpan="6" className="text-center text-secondary py-4">No incidents in this view.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}