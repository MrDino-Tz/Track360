# Running the Thibitisha backend

How to get the Thibitisha backend running locally, with or without Docker.

> The backend serves the React single-page app from `frontend/dist`. Before you
> can use the web UI you must build the frontend first — see
> [Running the Thibitisha frontend](FRONTEND.md). The API itself works without it.

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
| USSD webhook | `POST http://127.0.0.1:8000/webhooks/africastalking/ussd` |

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
| `THIBITISHA_GROQ_API_KEY` | Groq API key — enables equipment-specific AI questions in the two-way SMS prompt |
| `THIBITISHA_GROQ_MODEL` | Groq model id (default `groq/compound-mini`) |
| `AFRICASTALKING_PAYMENTS_PRODUCT_NAME` | Payments product name (AT dashboard) required for mobile-money rewards |
| `REWARD_DEFAULT_AMOUNT` | Default reward amount in TZS used when none is given (default `1000`) |
| `REWARD_CURRENCY` | Reward currency, ISO code (default `TZS`) |
| `DEFAULT_PHONE_COUNTRY_CODE` | Country code used when an inbound number starts with `0` (default `255`) |

The webhook does not need the API key — it is only used if outbound acknowledgment
SMS is enabled.

The outbound acknowledgment SMS is sent through the official
[africastalking Python SDK](https://developers.africastalking.com/sdks)
(`africastalking` package, `SMS.send()`). The sandbox is selected automatically
when `AFRICASTALKING_SANDBOX=true` (SDK username is forced to `sandbox`), so in
sandbox mode the API key alone is enough to configure it.

### AI-assisted questions

When a worker texts just an equipment code (e.g. `COMP01`), the two-way SMS
flow uses [Groq](https://groq.com) to generate 5 equipment-specific condition
questions tailored to that asset's type and location — instead of the generic
menu. If `GROQ_API_KEY` is unset or the request fails, Thibitisha silently falls
back to the generic condition list, so the SMS flow never breaks. See
`app/services/ai.py`. (Requires `pip install groq`, already in
`requirements.txt`.)

### Admin AI chat

The dashboard's **AI Assistant** tab (`POST /api/ai/chat`) lets a shift admin
chat with the same Groq model. The system prompt includes a live snapshot of
the facility (equipment count + recent open incidents), so answers are grounded
in the current state. Request body: `{"message": "...", "history": [{"role":
"user|assistant", "content": "..." }]}` → `{"reply": "...", "model": "..."}`.
Returns `503` when `GROQ_API_KEY` is unset, `502` on a Groq failure. See
`app/routers/ai_chat.py`.

### Report rewards

The incident page lets an admin thank a reporter with a payout to their phone
number:

| Method | What it does | Requirements |
| --- | --- | --- |
| `AIRTIME` | Sends mobile airtime via the Afrika's Talking Airtime API (`POST /version1/airtime/send`, installed SDK) | Sandbox simulates; production needs airtime credit |
| `MOBILE_MONEY` | Sends TZS via the Payments B2C API (`POST /mobile/b2c/request`) | `AFRICASTALKING_PAYMENTS_PRODUCT_NAME` configured (create the payments product in the AT dashboard — possible even in sandbox) |

Endpoints:

- `POST /api/incidents/{id}/reward` — body `{"method": "AIRTIME|MOBILE_MONEY", "amount?"}` (default amount = `REWARD_DEFAULT_AMOUNT`). Returns the recorded reward and stores it in the `rewards` table.
- `GET /api/incidents/{id}/rewards` — payout history for the incident.

Every send is recorded (method, amount, provider status/reference) even on
failure. In the sandbox nothing real is disbursed — payouts only move money in
production mode. See `app/services/rewards.py`.

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
  -d "to=10096" \
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

## USSD

Thibitisha exposes a USSD handler at `POST /webhooks/africastalking/ussd` that
follows the Africa's Talking USSD protocol (`application/x-www-form-urlencoded`,
`CON`/`END` replies in `text/plain`). It lets a worker report an equipment
condition from a feature phone:

```
Dial the USSD code
CON Thibitisha Equipment Report
   Enter equipment code or name:

Reply: COMP01
CON Select condition:
   1. Leaking
   2. Overheating
   ... (see CONDITION_MENU in app/services/conversation.py)

Reply: 2
END Incident #3 logged for Air Compressor (COMP01).
    Condition: Overheating.
```

A response starting with `CON` keeps the session open; `END` ends it.
Each session creates at most one incident (deduplicated by `sessionId`).
The response header `at-ussd-hop-metadata` labels the current menu hop
(`codeEntry`, `equip:<code>`, `incidentCreated`, `invalid`).

Simulate it locally with curl:

```bash
curl -X POST http://127.0.0.1:8000/webhooks/africastalking/ussd \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "sessionId=demo1" -d "serviceCode=*384*100#" \
  -d "phoneNumber=+255712345678" -d "text="         # first hop
curl -X POST http://127.0.0.1:8000/webhooks/africastalking/ussd \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "sessionId=demo1" -d "serviceCode=*384*100#" \
  -d "phoneNumber=+255712345678" -d "text=COMP01"   # second hop
curl -X POST http://127.0.0.1:8000/webhooks/africastalking/ussd \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "sessionId=demo1" -d "serviceCode=*384*100#" \
  -d "phoneNumber=+255712345678" -d "text=COMP01*2" # third hop -> END
```

To go live you must also register a USSD service code with Africa's Talking
and point its **USSD callback URL** at
`https://<public-domain>/webhooks/africastalking/ussd`.

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
| POST | `/webhooks/africastalking/ussd` |
| POST | `/ussd` |
| POST | `/api/sms/sync` |
| POST | `/api/ai/chat` |
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
