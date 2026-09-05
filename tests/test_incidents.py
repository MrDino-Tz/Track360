def _create_sms(client, external_id: str, text: str) -> dict:
    client.post(
        "/webhooks/africastalking/sms",
        data={
            "from": "+255754000111",
            "to": "20880",
            "text": text,
            "id": external_id,
            "date": "2026-09-05 10:00:00",
        },
    )
    return next(
        item
        for item in client.get("/api/incidents").json()
        if item["external_message_id"] == external_id
    )


def test_incident_can_be_updated(client):
    incident = _create_sms(client, "ATXid_update", "M04 machine stopped working")
    equipment = next(item for item in client.get("/api/equipment").json() if item["code"] == "M04")
    response = client.patch(
        f"/api/incidents/{incident['id']}",
        json={
            "severity": "HIGH",
            "status": "UNDER_REPAIR",
            "category": "STOPPAGE",
            "equipment_id": equipment["id"],
            "repair_notes": "Motor being inspected",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["severity"] == "HIGH"
    assert body["status"] == "UNDER_REPAIR"
    assert body["category"] == "STOPPAGE"
    assert body["acknowledged_at"] is not None


def test_resolved_incident_updates_equipment_history(client):
    incident = _create_sms(client, "ATXid_history", "M04 machine stopped working")
    equipment = next(item for item in client.get("/api/equipment").json() if item["code"] == "M04")
    before = client.get(f"/api/equipment/{equipment['id']}").json()
    client.patch(
        f"/api/incidents/{incident['id']}",
        json={
            "status": "RESOLVED",
            "repair_notes": "Motor replaced",
            "repair_cost": 300000,
            "downtime_minutes": 120,
        },
    )
    after = client.get(f"/api/equipment/{equipment['id']}").json()
    history = client.get(f"/api/equipment/{equipment['id']}/incidents").json()
    assert after["incident_count"] == before["incident_count"]
    assert after["open_count"] == before["open_count"] - 1
    assert float(after["total_repair_cost"]) == float(before["total_repair_cost"]) + 300000
    assert after["total_downtime_minutes"] == before["total_downtime_minutes"] + 120
    match = next(row for row in history if row["id"] == incident["id"])
    assert match["status"] == "RESOLVED"
    assert match["repair_notes"] == "Motor replaced"
    assert float(match["repair_cost"]) == 300000
    assert match["downtime_minutes"] == 120
