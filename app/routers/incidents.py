from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Equipment, Incident, utcnow
from app.schemas import IncidentOut, IncidentUpdate

router = APIRouter(prefix="/api/incidents", tags=["incidents"])

ALLOWED_STATUSES = {"NEW", "ACKNOWLEDGED", "UNDER_REPAIR", "RESOLVED"}
ALLOWED_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
OPEN_STATUSES = {"NEW", "ACKNOWLEDGED", "UNDER_REPAIR"}


@router.get("", response_model=list[IncidentOut])
def list_incidents(
    status: str | None = Query(default=None),
    equipment_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Incident]:
    query = db.query(Incident).options(joinedload(Incident.equipment))
    if status:
        query = query.filter(Incident.status == status.upper())
    if equipment_id is not None:
        query = query.filter(Incident.equipment_id == equipment_id)
    return query.order_by(Incident.reported_at.desc()).all()


@router.get("/{incident_id}", response_model=IncidentOut)
def get_incident(incident_id: int, db: Session = Depends(get_db)) -> Incident:
    incident = (
        db.query(Incident)
        .options(joinedload(Incident.equipment))
        .filter(Incident.id == incident_id)
        .one_or_none()
    )
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.patch("/{incident_id}", response_model=IncidentOut)
def update_incident(incident_id: int, payload: IncidentUpdate, db: Session = Depends(get_db)) -> Incident:
    incident = (
        db.query(Incident)
        .options(joinedload(Incident.equipment))
        .filter(Incident.id == incident_id)
        .one_or_none()
    )
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    data = payload.model_dump(exclude_unset=True)

    if "status" in data and data["status"]:
        status = data["status"].upper()
        if status not in ALLOWED_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status")
        incident.status = status
        now = utcnow()
        if status in {"ACKNOWLEDGED", "UNDER_REPAIR", "RESOLVED"} and incident.acknowledged_at is None:
            incident.acknowledged_at = now
        if status == "RESOLVED" and incident.resolved_at is None:
            incident.resolved_at = now
        if status != "RESOLVED":
            incident.resolved_at = None

    if "severity" in data and data["severity"]:
        severity = data["severity"].upper()
        if severity not in ALLOWED_SEVERITIES:
            raise HTTPException(status_code=400, detail="Invalid severity")
        incident.severity = severity

    if "category" in data:
        incident.category = data["category"].upper() if data["category"] else None

    if "repair_notes" in data:
        incident.repair_notes = data["repair_notes"]

    if "repair_cost" in data:
        incident.repair_cost = data["repair_cost"]

    if "downtime_minutes" in data:
        incident.downtime_minutes = data["downtime_minutes"]

    if "equipment_id" in data:
        equipment_id = data["equipment_id"]
        if equipment_id is not None and db.get(Equipment, equipment_id) is None:
            raise HTTPException(status_code=400, detail="Equipment not found")
        incident.equipment_id = equipment_id

    db.commit()
    _sync_equipment_status(db, incident.equipment_id)
    db.refresh(incident)
    return incident


def _sync_equipment_status(db: Session, equipment_id: int | None) -> None:
    if not equipment_id:
        return
    equipment = db.get(Equipment, equipment_id)
    if not equipment:
        return
    open_count = (
        db.query(Incident)
        .filter(Incident.equipment_id == equipment_id, Incident.status.in_(OPEN_STATUSES))
        .count()
    )
    under_repair = (
        db.query(Incident)
        .filter(Incident.equipment_id == equipment_id, Incident.status == "UNDER_REPAIR")
        .count()
    )
    if under_repair:
        equipment.status = "MAINTENANCE"
    elif open_count:
        equipment.status = "DEGRADED"
    else:
        equipment.status = "OPERATIONAL"
    db.commit()
