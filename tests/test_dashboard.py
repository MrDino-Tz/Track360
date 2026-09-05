from datetime import datetime, timezone

from app.database import SessionLocal
from app.models import Incident


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dashboard_summary_is_calculated_from_database(client):
    db = SessionLocal()
    try:
        equipment = {item["code"]: item["id"] for item in client.get("/api/equipment").json()}
        now = datetime.now(timezone.utc)
        rows = [
            Incident(
                equipment_id=equipment["M04"],
                sender_phone="+255700000001",
                original_message="M04 down",
                channel="SMS",
                status="NEW",
                severity="MEDIUM",
                reported_at=now,
            ),
            Incident(
                equipment_id=equipment["GEN01"],
                sender_phone="+255700000002",
                original_message="GEN01 noise",
                channel="SMS",
                status="NEW",
                severity="MEDIUM",
                reported_at=now,
            ),
            Incident(
                equipment_id=equipment["M04"],
                sender_phone="+255700000003",
                original_message="M04 belt",
                channel="SMS",
                status="UNDER_REPAIR",
                severity="HIGH",
                reported_at=now,
                repair_cost=100000,
                downtime_minutes=30,
            ),
            Incident(
                equipment_id=equipment["M01"],
                sender_phone="+255700000004",
                original_message="M01 blade",
                channel="SMS",
                status="RESOLVED",
                severity="LOW",
                reported_at=now,
                resolved_at=now,
                repair_cost=200000,
                downtime_minutes=45,
            ),
        ]
        db.add_all(rows)
        db.commit()
    finally:
        db.close()

    summary = client.get("/api/dashboard/summary").json()
    assert summary["total_equipment"] == 10
    assert summary["new_incidents"] == 2
    assert summary["under_repair"] == 1
    assert summary["open_incidents"] == 3
    assert summary["resolved_today"] == 1
    assert float(summary["maintenance_cost"]) == 300000
    assert summary["total_downtime_minutes"] == 75
    assert summary["incidents_this_month"] == 4
    assert any(row["code"] == "M04" for row in summary["failing_equipment"])


def test_recent_incidents_endpoint(client):
    client.post(
        "/webhooks/africastalking/sms",
        data={
            "from": "+255712345678",
            "to": "10096",
            "text": "M04 machine stopped working",
            "id": "ATXid_feed",
            "date": "2026-09-05 12:42:00",
        },
    )
    feed = client.get("/api/dashboard/recent-incidents").json()
    assert len(feed) == 1
    assert feed[0]["original_message"] == "M04 machine stopped working"
    assert feed[0]["sender_phone"] == "+255712345678"
    assert feed[0]["channel"] == "SMS"
    assert feed[0]["equipment"]["code"] == "M04"
