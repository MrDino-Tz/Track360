import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


def send_acknowledgement(phone: str, equipment_label: str, incident_id: int) -> None:
    settings = get_settings()
    if not settings.africastalking_send_ack:
        return
    if not settings.africastalking_username or not settings.africastalking_api_key:
        logger.warning("Acknowledgement SMS skipped: Africa's Talking credentials are not set")
        return

    base = (
        "https://api.sandbox.africastalking.com/version1/messaging"
        if settings.africastalking_sandbox
        else "https://api.africastalking.com/version1/messaging"
    )
    message = (
        f"PlantDesk: incident #{incident_id} logged"
        + (f" for {equipment_label}" if equipment_label else "")
        + ". Maintenance has been notified."
    )
    data = {
        "username": settings.africastalking_username,
        "to": phone,
        "message": message,
    }
    if settings.africastalking_sender_id:
        data["from"] = settings.africastalking_sender_id

    headers = {
        "Accept": "application/json",
        "apiKey": settings.africastalking_api_key,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    try:
        response = httpx.post(base, data=data, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception:
        logger.exception("Failed to send acknowledgement SMS to %s", phone)
