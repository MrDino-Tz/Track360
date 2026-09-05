"""Reward endpoints — send and list motivational payouts for an incident."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Incident, Reward
from app.schemas import RewardCreate, RewardOut
from app.services import rewards as rewards_svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/incidents", tags=["rewards"])


@router.post("/{incident_id}/reward", response_model=RewardOut)
def send_reward(
    incident_id: int, payload: RewardCreate, db: Session = Depends(get_db)
) -> Reward:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    method = payload.method.upper()
    amount = payload.amount or get_settings().reward_default_amount
    if amount < rewards_svc.MIN_AMOUNT:
        raise HTTPException(
            status_code=400,
            detail=f"amount must be at least {rewards_svc.MIN_AMOUNT}",
        )
    if (
        method == "MOBILE_MONEY"
        and not get_settings().africastalking_payments_product_name
    ):
        raise HTTPException(
            status_code=400,
            detail="AFRICASTALKING_PAYMENTS_PRODUCT_NAME is not configured for mobile-money rewards",
        )

    if method == "AIRTIME":
        result = rewards_svc.send_airtime(incident.sender_phone, amount)
    else:
        result = rewards_svc.send_mobile_money(incident.sender_phone, amount)

    reward = Reward(
        incident_id=incident.id,
        sender_phone=incident.sender_phone,
        method=method,
        currency=get_settings().reward_currency,
        amount=amount,
        provider_status=result["provider_status"],
        provider_reference=result.get("provider_reference"),
        message=result.get("message"),
    )
    db.add(reward)
    db.commit()
    db.refresh(reward)

    if not result["ok"]:
        logger.warning(
            "Reward %s to %s for incident #%s failed: %s",
            method,
            incident.sender_phone,
            incident.id,
            result.get("message"),
        )
        raise HTTPException(
            status_code=502,
            detail=f"Reward failed (status={result['provider_status']}): {result.get('message')}",
        )

    return reward


@router.get("/{incident_id}/rewards", response_model=list[RewardOut])
def list_rewards(incident_id: int, db: Session = Depends(get_db)) -> list[Reward]:
    if not db.get(Incident, incident_id):
        raise HTTPException(status_code=404, detail="Incident not found")
    return (
        db.query(Reward)
        .filter(Reward.incident_id == incident_id)
        .order_by(Reward.created_at.desc())
        .all()
    )