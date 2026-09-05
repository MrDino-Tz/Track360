WEBHOOK = "/webhooks/africastalking/sms"


def _sms(**overrides):
    payload = {
        "from": "+255712345678",
        "to": "10096",
        "text": "COMP01",
        "id": "ATXid_conv_001",
        "date": "2026-09-05 12:42:00",
    }
    payload.update(overrides)
    return payload


def _find(client, ext_id):
    for item in client.get("/api/incidents").json():
        if item["external_message_id"] == ext_id:
            return item
    return None


def test_code_only_message_does_not_create_incident(client):
    before = len(client.get("/api/incidents").json())
    resp = client.post(WEBHOOK, data=_sms(id="tw_001", text="COMP01"))
    after = len(client.get("/api/incidents").json())
    assert resp.status_code == 200
    assert resp.text == "GOOD"
    # No incident created yet — we prompted for a description instead.
    assert after == before


def test_follow_up_description_creates_incident_for_pending_equipment(client):
    # Step 1: worker sends just the code.
    client.post(WEBHOOK, data=_sms(id="tw_002a", text="COMP01", **{"from": "+25570001111"}))
    assert len(client.get("/api/incidents").json()) == 0

    # Step 2: worker describes the problem (no code). Should attach to COMP01
    # because the conversation is pending for that sender.
    client.post(
        WEBHOOK,
        data=_sms(id="tw_002b", text="air pressure dropping", **{"from": "+25570001111"}),
    )
    incident = _find(client, "tw_002b")
    assert incident is not None
    assert incident["equipment"]["code"] == "COMP01"
    assert incident["equipment"]["name"] == "Air Compressor"


def test_normal_coded_message_still_creates_incident_directly(client):
    before = len(client.get("/api/incidents").json())
    client.post(WEBHOOK, data=_sms(id="tw_003", text="M04 conveyor jammed"))
    after = len(client.get("/api/incidents").json())
    assert after == before + 1
    incident = _find(client, "tw_003")
    assert incident["equipment"]["code"] == "M04"
    assert incident["status"] == "NEW"


def test_menu_number_reply_builds_condition_description(client, monkeypatch):
    import app.services.ai as ai

    monkeypatch.setattr(ai, "_ask_groq", lambda equipment: [])
    phone = "+255722223333"
    # Step 1: code only -> prompt.
    client.post(WEBHOOK, data=_sms(id="tw_m1", text="COMP01", **{"from": phone}))
    assert len(client.get("/api/incidents").json()) == 0

    # Step 2: reply with menu option "2" (Overheating).
    client.post(WEBHOOK, data=_sms(id="tw_m2", text="2", **{"from": phone}))
    incident = _find(client, "tw_m2")
    assert incident is not None
    assert incident["equipment"]["code"] == "COMP01"
    assert incident["original_message"] == "COMP01 Overheating"
    assert incident["category"] == "OVERHEATING"


def test_menu_free_text_reply_keeps_description(client):
    phone = "+255733334444"
    client.post(WEBHOOK, data=_sms(id="tw_f1", text="GEN01", **{"from": phone}))
    assert len(client.get("/api/incidents").json()) == 0

    client.post(WEBHOOK, data=_sms(id="tw_f2", text="belt snapped", **{"from": phone}))
    incident = _find(client, "tw_f2")
    assert incident is not None
    assert incident["equipment"]["code"] == "GEN01"
    assert incident["original_message"] == "belt snapped"


def test_prompt_menu_contains_conditions():
    from app.services.outbound import send_prompt

    # Just sanity-check the menu text is built from CONDITION_MENU.
    from unittest.mock import patch

    sent = {}

    def fake_send(phone, message, settings):
        sent["message"] = message

    with patch("app.services.outbound._send", fake_send):
        send_prompt("+25570001111", "COMP01")

    msg = sent["message"]
    assert "COMP01" in msg
    for label in ("Leaking", "Overheating", "Not running", "Electrical", "Mechanical", "Other"):
        assert label in msg


def test_acknowledgement_thanks_reporter():
    from unittest.mock import patch

    from app.services.outbound import send_acknowledgement

    sent = {}

    def fake_send(phone, message, settings):
        sent["message"] = message

    with patch("app.services.outbound._send", fake_send):
        send_acknowledgement("+25570001111", "COMP01", 42)

    msg = sent["message"]
    assert "Thank you for your report" in msg
    assert "Incident #42" in msg
    assert "Maintenance has been notified" in msg


def test_ai_generates_equipment_specific_questions(monkeypatch):
    phone = "+255744445555"

    import app.services.ai as ai
    from app.database import SessionLocal
    from app.services.conversation import process_inbound

    captured = {}

    def fake_equipment_questions(equipment):
        captured["code"] = equipment.code
        return ["Low air pressure", "Overheating", "Oil leak", "Loud noise", "Not starting", "Other"]

    monkeypatch.setattr(ai, "equipment_questions", fake_equipment_questions)

    db = SessionLocal()
    try:
        result = process_inbound(db, sender=phone, text="COMP01", external_id="ai_1")
        assert result.prompted is True
        assert captured["code"] == "COMP01"

        # Follow-up with AI menu number 3 -> "Oil leak".
        result2 = process_inbound(db, sender=phone, text="3", external_id="ai_2")
        assert result2.incident is not None
        assert result2.incident.original_message == "COMP01 Oil leak"
        assert result2.incident.category == "LEAK"
    finally:
        db.close()


def test_ai_fallback_menu_uses_generic_conditions(monkeypatch):
    # If Groq is absent, equipment_questions returns CONDITION_MENU values.
    import app.services.ai as ai

    monkeypatch.setattr(ai, "_ask_groq", lambda equipment: [])

    class FakeEq:
        code = "COMP01"
        name = "Air Compressor"
        equipment_type = "Compressor"
        location = "Utilities"

    questions = ai.equipment_questions(FakeEq())
    assert questions == [
        "Leaking",
        "Overheating",
        "Not running",
        "Electrical fault",
        "Mechanical fault / noise",
        "Other",
    ]
