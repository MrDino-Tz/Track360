import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api, endpoints } from '../api';
import { fmtTZS, fmtMinutes, fmtDate } from '../format';
import { EqChip, StatusChip, SimpleStat, Loading, ErrorNote } from '../components/ui';

export default function EquipmentDetailPage() {
  const { id } = useParams();
  const [item, setItem] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.get(endpoints.equipmentItem(id)), api.get(endpoints.equipmentIncidents(id))])
      .then(([eq, history]) => {
        if (cancelled) return;
        setItem(eq);
        setIncidents(history);
        setError(null);
      })
      .catch((err) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) return <ErrorNote>Backend unreachable at /api — is FastAPI running on :8000? ({error})</ErrorNote>;
  if (!item) return <Loading />;

  return (
    <div>
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 gap-3">
        <div>
          <h1 className="fs-3 mb-1">
            {item.code} — {item.name} <EqChip status={item.status} />
          </h1>
          <p className="mb-0">{item.equipment_type} · {item.location}</p>
        </div>
        <div>
          <Link to="/equipment" className="btn btn-outline-secondary"><i className="ti ti-arrow-left"></i> Back to equipment</Link>
        </div>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-6 col-lg-3"><SimpleStat label="Incidents" value={item.incident_count} /></div>
        <div className="col-6 col-lg-3"><SimpleStat label="Open" value={item.open_count} /></div>
        <div className="col-6 col-lg-3"><SimpleStat label="Total repair cost" value={fmtTZS(item.total_repair_cost)} /></div>
        <div className="col-6 col-lg-3"><SimpleStat label="Total downtime" value={fmtMinutes(item.total_downtime_minutes)} /></div>
      </div>

      <div className="card table-responsive">
        <div className="card-header bg-white px-4 py-3"><h4 className="mb-0 h5">History</h4></div>
        <table className="table mb-0 text-nowrap table-hover">
          <thead className="table-light border-light">
            <tr><th>Date</th><th>Message</th><th>Channel</th><th>Status</th><th>Cost</th></tr>
          </thead>
          <tbody>
            {incidents.length
              ? incidents.map((row) => (
                  <tr key={row.id} className="align-middle">
                    <td><Link className="text-decoration-none" to={`/incidents/${row.id}`}>{fmtDate(row.reported_at)}</Link></td>
                    <td>“{row.original_message}”</td>
                    <td>{row.channel}</td>
                    <td><StatusChip status={row.status} /></td>
                    <td>{fmtTZS(row.repair_cost)}</td>
                  </tr>
                ))
              : <tr><td colSpan="5" className="text-center text-secondary py-4">No incidents recorded for this asset.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}