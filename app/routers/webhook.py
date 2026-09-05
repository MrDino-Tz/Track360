from datetime import datetime, timezone
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.services.callback import parse_africastalking_payload, parse_callback_date
from app.services.conversation import pending_code, pending_questions, process_inbound
from app.services.outbound import send_acknowledgement, send_prompt
from app.services.phone import normalize_phone

logger = logging.getLogger(__name__)

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

    result = process_inbound(
        db,
        sender=str(sender),
        text=str(text),
        recipient=str(recipient) if recipient else None,
        external_id=str(external_id) if external_id else None,
        reported_at=parse_callback_date(payload.get("date")),
    )

    if result.duplicate:
        logger.info("Duplicate SMS ignored (external_id=%s)", external_id)
        return Response(content="GOOD", media_type="text/plain", status_code=200)

    _last_inbound.update(
        received_at=datetime.now(timezone.utc),
        sender=str(sender),
        text=str(text),
    )

    # Two-way: we asked for a description instead of creating an incident.
    if result.prompted:
        phone = normalize_phone(str(sender))
        code = pending_code(phone) or "device"
        questions = pending_questions(phone)
        logger.info("%s sent device code only (%r) — prompted for a description", phone, str(text))
        if get_settings().africastalking_send_ack:
            background.add_task(send_prompt, phone, code, questions)
        return Response(content="GOOD", media_type="text/plain", status_code=200)

    incident = result.incident
    eq_label = incident.equipment.code if incident.equipment else "Unassigned"
    logger.info(
        "Inbound SMS from %s -> incident #%s (equipment=%s, category=%s): %r",
        incident.sender_phone,
        incident.id,
        eq_label,
        incident.category,
        incident.original_message,
    )

    if get_settings().africastalking_send_ack:
        background.add_task(send_acknowledgement, incident.sender_phone, eq_label, incident.id)

    return Response(content="GOOD", media_type="text/plain", status_code=200)