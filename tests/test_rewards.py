from types import SimpleNamespace

import pytest

WEBHOOK = "/webhooks/africastalking/sms"


@pytest.fixture
def incident_id(client):
    client.post(
        WEBHOOK,
        data={
            "from": "+255712345678",
            "to": "10096",
            "text": "COMP01 air pressure dropping",
            "id": "rw_inc_001",
            "date": "2026-09-05 12:42:00",
        },
    )
    return client.get("/api/incidents").json()[0]["id"]


def test_airtime_reward_success(monkeypatch, client, incident_id):
    import app.services.rewards as rewards_svc

    monkeypatch.setattr(
        rewards_svc,
        "send_airtime",
        lambda phone, amount: {
            "ok": True,
            "provider_status": "Success",
            "provider_reference": "ATreq_123",
            "message": "ok",
        },
    )

    resp = client.post(
        f"/api/incidents/{incident_id}/reward",
        json={"method": "AIRTIME", "amount": 500},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["method"] == "AIRTIME"
    assert body["sender_phone"] == "+255712345678"
    assert float(body["amount"]) == 500
    assert body["provider_status"] == "Success"
    assert body["provider_reference"] == "ATreq_123"

    history = client.get(f"/api/incidents/{incident_id}/rewards").json()
    assert len(history) == 1
    assert history[0]["method"] == "AIRTIME"


def test_mobile_money_reward_success(monkeypatch, client, incident_id):
    import app.routers.rewards as rewards_router
    import app.services.rewards as rewards_svc

    settings = SimpleNamespace(
        africastalking_payments_product_name="ThibitishaRewards",
        reward_default_amount=1000,
        reward_currency="TZS",
    )
    monkeypatch.setattr(rewards_router, "get_settings", lambda: settings)

    monkeypatch.setattr(
        rewards_svc,
        "send_mobile_money",
        lambda phone, amount: {
            "ok": True,
            "provider_status": "Queued",
            "provider_reference": "ATP_abc",
            "message": "queued",
        },
    )

    resp = client.post(
        f"/api/incidents/{incident_id}/reward",
        json={"method": "MOBILE_MONEY", "amount": 2000},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["method"] == "MOBILE_MONEY"
    assert float(body["amount"]) == 2000
    assert body["provider_reference"] == "ATP_abc"


def test_mobile_money_unconfigured_returns_400(client, incident_id):
    resp = client.post(
        f"/api/incidents/{incident_id}/reward",
        json={"method": "MOBILE_MONEY", "amount": 1000},
    )
    assert resp.status_code == 400
    assert "PRODUCT_NAME" in resp.json()["detail"]


def test_reward_unknown_incident_returns_404(client):
    resp = client.post(
        "/api/incidents/99999/reward",
        json={"method": "AIRTIME", "amount": 1000},
    )
    assert resp.status_code == 404


def test_reward_amount_too_small_returns_400(client, incident_id):
    resp = client.post(
        f"/api/incidents/{incident_id}/reward",
        json={"method": "AIRTIME", "amount": 10},
    )
    assert resp.status_code == 400
    assert "at least" in resp.json()["detail"]


def test_reward_invalid_method_returns_422(client, incident_id):
    resp = client.post(
        f"/api/incidents/{incident_id}/reward",
        json={"method": "BITCOIN", "amount": 1000},
    )
    assert resp.status_code == 422


def test_provider_failure_records_failed_row(monkeypatch, client, incident_id):
    import app.services.rewards as rewards_svc

    monkeypatch.setattr(
        rewards_svc,
        "send_airtime",
        lambda phone, amount: {
            "ok": False,
            "provider_status": "Failed",
            "provider_reference": None,
            "message": "Invalid amount",
        },
    )

    resp = client.post(
        f"/api/incidents/{incident_id}/reward",
        json={"method": "AIRTIME", "amount": 1000},
    )
    assert resp.status_code == 502

    history = client.get(f"/api/incidents/{incident_id}/rewards").json()
    assert len(history) == 1
    assert history[0]["provider_status"] == "Failed"


def test_airtime_service_normalizes_response():
    from app.services.rewards import _airtime_entry, send_airtime

    assert _airtime_entry({"responses": [{"status": "Success", "requestId": "X"}]})["requestId"] == "X"