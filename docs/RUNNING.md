# Running the Track360 backend

How to get the Track360 (PlantDesk) backend running locally, with or without Docker.

> The backend serves the React single-page app from `frontend/dist`. Before you
> can use the web UI you must build the frontend first — see
> [Running the Track360 frontend](FRONTEND.md). The API itself works without it.

## Prerequisites

- Python 3.11+
- (Optional for local dev) [ngrok](https://ngrok.com/) or another public HTTPS tunnel
- (Optional for SMS ack) Africa's Talking credentials

## Quick start (local, no Docker)

From the project root:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # Windows: copy .env.example .env
```

Start the server:

```bash
uvicorn app.main:app --reload
```

The app is then available at:

| Endpoint | URL |
| --- | --- |
| API + dashboard | http://127.0.0.1:8000 |
| Health check | http://127.0.0.1:8000/health |
| SMS webhook | `POST http://127.0.0.1:8000/webhooks/africastalking/sms` |

On first start the app creates SQLite at `data/plant.db`, builds the tables, and
seeds 10 demo plant assets (equipment inventory). No incidents are seeded — the
inbox starts empty until real SMS arrive via the webhook.

## Environment configuration

Edit `.env` to configure behavior:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy URL. Default `sqlite:///./data/plant.db`. Postgres-compatible. |
| `AFRICASTALKING_USERNAME` | Africa's Talking username (`sandbox` for sandbox) |
| `AFRICASTALKING_API_KEY` | API key from the Africa's Talking dashboard |
| `AFRICASTALKING_SENDER_ID` | Optional sender ID for the ack SMS |
| `AFRICASTALKING_SANDBOX` | `true` to use the sandbox endpoint |
| `AFRICASTALKING_SEND_ACK` | `true` to send an acknowledgment SMS after ingest |
| `DEFAULT_PHONE_COUNTRY_CODE` | Country code used when an inbound number starts with `0` (default `255`) |

The webhook does not need the API key — it is only used if outbound acknowledgment
SMS is enabled.

## Running the tests

```bash
pytest -q
```

## Simulating an inbound SMS

With the server running, simulate Africa's Talking POSTing an SMS:

```bash
curl -X POST http://127.0.0.1:8000/webhooks/africastalking/sms \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "from=+255712345678" \
  -d "to=20880" \
  -d "text=M04 machine stopped working" \
  -d "id=ATXid_local_001" \
  -d "date=2026-09-05 12:42:00"
```

Expect an HTTP 200 with body `GOOD`. Refresh the dashboard (or wait 4s for the
auto-poll) — a NEW incident for **M04 — Conveyor** should appear.

## Exposing the webhook publicly

Africa's Talking cannot reach `localhost`. Tunnel the backend:

```bash
ngrok http 8000
```

Copy the HTTPS origin, e.g. `https://abc123.ngrok-free.app`. The public callback is:

```
https://<public-domain>/webhooks/africastalking/sms
```

Keep uvicorn running while the tunnel is open.

### Configure the Africa's Talking callback

1. Log in to the [Africa's Talking dashboard](https://account.africastalking.com/).
2. Open **SMS**.
3. Set **Incoming Messages** callback URL to the public URL above.
4. Save.

Out-of-the-box, the webhook accepts the real form-encoded POST body Africa's
Talking sends: `from`, `to`, `text`, `id`, `date`, `linkId`.

## Running with Docker

From the project root:

```bash
cp .env.example .env
docker compose up --build
```

The app is at http://localhost:8000. SQLite is persisted in the `plant-data` volume.

## Demo procedure

1. Open http://127.0.0.1:8000 and confirm **New Incidents** starts at 0 / the inbox is empty.
2. Start the public tunnel and set the Africa's Talking incoming-message callback.
3. From a phone, SMS the Africa's Talking number: `M04 machine stopped working`.
4. Africa's Talking POSTs to `/webhooks/africastalking/sms`.
5. The dashboard feed updates on its own — a NEW card for **M04 — Conveyor** appears.
6. Open the incident, set severity **HIGH** and status **UNDER_REPAIR**, save.
7. Later record repair notes, cost, downtime, and status **RESOLVED**.
8. Open **Equipment → M04 — Conveyor** — the incident is permanent history.

## API reference

| Method | Path |
| --- | --- |
| GET | `/health` |
| POST | `/webhooks/africastalking/sms` |
| GET | `/api/equipment` |
| POST | `/api/equipment` |
| GET | `/api/equipment/{id}` |
| GET | `/api/equipment/{id}/incidents` |
| GET | `/api/incidents` |
| GET | `/api/incidents/{id}` |
| PATCH | `/api/incidents/{id}` |
| GET | `/api/dashboard/summary` |
| GET | `/api/dashboard/recent-incidents` |

Incident statuses: `NEW`, `ACKNOWLEDGED`, `UNDER_REPAIR`, `RESOLVED`.
