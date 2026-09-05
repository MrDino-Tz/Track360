import logging
import threading

from sqlalchemy.orm import Session

from app.services.equipment_matcher import detect_equipment
from app.services.phone import normalize_phone
from app.services.sms_ingest import ingest_sms

logger = logging.getLogger(__name__)

# In-memory map: pending = { sender_phone: {equipment_code, questions, at} }
_pending: dict[str, dict] = {}
_lock = threading.Lock()
PENDING_TTL_SECONDS = 600  # 10 minutes

# Numbered menu sent by send_prompt; a follow-up can be the number or free text.
CONDITION_MENU = {
    "1": "Leaking",
    "2": "Overheating",
    "3": "Not running",
    "4": "Electrical fault",
    "5": "Mechanical fault / noise",
    "6": "Other",
}


def condition_for_reply(text: str, questions: list[str] | None = None) -> str | None:
    """Return the chosen label if the reply is a menu number, else None."""
    items = questions if questions else list(CONDITION_MENU.values())
    key = (text or "").strip(" .,!?;:'\"-")
    if key.isdigit():
        idx = int(key) - 1
        if 0 <= idx < len(items):
            return items[idx]
        return None
    # Allow "option 2" style replies.
    for num, label in enumerate(items, start=1):
        if key.lower() in (f"option {num}", f"opt {num}"):
            return label
    return None


class AwaitingDescription(Exception):
    """Raised when the SMS is just an equipment code; reply requesting a description."""


def classify_code_only_message(message: str, db: Session):
    """Return the equipment code if the message consists ONLY of that code.

    Examples that prompt for a description: "COMP01", " comp01 ", "COMP01."
    Anything with real problem text ("COMP01 air leak") returns None.
    """
    text = (message or "").strip().upper()
    if not text:
        return None
    equipment = detect_equipment(text, db)
    if equipment is None:
        return None
    code = equipment.code.upper()
    # The whole message (case-insensitive, surrounding punctuation ignored)
    # equals just the code -> code-only prompt.
    if text.strip(" .,!?;:'\"-") == code:
        return code
    return None


def remember_pending(
    phone: str, equipment_code: str, questions: list[str] | None = None
) -> None:
    key = normalize_phone(phone)
    if not key:
        return
    with _lock:
        _pending[key] = {
            "equipment_code": equipment_code,
            "questions": list(questions or []),
            "at": _now(),
        }


def pending_for(phone: str) -> dict | None:
    key = normalize_phone(phone)
    with _lock:
        entry = _pending.get(key)
        if not entry:
            return None
        if _now() - entry["at"] > PENDING_TTL_SECONDS:
            _pending.pop(key, None)
            return None
        return dict(entry)


def pending_code(phone: str) -> str | None:
    entry = pending_for(phone)
    return entry["equipment_code"] if entry else None


def pending_questions(phone: str) -> list[str]:
    entry = pending_for(phone)
    return list(entry.get("questions", [])) if entry else []


def clear_pending(phone: str) -> None:
    key = normalize_phone(phone)
    with _lock:
        _pending.pop(key, None)


def reset_pending() -> None:
    with _lock:
        _pending.clear()


class InboundResult:
    """Outcome of processing an inbound SMS."""

    def __init__(self, incident=None, prompted: bool = False, duplicate: bool = False):
        self.incident = incident
        self.prompted = prompted
        self.duplicate = duplicate


def process_inbound(
    db: Session,
    *,
    sender: str,
    text: str,
    recipient: str | None = None,
    external_id: str | None = None,
    reported_at=None,
) -> InboundResult:
    """Decide how to handle an inbound SMS under two-way conversation rules.

    - If this sender already has a pending equipment (we asked for a
      description), create the incident against that equipment.
    - Else if the message is just a device code, remember it as pending and
      prompt for the problem (no incident created yet).
    - Else create a normal incident.
    """
    message = (text or "").strip()
    phone = normalize_phone(sender)
    from app.services.sms_ingest import DuplicateIncident

    # Follow-up to a prompt for a description?
    pending = pending_for(phone) if phone else None
    if pending and pending["equipment_code"]:
        pending_code = pending["equipment_code"]
        questions = pending.get("questions") or []
        # Menu number chosen -> build a description like "Leaking".
        label = condition_for_reply(message, questions)
        incident_text = text
        if label is not None:
            incident_text = f"{pending_code} {label}"
        try:
            incident = ingest_sms(
                db,
                sender=sender,
                text=incident_text,
                recipient=recipient,
                external_id=external_id,
                reported_at=reported_at,
                forced_equipment_code=pending_code,
            )
        except DuplicateIncident:
            return InboundResult(duplicate=True)
        clear_pending(phone)
        return InboundResult(incident=incident)

    # Just a device code -> ask tailored questions.
    code = classify_code_only_message(message, db)
    if code:
        equipment = detect_equipment(code, db)
        from app.services.ai import equipment_questions

        questions = equipment_questions(equipment) if equipment else []
        remember_pending(phone, code, questions)
        return InboundResult(prompted=True)

    # Normal report: "<code> <problem>".
    try:
        incident = ingest_sms(
            db,
            sender=sender,
            text=text,
            recipient=recipient,
            external_id=external_id,
            reported_at=reported_at,
        )
    except DuplicateIncident:
        return InboundResult(duplicate=True)
    return InboundResult(incident=incident)


def _now() -> float:
    import time

    return time.time()