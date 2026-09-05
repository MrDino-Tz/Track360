from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.services.callback import parse_africastalking_payload, parse_callback_date
from app.services.outbound import send_acknowledgement
from app.services.sms_ingest import DuplicateIncident, ingest_sms

router = APIRouter()

_last_inbound: dict = {"received_at": None, "sender": None, "text": None}


def last_sms_status() -> dict:
    return dict(_last_inbound)


@router.post("/webhooks/africastalking/sms")
async def africastalking_inbound_sms(
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Response:
    payload = await parse_africastalking_payload(request)
    sender = payload.get("from") or payload.get("sender") or payload.get("phoneNumber")
    text = payload.get("text") or payload.get("message")
    recipient = payload.get("to") or payload.get("recipient")
    external_id = payload.get("id") or payload.get("messageId")

    if not sender or text is None or str(text).strip() == "":
        return Response(content="BAD", media_type="text/plain", status_code=400)

    try:
        incident = ingest_sms(
            db,
            sender=str(sender),
            text=str(text),
            recipient=str(recipient) if recipient else None,
            external_id=str(external_id) if external_id else None,
            reported_at=parse_callback_date(payload.get("date")),
        )
    except DuplicateIncident:
        return Response(content="GOOD", media_type="text/plain", status_code=200)

    _last_inbound.update(
        received_at=datetime.now(timezone.utc),
        sender=str(sender),
        text=str(text),
    )

    if get_settings().africastalking_send_ack:
        label = incident.equipment.code if incident.equipment else "Unassigned"
        background.add_task(send_acknowledgement, incident.sender_phone, label, incident.id)

    return Response(content="GOOD", media_type="text/plain", status_code=200)
