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

function Chip({ text, color }) {
  return <span className={`badge ${color}`}>{text.replace(/_/g, ' ')}</span>;
}

export function StatusChip({ status }) {
  return <Chip text={status} color={STATUS_COLOR[status] || 'bg-secondary'} />;
}

export function SeverityChip({ severity }) {
  return <Chip text={severity} color={SEVERITY_COLOR[severity] || 'bg-secondary'} />;
}

export function EqChip({ status }) {
  return <Chip text={status} color={EQ_STATUS_COLOR[status] || 'bg-secondary'} />;
}

export function KpiCard({ icon, iconClass, title, value, extra, extraClass }) {
  return (
    <div className={`card p-4 ${iconClass ? '' : 'h-100'}`}>
      <div className="d-flex gap-3">
        <div className={`icon-shape icon-md ${iconClass} text-white rounded-2`}>
          <i className={`${icon} fs-4`}></i>
        </div>
        <div className="w-100">
          <h2 className="mb-3 fs-6">{title}</h2>
          <h3 className="fw-bold mb-0">{value}</h3>
          {extra && <p className={`mb-0 small ${extraClass || 'text-secondary'}`}>{extra}</p>}
        </div>
      </div>
    </div>
  );
}

export function SimpleStat({ label, value, extra, extraClass }) {
  return (
    <div className="card h-100">
      <div className="card-body p-4">
        <span className="text-secondary small">{label}</span>
        <h3 className="mb-1 fw-bold">{value}</h3>
        {extra && <p className={`mb-0 small ${extraClass || 'text-secondary'}`}>{extra}</p>}
      </div>
    </div>
  );
}

export function Loading() {
  return <div className="text-secondary py-4 text-center">Loading…</div>;
}

export function ErrorNote({ children }) {
  return <div className="text-danger small py-2">{children}</div>;
}