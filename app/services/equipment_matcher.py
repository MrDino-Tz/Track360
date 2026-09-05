import re

from sqlalchemy.orm import Session

from app.models import Equipment


def detect_equipment(message: str, db: Session) -> Equipment | None:
    if not message:
        return None
    equipment = db.query(Equipment).all()
    if not equipment:
        return None
    text = message.upper()
    ranked = sorted(equipment, key=lambda item: len(item.code), reverse=True)
    for item in ranked:
        pattern = r"(?<![A-Z0-9])" + re.escape(item.code.upper()) + r"(?![A-Z0-9])"
        if re.search(pattern, text):
            return item
    return None
