import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import ApexCharts from 'apexcharts';
import { api, endpoints } from '../api';
import { fmtMinutes, fmtTZS, isFresh, equipmentLabel, fmtTime } from '../format';
import { KpiCard, SimpleStat, Loading, ErrorNote, StatusChip, SeverityChip } from '../components/ui';

const DAY_MS = 86400000;
const num = (v) => (v == null || v === '' ? 0 : Number(v));

function IncidentCard({ item }) {
  const fresh = isFresh(item.reported_at);
  return (
    <div className={`border rounded-2 p-3 mb-2 ${fresh ? 'border-primary' : 'border-light'}`}>
      <div className="d-flex justify-content-between align-items-start gap-2">
        <div>
          <span className="fw-semibold">{equipmentLabel(item)}</span>
          <div className="mb-1">
            <StatusChip status={item.status} /> <SeverityChip severity={item.severity} />
          </div>
        </div>
        <span className="small text-secondary">{fmtTime(item.reported_at)}</span>
      </div>
      <p className="mb-1">“{item.original_message}”</p>
      <div className="small text-secondary d-flex gap-3 flex-wrap">
        <span><i className="ti ti-phone"></i> {item.sender_phone}</span>
        <span><i className="ti ti-message"></i> {item.channel}</span>
      </div>
      <Link className="small text-primary text-decoration-none" to={`/incidents/${item.id}`}>
        Open incident <i className="ti ti-arrow-right"></i>
      </Link>
    </div>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [error, setError] = useState(null);
  const trendRef = useRef(null);
  const donutRef = useRef(null);
  const trendChart = useRef(null);
  const donutChart = useRef(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [nextSummary, nextIncidents] = await Promise.all([
          api.get(endpoints.summary),
          api.get(endpoints.recentIncidents),
        ]);
        if (cancelled) return;
        setSummary(nextSummary);
        setIncidents(nextIncidents);
        setError(null);
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }

    load();
    const timer = setInterval(load, 4000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (!summary) return;
    if (!trendChart.current && trendRef.current) {
      trendChart.current = new ApexCharts(trendRef.current, {
        chart: { type: 'bar', height: 320, toolbar: { show: false } },
        colors: ['#E66239'],
        series: [{ name: 'Incidents', data: [] }],
        plotOptions: { bar: { columnWidth: '55%', borderRadius: 3 } },
        dataLabels: { enabled: false },
        grid: { borderColor: '#e2e8f0' },
        xaxis: { categories: [], axisBorder: { show: false } },
        yaxis: { labels: { formatter: (v) => Math.round(v) } },
      });
      trendChart.current.render();
    }
    if (!donutChart.current && donutRef.current) {
      donutChart.current = new ApexCharts(donutRef.current, {
        chart: { type: 'donut', height: 320 },
        series: [],
        labels: [],
        colors: ['#FB2C36', '#F0B100', '#00B8DB'],
        stroke: { width: 0 },
        dataLabels: { enabled: false },
        legend: { position: 'bottom' },
        plotOptions: { pie: { donut: { labels: { show: true, total: { show: true, label: 'Open' } } } } },
      });
      donutChart.current.render();
    }

    const now = new Date();
    now.setHours(0, 0, 0, 0);
    const labels = [];
    const buckets = [];
    for (let i = 13; i >= 0; i--) {
      const d = new Date(now.getTime() - i * DAY_MS);
      labels.push(d.toLocaleDateString([], { day: '2-digit', month: 'short' }));
      buckets.push(0);
    }
    for (const item of incidents) {
      const d = item.reported_at ? new Date(item.reported_at.endsWith('Z') || item.reported_at.includes('+') ? item.reported_at : item.reported_at + 'Z') : null;
      if (!d) continue;
      const idx = Math.floor((now.getTime() - d.getTime()) / DAY_MS);
      if (idx >= 0 && idx < 14) buckets[13 - idx] += 1;
    }
    if (trendChart.current) {
      trendChart.current.updateOptions({ xaxis: { categories: labels } });
      trendChart.current.updateSeries([{ name: 'Incidents', data: buckets }]);
    }

    if (donutChart.current && trendChart.current) {
      const ack = Math.max(0, num(summary.open_incidents) - num(summary.under_repair) - num(summary.new_incidents));
      donutChart.current.updateOptions({ labels: ['NEW', 'ACKNOWLEDGED', 'UNDER_REPAIR'] });
      donutChart.current.updateSeries([num(summary.new_incidents), ack, num(summary.under_repair)]);
    }
  }, [summary, incidents]);

  return (
    <div>
      <div className="mb-6">
        <h1 className="fs-3 mb-1">Thibitisha</h1>
        <p className="mb-0">SMS &amp; USSD equipment incident desk — a texted fault becomes a trackable incident.</p>
      </div>

      {error && <ErrorNote>Backend unreachable at /api — is FastAPI running on :8000? ({error})</ErrorNote>}

      {!summary ? (
        <Loading />
      ) : (
        <>
          <div className="row g-3 mb-3">
            <div className="col-6 col-xl-3">
              <KpiCard icon="ti ti-building-factory" iconClass="bg-primary" title="Total Equipment" value={num(summary.total_equipment)} extra="plant assets" extraClass="text-primary" />
            </div>
            <div className="col-6 col-xl-3">
              <KpiCard icon="ti ti-message-exclamation" iconClass="bg-danger" title="New Incidents" value={num(summary.new_incidents)} extra="awaiting review" extraClass="text-danger" />
            </div>
            <div className="col-6 col-xl-3">
              <KpiCard icon="ti ti-alert-triangle" iconClass="bg-info" title="Open Incidents" value={num(summary.open_incidents)} extra="not yet resolved" extraClass="text-info" />
            </div>
            <div className="col-6 col-xl-3">
              <KpiCard icon="ti ti-wrench" iconClass="bg-warning" title="Under Repair" value={num(summary.under_repair)} extra="in maintenance" extraClass="text-warning" />
            </div>
          </div>

          <div className="row g-3 mb-3">
            <div className="col-6 col-xl-3">
              <SimpleStat label="Resolved Today" value={num(summary.resolved_today)} extra={<><i className="ti ti-circle-check"></i> closed incidents</>} extraClass="text-success" />
            </div>
            <div className="col-6 col-xl-3">
              <SimpleStat label="Incidents This Month" value={num(summary.incidents_this_month)} extra={<><i className="ti ti-calendar-month"></i> reported since the 1st</>} />
            </div>
            <div className="col-6 col-xl-3">
              <SimpleStat label="Maintenance Cost" value={fmtTZS(summary.maintenance_cost)} extra={<><i className="ti ti-cash"></i> total repair spend</>} />
            </div>
            <div className="col-6 col-xl-3">
              <SimpleStat label="Total Downtime" value={fmtMinutes(summary.total_downtime_minutes)} extra={<><i className="ti ti-clock"></i> accumulated downtime</>} />
            </div>
          </div>

          <div className="row g-3 mb-3">
            <div className="col-12 col-lg-7">
              <div className="card h-100">
                <div className="card-header d-flex justify-content-between align-items-center bg-transparent px-4 py-3">
                  <h3 className="h5 mb-0">Incidents — last 14 days</h3>
                  <span className="badge bg-primary-subtle text-primary">auto-refresh 4s</span>
                </div>
                <div className="card-body p-4">
                  <div ref={trendRef}></div>
                </div>
              </div>
            </div>
            <div className="col-12 col-lg-5">
              <div className="card h-100">
                <div className="card-header d-flex justify-content-between align-items-center bg-transparent px-4 py-3">
                  <h3 className="h5 mb-0">Open Incidents by Status</h3>
                </div>
                <div className="card-body p-4">
                  <div ref={donutRef}></div>
                </div>
              </div>
            </div>
          </div>

          <div className="row g-3">
            <div className="col-lg-6">
              <div className="card h-100">
                <div className="card-header bg-white d-flex justify-content-between align-items-center px-4 py-3">
                  <h4 className="mb-0 h5"><i className="ti ti-message-heart me-1"></i> Incoming Incident Feed</h4>
                  <Link className="small text-primary text-decoration-underline" to="/incidents">Open inbox</Link>
                </div>
                <div className="card-body p-3">
                  {incidents.length
                    ? incidents.map((item) => <IncidentCard key={item.id} item={item} />)
                    : <div className="text-secondary p-3">No incidents yet. Send an SMS to the Africa's Talking number.</div>}
                </div>
              </div>
            </div>
            <div className="col-lg-6">
              <div className="card mb-3">
                <div className="card-header bg-white px-4 py-3"><h4 className="mb-0 h5">Maintenance Intelligence</h4></div>
                <div className="card-body p-4">
                  {summary.insights && summary.insights.length
                    ? summary.insights.map((text, i) => (
                        <div key={i} className="d-flex gap-2 align-items-start mb-2">
                          <i className="ti ti-alert-triangle text-danger mt-1"></i>
                          <span>{text}</span>
                        </div>
                      ))
                    : <div className="text-secondary">No recurring-failure warnings in the last 30 days.</div>}
                </div>
              </div>
              <div className="card mb-3">
                <div className="card-header bg-white px-4 py-3"><h4 className="mb-0 h5">Most Frequent Failures</h4></div>
                <div className="card-body p-4 pt-2">
                  {summary.failing_equipment && summary.failing_equipment.length
                    ? summary.failing_equipment.slice(0, 6).map((row) => (
                        <div key={row.equipment_id} className="d-flex justify-content-between align-items-center border-bottom py-2">
                          <Link className="text-decoration-none" to={`/equipment/${row.equipment_id}`}>
                            <span className="fw-semibold">{row.code}</span>
                            <span className="text-secondary ms-2">{row.name}</span>
                          </Link>
                          <span className="small text-secondary">
                            {row.incident_count} · {fmtTZS(row.total_repair_cost)} · {fmtMinutes(row.total_downtime_minutes)}
                          </span>
                        </div>
                      ))
                    : <div className="text-secondary">No failure data yet.</div>}
                </div>
              </div>
              <div className="card">
                <div className="card-header bg-white px-4 py-3"><h4 className="mb-0 h5">Recurring Categories</h4></div>
                <div className="card-body p-4 pt-2">
                  {summary.recurring_categories && summary.recurring_categories.length
                    ? summary.recurring_categories.map((row) => (
                        <div key={row.category} className="d-flex justify-content-between border-bottom py-2">
                          <span>{row.category}</span>
                          <span className="badge bg-primary-subtle text-primary">{row.count}</span>
                        </div>
                      ))
                    : <div className="text-secondary">No data yet.</div>}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}