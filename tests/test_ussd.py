from fastapi.testclient import TestClient

from app.main import app

USSD = "/webhooks/africastalking/ussd"


def _ussd(client, text, session="sess_1", phone="+255712345678", service="384"):
    return client.post(
        USSD,
        data={
            "sessionId": session,
            "serviceCode": service,
            "phoneNumber": phone,
            "text": text,
        },
    )


def _incident_count(client):
    return len(client.get("/api/incidents").json())


def test_initial_prompt_asks_for_equipment_code(client):
    resp = _ussd(client, "")
    assert resp.status_code == 200
    body = resp.content.decode()
    assert body.startswith("CON ")
    assert "Thibitisha Equipment Report" in body
    assert "Enter equipment code or name" in body
    assert resp.headers.get("at-ussd-hop-metadata") == "codeEntry"


def test_enter_equipment_code_shows_conditions(client):
    resp = _ussd(client, "COMP01")
    body = resp.content.decode()
    assert body.startswith("CON ")
    assert "Select condition" in body
    assert "Leaking" in body
    assert "Other" in body
    assert resp.headers.get("at-ussd-hop-metadata") == "equip:COMP01"


def test_enter_equipment_name_shows_conditions(client):
    resp = _ussd(client, "Air Compressor")
    assert resp.headers.get("at-ussd-hop-metadata") == "equip:COMP01"


def test_enter_equipment_name_without_spaces_shows_conditions(client):
    # Some USSD keypads drop spaces when typing a free-text value.
    resp = _ussd(client, "aircompressor")
    assert resp.headers.get("at-ussd-hop-metadata") == "equip:COMP01"


def test_enter_name_then_condition_creates_incident(client):
    before = _incident_count(client)
    resp = _ussd(client, "water pump*3")
    body = resp.content.decode()
    assert body.startswith("END Thank you for your report")
    assert "Incident #" in body
    assert "Water Pump (PUMP01)" in body
    assert _incident_count(client) == before + 1
    incident = client.get("/api/incidents").json()[0]
    assert incident["equipment"]["code"] == "PUMP01"
    assert incident["category"] == "STOPPAGE"


def test_lowercase_code_and_space_are_tolerated(client):
    resp = _ussd(client, "comp01")
    assert resp.content.decode().startswith("CON ")
    assert resp.headers.get("at-ussd-hop-metadata") == "equip:COMP01"


def test_pick_condition_creates_incident(client):
    before = _incident_count(client)
    resp = _ussd(client, "COMP01*2")
    body = resp.content.decode()
    assert body.startswith("END ")
    assert "logged for Air Compressor (COMP01)" in body
    assert _incident_count(client) == before + 1

    incident = client.get("/api/incidents").json()[0]
    assert incident["channel"] == "USSD"
    assert incident["equipment"]["code"] == "COMP01"
    assert incident["original_message"] == "COMP01 Overheating"
    assert incident["category"] == "OVERHEATING"
    assert incident["sender_phone"] == "+255712345678"


def test_unknown_equipment_code_returns_end(client):
    resp = _ussd(client, "UNKNOWN")
    assert resp.content.decode().startswith("END Unknown equipment")


def test_invalid_condition_returns_end(client):
    resp = _ussd(client, "COMP01*99")
    assert resp.content.decode().startswith("END Invalid condition")


def test_same_session_dedupes_on_resubmit(client):
    before = _incident_count(client)
    _ussd(client, "M01*1", session="dup_sess")
    assert _incident_count(client) == before + 1
    # Resubmitting the same full path for the same session should not
    # create a duplicate (dedup by external_message_id = ussd:session_id).
    _ussd(client, "M01*1", session="dup_sess")
    assert _incident_count(client) == before + 1


def test_short_ussd_path_alias_works(client):
    # The AT dashboard callback is often configured as https://<host>/ussd.
    resp = client.post(
        "/ussd",
        data={
            "sessionId": "alias_sess",
            "serviceCode": "384",
            "phoneNumber": "+255712345678",
            "text": "COMP01*2",
        },
    )
    assert resp.status_code == 200
    body = resp.content.decode()
    assert body.startswith("END Thank you for your report")
    assert "logged for Air Compressor (COMP01)" in body
    # Same session should not duplicate through the alias either.
    count = _incident_count(client)
    client.post(
        "/ussd",
        data={
            "sessionId": "alias_sess",
            "serviceCode": "384",
            "phoneNumber": "+255712345678",
            "text": "COMP01*2",
        },
    )
    assert _incident_count(client) == count