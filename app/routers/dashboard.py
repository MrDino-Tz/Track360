from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Equipment, Incident
from app.routers.webhook import last_sms_status
from app.schemas import CategoryCount, ChannelStatus, DashboardSummary, FailingEquipment, IncidentOut

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

OPEN_STATUSES = ("NEW", "ACKNOWLEDGED", "UNDER_REPAIR")


@router.get("/channel", response_model=ChannelStatus)
def channel_status() -> ChannelStatus:
    return ChannelStatus(live=True, **last_sms_status())


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_equipment = db.query(func.count(Equipment.id)).scalar() or 0
    new_incidents = db.query(func.count(Incident.id)).filter(Incident.status == "NEW").scalar() or 0
    open_incidents = (
        db.query(func.count(Incident.id)).filter(Incident.status.in_(OPEN_STATUSES)).scalar() or 0
    )
    under_repair = (
        db.query(func.count(Incident.id)).filter(Incident.status == "UNDER_REPAIR").scalar() or 0
    )
    resolved_today = (
        db.query(func.count(Incident.id))
        .filter(Incident.status == "RESOLVED", Incident.resolved_at >= day_start)
        .scalar()
        or 0
    )
    incidents_this_month = (
        db.query(func.count(Incident.id)).filter(Incident.reported_at >= month_start).scalar() or 0
    )
    maintenance_cost = db.query(func.coalesce(func.sum(Incident.repair_cost), 0)).scalar() or 0
    total_downtime = db.query(func.coalesce(func.sum(Incident.downtime_minutes), 0)).scalar() or 0

    failing_rows = (
        db.query(
            Equipment.id,
            Equipment.code,
            Equipment.name,
            func.count(Incident.id).label("incident_count"),
            func.coalesce(func.sum(Incident.repair_cost), 0).label("total_repair_cost"),
            func.coalesce(func.sum(Incident.downtime_minutes), 0).label("total_downtime_minutes"),
        )
        .join(Incident, Incident.equipment_id == Equipment.id)
        .group_by(Equipment.id, Equipment.code, Equipment.name)
        .order_by(func.count(Incident.id).desc())
        .all()
    )
    failing = [
        FailingEquipment(
            equipment_id=row.id,
            code=row.code,
            name=row.name,
            incident_count=int(row.incident_count),
            total_repair_cost=Decimal(str(row.total_repair_cost)),
            total_downtime_minutes=int(row.total_downtime_minutes),
        )
        for row in failing_rows
    ]

    category_rows = (
        db.query(Incident.category, func.count(Incident.id))
        .filter(Incident.category.isnot(None))
        .group_by(Incident.category)
        .order_by(func.count(Incident.id).desc())
        .all()
    )
    recurring = [CategoryCount(category=row[0], count=int(row[1])) for row in category_rows]

    insights: list[str] = []
    window_start = now - timedelta(days=30)
    recent_failing = (
        db.query(Equipment.code, func.count(Incident.id))
        .join(Incident, Incident.equipment_id == Equipment.id)
        .filter(Incident.reported_at >= window_start)
        .group_by(Equipment.code)
        .having(func.count(Incident.id) >= 3)
        .order_by(func.count(Incident.id).desc())
        .all()
    )
    for code, count in recent_failing:
        insights.append(f"{code} has recorded {int(count)} incidents in the last 30 days.")

    return DashboardSummary(
        total_equipment=int(total_equipment),
        new_incidents=int(new_incidents),
        open_incidents=int(open_incidents),
        under_repair=int(under_repair),
        resolved_today=int(resolved_today),
        incidents_this_month=int(incidents_this_month),
        maintenance_cost=Decimal(str(maintenance_cost)),
        total_downtime_minutes=int(total_downtime),
        insights=insights,
        failing_equipment=failing,
        recurring_categories=recurring,
    )


@router.get("/recent-incidents", response_model=list[IncidentOut])
def recent_incidents(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)) -> list[Incident]:
    return (
        db.query(Incident)
        .options(joinedload(Incident.equipment))
        .order_by(Incident.reported_at.desc())
        .limit(limit)
        .all()
    )
