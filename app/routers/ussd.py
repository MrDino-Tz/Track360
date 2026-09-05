import logging

from fastapi import APIRouter, Depends, Form
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.ussd import handle_ussd

logger = logging.getLogger(__name__)

router = APIRouter()


def _respond(
    session_id: str,
    service_code: str,
    phone: str,
    text: str,
    db: Session,
):
    body, hop = handle_ussd(
        db,
        session_id=session_id,
        phone_number=phone,
        service_code=service_code,
        text=text,
    )
    headers = {}
    if hop:
        headers["at-ussd-hop-metadata"] = hop
    logger.info(
        "USSD session=%s phone=%s code=%s text=%r -> hop=%s",
        session_id,
        phone,
        service_code,
        text,
        hop,
    )
    return PlainTextResponse(body, status_code=200, headers=headers)


@router.post("/webhooks/africastalking/ussd")
async def africastalking_ussd(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(""),
    db: Session = Depends(get_db),
):
    return _respond(sessionId, serviceCode, phoneNumber, text, db)


# Alias so the Africa's Talking dashboard callback (often configured as
# https://<host>/ussd) works without changes.
@router.post("/ussd")
async def ussd_shortcut(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(""),
    db: Session = Depends(get_db),
):
    return _respond(sessionId, serviceCode, phoneNumber, text, db)