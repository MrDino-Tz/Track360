from datetime import datetime, timezone
import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.services.africastalking import get_sms, _SDK_AVAILABLE
from app.services.conversation import process_inbound
from app.services.outbound import send_acknowledgement, send_prompt
from app.routers.webhook import _last_inbound

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/sms/sync")
def sync_inbox(background: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    """Pull all received SMS from the Africa's Talking inbox into Thibitisha.

    Two-way: a lone device code prompts for a description; a coded problem
    creates an incident. Each message's `linkId` dedupes on re-sync.
    """
    stats = {"total": 0, "imported": 0, "prompted": 0, "duplicates": 0, "errors": 0, "latest": None}

    sms = get_sms()
    if not _SDK_AVAILABLE or sms is None:
        return {"error": "africastalking SDK not available", **stats}

    try:
        response = sms.fetch_messages()
    except Exception as exc:
        logger.error("Failed to fetch SMS inbox from Africa's Talking: %s", exc)
        return {"error": str(exc), **stats}

    messages = response.get("SMSMessageData", {}).get("Messages", [])
    stats["total"] = len(messages)

    for msg in messages:
        message_id = str(msg.get("linkId") or msg.get("id") or "")
        text = msg.get("text")
        sender = msg.get("from")
        if not sender or not text or str(text).strip() == "":
            stats["errors"] += 1
            continue

        result = process_inbound(
            db,
            sender=str(sender),
            text=str(text),
            recipient=str(msg.get("to")) if msg.get("to") else None,
            external_id=message_id or None,
            reported_at=_parse_date(msg.get("date")),
        )

        if result.duplicate:
            stats["duplicates"] += 1
            continue

        if result.prompted:
            stats["prompted"] += 1
            stats["latest"] = {"from": sender, "text": str(text)}
            _last_inbound.update(
                received_at=datetime.now(timezone.utc),
                sender=str(sender),
                text=str(text),
            )
            logger.info(
                "Synced code-only SMS from %s (%r) — prompted for description",
                sender,
                str(text),
            )
            if get_settings().africastalking_send_ack:
                from app.services.conversation import pending_code, pending_questions
                from app.services.phone import normalize_phone

                phone = normalize_phone(str(sender))
                code = pending_code(phone) or "device"
                questions = pending_questions(phone)
                background.add_task(send_prompt, phone, code, questions)
            continue

        stats["imported"] += 1
        stats["latest"] = {"from": sender, "text": str(text)}
        _last_inbound.update(
            received_at=datetime.now(timezone.utc),
            sender=str(sender),
            text=str(text),
        )

        incident = result.incident
        eq_label = incident.equipment.code if incident.equipment else "Unassigned"
        logger.info(
            "Synced SMS from %s -> incident #%s (equipment=%s, category=%s): %r",
            incident.sender_phone,
            incident.id,
            eq_label,
            incident.category,
            incident.original_message,
        )
        if get_settings().africastalking_send_ack:
            background.add_task(send_acknowledgement, incident.sender_phone, eq_label, incident.id)

    return stats


def _parse_date(value):
    from app.services.callback import parse_callback_date

    return parse_callback_date(value)