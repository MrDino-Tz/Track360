from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Equipment, Incident, utcnow
from app.services.classifier import classify_message
from app.services.equipment_matcher import detect_equipment
from app.services.phone import normalize_phone


class DuplicateIncident(Exception):
    def __init__(self, incident: Incident):
        self.incident = incident


def ingest_sms(
    db: Session,
    *,
    sender: str,
    text: str,
    recipient: str | None = None,
    external_id: str | None = None,
    reported_at=None,
) -> Incident:
    sender_phone = normalize_phone(sender)
    message = text.strip()
    external_message_id = (external_id or "").strip() or None

    if external_message_id:
        existing = (
            db.query(Incident)
            .filter(Incident.external_message_id == external_message_id)
            .one_or_none()
        )
        if existing:
            raise DuplicateIncident(existing)

    equipment = detect_equipment(message, db)
    incident = Incident(
        equipment_id=equipment.id if equipment else None,
        sender_phone=sender_phone,
        recipient_number=recipient or None,
        original_message=text if text is not None else "",
        channel="SMS",
        category=classify_message(message),
        severity="MEDIUM",
        status="NEW",
        reported_at=reported_at or utcnow(),
        external_message_id=external_message_id,
    )
    db.add(incident)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if external_message_id:
            existing = (
                db.query(Incident)
                .filter(Incident.external_message_id == external_message_id)
                .one_or_none()
            )
            if existing:
                raise DuplicateIncident(existing)
        raise
    db.refresh(incident)
    if incident.equipment_id:
        incident.equipment = db.get(Equipment, incident.equipment_id)
    return incident
