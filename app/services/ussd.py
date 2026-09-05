"""USSD session handler for Thibitisha equipment incident reports.

Africa's Talking sends the accumulated user input as a ``*``-delimited
string (e.g. ``"COMP01"``, ``"COMP01*2"``).  We reply with a ``CON``
(continue) or ``END`` (terminal) prefix.  The response body is
``text/plain``.

Menu flow
---------
Step 0 – Reporter types the equipment code (e.g. ``COMP01``)
Step 1 – Reporter picks a condition number from CONDITION_MENU
Step 2 – Incident created → END
"""

import logging

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Equipment, Incident, utcnow
from app.services.classifier import classify_message
from app.services.conversation import CONDITION_MENU

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _find_equipment_by_text(db: Session, raw: str) -> Equipment | None:
    """Match equipment by its code or by its name.

    Names are matched flexibly:
    - exact code (case-insensitive)
    - name with normalized internal whitespace ("Air Compressor", " air  compressor ")
    - name with all whitespace removed ("aircompressor") — common when USSD
      keypads drop spaces
    """
    text = (raw or "").strip()
    if not text:
        return None

    # Exact code match first.
    code = text.upper()
    eq = db.query(Equipment).filter(Equipment.code == code).one_or_none()
    if eq:
        return eq

    # Name match: collapse internal whitespace ...
    normalized = " ".join(text.split()).lower()
    lower_name = func.lower(Equipment.name)
    found = (
        db.query(Equipment)
        .filter(lower_name == normalized)
        .one_or_none()
    )
    if found:
        return found

    # ... or drop whitespace entirely.
    squashed = normalized.replace(" ", "")
    if squashed:
        found = (
            db.query(Equipment)
            .filter(func.replace(lower_name, " ", "") == squashed)
            .one_or_none()
        )
        if found:
            return found

    # Partial/unusual names — not a good idea to fuzzy match here; return None.
    return None


def _condition_menu() -> str:
    lines = ["CON Select condition:", ""]
    for num, label in CONDITION_MENU.items():
        lines.append(f"{num}. {label}")
    return "\n".join(lines)


def _create_incident(
    db: Session,
    *,
    equipment: Equipment,
    condition_label: str,
    phone_number: str,
    session_id: str,
) -> Incident:
    original_message = f"{equipment.code} {condition_label}"
    incident = Incident(
        equipment_id=equipment.id,
        sender_phone=phone_number,
        recipient_number=None,
        original_message=original_message,
        channel="USSD",
        category=classify_message(original_message),
        severity="MEDIUM",
        status="NEW",
        reported_at=utcnow(),
        external_message_id=f"ussd:{session_id}",
    )
    db.add(incident)
    try:
        db.commit()
    except IntegrityError:
        # Same USSD session resubmitted — return existing incident.
        db.rollback()
        existing = (
            db.query(Incident)
            .filter(Incident.external_message_id == f"ussd:{session_id}")
            .one_or_none()
        )
        if existing:
            if existing.equipment_id:
                existing.equipment = db.get(Equipment, existing.equipment_id)
            return existing
        raise
    db.refresh(incident)
    incident.equipment = db.get(Equipment, incident.equipment_id)
    return incident


# ── Public entry point ───────────────────────────────────────────────────────

def handle_ussd(
    db: Session,
    *,
    session_id: str,
    phone_number: str,
    service_code: str,
    text: str,
) -> tuple[str, str]:
    """Process a single USSD request.  Returns ``(response_body, hop_metadata)``."""

    parts = [p for p in (text or "").split("*") if p]
    parts = [p.strip() for p in parts if p.strip()]

    # ── Step 0: no input yet → ask for equipment code or name ────────────
    if len(parts) == 0:
        return "CON Thibitisha Equipment Report\n\nEnter equipment code or name:", "codeEntry"

    # ── Step 0b: equipment code or name given → show condition menu ──────
    if len(parts) == 1:
        equipment = _find_equipment_by_text(db, parts[0])
        if equipment is None:
            return "END Unknown equipment. Try again", "invalid"
        return _condition_menu(), f"equip:{equipment.code}"

    # ── Step 1: code/name*condition → create incident ─────────────────────
    if len(parts) == 2:
        equipment = _find_equipment_by_text(db, parts[0])
        if equipment is None:
            return "END Unknown equipment.", "invalid"

        cond_label = CONDITION_MENU.get(parts[1].strip(), "").strip()
        if not cond_label:
            return "END Invalid condition.", "invalid"

        incident = _create_incident(
            db,
            equipment=equipment,
            condition_label=cond_label,
            phone_number=phone_number,
            session_id=session_id,
        )
        return (
            f"END Thank you for your report.\n"
            f"Incident #{incident.id} logged for "
            f"{equipment.name} ({equipment.code}).\nCondition: {cond_label}.",
            "incidentCreated",
        )

    return "END Invalid selection.", "invalid"