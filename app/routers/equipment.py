from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Equipment, Incident
from app.schemas import EquipmentCreate, EquipmentHistoryOut, EquipmentOut, IncidentOut

router = APIRouter(prefix="/api/equipment", tags=["equipment"])

OPEN_STATUSES = ("NEW", "ACKNOWLEDGED", "UNDER_REPAIR")


@router.get("", response_model=list[EquipmentHistoryOut])
def list_equipment(db: Session = Depends(get_db)) -> list[EquipmentHistoryOut]:
    equipment = db.query(Equipment).order_by(Equipment.code.asc()).all()
    return [_with_stats(db, item) for item in equipment]


@router.post("", response_model=EquipmentOut, status_code=201)
def create_equipment(payload: EquipmentCreate, db: Session = Depends(get_db)) -> Equipment:
    existing = db.query(Equipment).filter(Equipment.code == payload.code.upper().strip()).one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Equipment code already exists")
    item = Equipment(
        code=payload.code.upper().strip(),
        name=payload.name.strip(),
        equipment_type=payload.equipment_type.strip(),
        location=payload.location.strip(),
        status=payload.status,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{equipment_id}", response_model=EquipmentHistoryOut)
def get_equipment(equipment_id: int, db: Session = Depends(get_db)) -> EquipmentHistoryOut:
    item = db.get(Equipment, equipment_id)
    if not item:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return _with_stats(db, item)


@router.get("/{equipment_id}/incidents", response_model=list[IncidentOut])
def equipment_incidents(equipment_id: int, db: Session = Depends(get_db)) -> list[Incident]:
    item = db.get(Equipment, equipment_id)
    if not item:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return (
        db.query(Incident)
        .filter(Incident.equipment_id == equipment_id)
        .order_by(Incident.reported_at.desc())
        .all()
    )


def _with_stats(db: Session, item: Equipment) -> EquipmentHistoryOut:
    incident_count = db.query(func.count(Incident.id)).filter(Incident.equipment_id == item.id).scalar() or 0
    open_count = (
        db.query(func.count(Incident.id))
        .filter(Incident.equipment_id == item.id, Incident.status.in_(OPEN_STATUSES))
        .scalar()
        or 0
    )
    cost = (
        db.query(func.coalesce(func.sum(Incident.repair_cost), 0))
        .filter(Incident.equipment_id == item.id)
        .scalar()
        or 0
    )
    downtime = (
        db.query(func.coalesce(func.sum(Incident.downtime_minutes), 0))
        .filter(Incident.equipment_id == item.id)
        .scalar()
        or 0
    )
    return EquipmentHistoryOut(
        id=item.id,
        code=item.code,
        name=item.name,
        equipment_type=item.equipment_type,
        location=item.location,
        status=item.status,
        created_at=item.created_at,
        incident_count=int(incident_count),
        open_count=int(open_count),
        total_repair_cost=Decimal(str(cost)),
        total_downtime_minutes=int(downtime),
    )
