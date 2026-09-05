# PlantDesk

Manufacturing equipment incident reporting over ordinary SMS.

A worker sends `M04 machine stopped working` to an Africa's Talking number. Africa's Talking posts that message to this backend. The backend stores the SMS, creates an incident, and the dashboard shows it within a few seconds.

**Send an SMS about an equipment problem, and it becomes a trackable incident on the manufacturing dashboard.**

This MVP does not include USSD, Voice, IoT, or predictive maintenance.

## Architecture

```
Phone
  → SMS
Africa's Talking
  → HTTP POST /webhooks/africastalking/sms
FastAPI
  → SQLite
  → REST API
  → PlantDesk dashboard
```

Local development uses a public HTTPS tunnel (ngrok or similar) so Africa's Talking can reach the webhook.

## Installation

Python 3.11+ is required.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

On macOS or Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Put your Africa's Talking credentials in `.env`. Never put them in frontend code.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `AFRICASTALKING_USERNAME` | Africa's Talking username (`sandbox` for the sandbox) |
| `AFRICASTALKING_API_KEY` | API key from the Africa's Talking dashboard |
| `AFRICASTALKING_SENDER_ID` | Optional sender ID for acknowledgement SMS |
| `AFRICASTALKING_SANDBOX` | `true` to use the sandbox messaging endpoint |
| `AFRICASTALKING_SEND_ACK` | `true` to send an optional acknowledgement SMS after ingest |
| `DATABASE_URL` | SQLAlchemy URL. Default is SQLite: `sqlite:///./data/plant.db` |
| `DEFAULT_PHONE_COUNTRY_CODE` | Used when an inbound number starts with `0`. Default `255` |

The webhook itself does not need the API key. The key is only used if outbound acknowledgement SMS is enabled.

## Database initialization

SQLite is created automatically on first start at `data/plant.db`.

Tables are created with SQLAlchemy `create_all`. If the equipment table is empty, the app seeds 10 plant assets and historical incidents.

The schema is PostgreSQL-compatible. To switch later, set `DATABASE_URL` to a Postgres URL. No models need to change.

## Running the backend

From the project root:

```bash
uvicorn app.main:app --reload
```

- API and dashboard: http://127.0.0.1:8000
- Health: http://127.0.0.1:8000/health
- Webhook: `POST http://127.0.0.1:8000/webhooks/africastalking/sms`

## Running the frontend

The dashboard is static files served by FastAPI. Opening http://127.0.0.1:8000 is enough.

Screens:

1. Dashboard — KPIs and the incoming incident feed
2. Incident Inbox
3. Incident Detail
4. Equipment List
5. Equipment Detail / History

The feed polls `/api/dashboard/recent-incidents` every 4 seconds.

## Exposing the callback publicly

Africa's Talking cannot call `localhost`. During the hackathon, tunnel the backend:

```bash
ngrok http 8000
```

Copy the HTTPS origin, for example `https://abc123.ngrok-free.app`.

The public callback URL is:

```
https://<public-domain>/webhooks/africastalking/sms
```

Leave uvicorn running while the tunnel is open.

## Configuring the Africa's Talking SMS callback

1. Log in to the [Africa's Talking dashboard](https://account.africastalking.com/).
2. Open **SMS**.
3. Set the **Incoming Messages** callback URL to `https://<public-domain>/webhooks/africastalking/sms`.
4. Save.

The app accepts the real form-encoded POST body Africa's Talking sends:

- `from` — sender phone
- `to` — shortcode or service number
- `text` — original SMS
- `id` — Africa's Talking message id (used to ignore duplicate callbacks)
- `date` — received time
- `linkId` — optional

The webhook responds with HTTP 200 and body `GOOD` after the incident is saved.

## Testing inbound SMS

### Automated tests

```bash
pytest -q
```

### Simulate Africa's Talking locally

PowerShell:

```powershell
curl.exe -X POST http://127.0.0.1:8000/webhooks/africastalking/sms `
  -H "Content-Type: application/x-www-form-urlencoded" `
  -d "from=+255712345678" `
  -d "to=20880" `
  -d "text=M04 machine stopped working" `
  -d "id=ATXid_local_001" `
  -d "date=2026-09-05+12:42:00"
```

Command Prompt:

```bat
curl -X POST http://127.0.0.1:8000/webhooks/africastalking/sms ^
  -H "Content-Type: application/x-www-form-urlencoded" ^
  -d "from=+255712345678" ^
  -d "to=20880" ^
  -d "text=M04 machine stopped working" ^
  -d "id=ATXid_local_001" ^
  -d "date=2026-09-05+12:42:00"
```

macOS / Linux:

```bash
curl -X POST http://127.0.0.1:8000/webhooks/africastalking/sms \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "from=+255712345678" \
  -d "to=20880" \
  -d "text=M04 machine stopped working" \
  -d "id=ATXid_local_001" \
  -d "date=2026-09-05+12:42:00"
```

Refresh the dashboard. A NEW incident for **M04 — Conveyor** should appear without restarting the app.

If the SMS has no known equipment code, the incident is still stored as **Unassigned**.

## Demo procedure

1. Open http://127.0.0.1:8000. Confirm **New Incidents: 2**.
2. Start the public tunnel and set the Africa's Talking incoming-message callback.
3. From a phone, SMS the Africa's Talking number:

   `M04 machine stopped working`

4. Africa's Talking receives the SMS and POSTs to `/webhooks/africastalking/sms`.
5. The dashboard feed updates on its own. The new card shows:

   - NEW
   - M04 — Conveyor
   - "M04 machine stopped working"
   - reporter phone
   - Channel SMS

6. Open the incident. Set severity **HIGH** and status **UNDER_REPAIR**. Save.
7. Later record repair notes `Motor replaced`, cost `300000`, downtime `120`, status **RESOLVED**.
8. Open **Equipment → M04 — Conveyor**. The incident is now permanent history.

## Docker

```bash
copy .env.example .env
docker compose up --build
```

The app is at http://localhost:8000. SQLite is stored in the `plant-data` volume.

## API

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
