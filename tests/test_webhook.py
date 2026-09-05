WEBHOOK = "/webhooks/africastalking/sms"


def _sms(**overrides):
    payload = {
        "from": "+255712345678",
        "to": "10096",
        "text": "M04 machine stopped working",
        "id": "ATXid_demo_001",
        "date": "2026-09-05 12:42:00",
        "linkId": "SampleLinkId123",
    }
    payload.update(overrides)
    return payload


def test_webhook_receives_form_encoded_sms(client):
    response = client.post(WEBHOOK, data=_sms())
    assert response.status_code == 200
    assert response.text == "GOOD"


def test_valid_sms_creates_one_incident(client):
    before = client.get("/api/incidents").json()
    client.post(WEBHOOK, data=_sms(id="ATXid_one", text="M01 machine stopped"))
    after = client.get("/api/incidents").json()
    assert len(after) == len(before) + 1


def test_original_sms_is_preserved(client):
    text = "M04 machine stopped working"
    client.post(WEBHOOK, data=_sms(id="ATXid_preserve", text=text))
    incidents = client.get("/api/incidents").json()
    match = next(item for item in incidents if item["external_message_id"] == "ATXid_preserve")
    assert match["original_message"] == text
    assert match["channel"] == "SMS"


def test_sender_number_is_stored_and_normalized(client):
    client.post(WEBHOOK, data=_sms(id="ATXid_phone", **{"from": "0712345678", "text": "GEN01 overheating"}))
    match = next(
        item
        for item in client.get("/api/incidents").json()
        if item["external_message_id"] == "ATXid_phone"
    )
    assert match["sender_phone"] == "+255712345678"
    assert match["recipient_number"] == "10096"


def test_known_equipment_code_is_matched(client):
    client.post(WEBHOOK, data=_sms(id="ATXid_m03", text="M03 conveyor stuck"))
    match = next(
        item
        for item in client.get("/api/incidents").json()
        if item["external_message_id"] == "ATXid_m03"
    )
    assert match["equipment"]["code"] == "M03"
    assert match["equipment"]["name"] == "Packaging Machine"
    assert match["status"] == "NEW"


def test_unknown_equipment_creates_unassigned_incident(client):
    client.post(
        WEBHOOK,
        data=_sms(id="ATXid_unassigned", text="Packaging machine stopped again"),
    )
    match = next(
        item
        for item in client.get("/api/incidents").json()
        if item["external_message_id"] == "ATXid_unassigned"
    )
    assert match["equipment_id"] is None
    assert match["equipment"] is None
    assert match["status"] == "NEW"
    assert match["original_message"] == "Packaging machine stopped again"


def test_duplicate_callback_does_not_create_duplicate_incident(client):
    payload = _sms(id="ATXid_dup", text="PUMP01 leaking")
    first = client.post(WEBHOOK, data=payload)
    second = client.post(WEBHOOK, data=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    matches = [
        item
        for item in client.get("/api/incidents").json()
        if item["external_message_id"] == "ATXid_dup"
    ]
    assert len(matches) == 1


def test_missing_sender_is_rejected(client):
    response = client.post(WEBHOOK, data={"text": "hello", "to": "10096"})
    assert response.status_code == 400
    assert response.text == "BAD"
