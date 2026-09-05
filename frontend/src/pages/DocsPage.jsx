export default function DocsPage() {
  return (
    <div>
      <h1 className="fs-3 mb-1">Docs</h1>
      <p className="mb-4">Quick notes for the Track360 front-end (React + Vite + Bootstrap) and its FastAPI backend.</p>

      <div className="row g-3">
        <div className="col-lg-6">
          <div className="card h-100">
            <div className="card-header bg-white px-4 py-3"><h4 className="mb-0 h5">Run the app</h4></div>
            <div className="card-body p-4">
              <ol>
                <li className="mb-2">Start the backend (FastAPI on <code>:8000</code>).</li>
                <li className="mb-2">
                  <pre className="bg-light border rounded p-3 mt-2"><code>npm install</code></pre>
                </li>
                <li>
                  <pre className="bg-light border rounded p-3 mt-2"><code>npm run dev</code></pre>
                </li>
              </ol>
              <p className="small text-secondary mb-0">
                The dev server proxies <code>/api</code>, <code>/webhooks</code> and <code>/health</code> to the
                FastAPI backend on <code>127.0.0.1:8000</code>.
              </p>
            </div>
          </div>
        </div>
        <div className="col-lg-6">
          <div className="card h-100">
            <div className="card-header bg-white px-4 py-3"><h4 className="mb-0 h5">Routes</h4></div>
            <div className="card-body p-4">
              <ul className="mb-0">
                <li><code>#/</code> — Dashboard (KPIs, charts, live feed)</li>
                <li><code>#/incidents</code> — Incident Inbox</li>
                <li><code>#/incidents/:id</code> — Incident detail / edit</li>
                <li><code>#/equipment</code> — Equipment list</li>
                <li><code>#/equipment/:id</code> — Equipment history</li>
                <li><code>#/docs</code> — This page</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}