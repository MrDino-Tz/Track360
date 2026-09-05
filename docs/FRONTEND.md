# Running the Track360 frontend

Track360's UI is a **React SPA** built with Vite (Bootstrap/tabler look inherited
from the InApp template). It talks to the FastAPI backend over `/api/*`.

## Project layout (frontend/)

```
frontend/
  index.html            React entry
  public/               static assets (favicons, logo)
  src/
    main.jsx            React root + HashRouter
    App.jsx             routes
    api.js              fetch helpers + API endpoints
    format.js           formatters (TZS, minutes, dates)
    components/         Layout (sidebar/topbar) + shared UI
    pages/              Dashboard, Incident Inbox/Detail, Equipment List/Detail, 404
    legacy-mpa/         archived template pages (not used)
  dist/                 production build (created by `npm run build`)
  package.json
```

## Prerequisites

- Node.js 20+ and npm
- The FastAPI **backend running on port 8000** — the UI has no mocks; every page
  loads live data from the backend (`/api/dashboard/*`, `/api/incidents`,
  `/api/equipment/*`). See `docs/RUNNING.md`.

## Option A — dev server (for UI development)

From `frontend/`:

```bash
npm install
npm run dev
```

Open http://localhost:5173 (Vite prints the exact port). In dev, Vite proxies
`/api`, `/webhooks` and `/health` to `http://127.0.0.1:8000` (see
`frontend/vite.config.js`), so the UI and backend work together with hot reload.

## Option B — production build, served by the backend

1. Build the SPA (from `frontend/`):

   ```bash
   npm install
   npm run build
   ```

   Output goes to `frontend/dist/`.

2. Start the backend:

   ```bash
   uvicorn app.main:app --reload    # from project root
   ```

3. Open http://127.0.0.1:8000

The backend mounts `frontend/dist` at `/` (`app/main.py`, `create_app`), so the
app and its assets are served from the same origin as the API — no proxy, no CORS.
If `frontend/dist` doesn't exist yet, the backend still serves the API but the
web UI will 404.

## Option C — Docker

The `Dockerfile` builds the frontend (`npm ci && npm run build`) in a Node stage,
then copies `dist` into the Python image. Just run:

```bash
docker compose up --build
```

and open http://localhost:8000.

## Routes (hash-based, no server config needed)

| URL | Page |
| --- | --- |
| `/#/` | Dashboard (KPIs, charts, live SMS feed) |
| `/#/incidents` | Incident Inbox |
| `/#/incidents/:id` | Incident detail / edit |
| `/#/equipment` | Equipment list |
| `/#/equipment/:id` | Equipment history |

Everything under `#/` is client-side — refresh/reload works without any server
rewrite rules.