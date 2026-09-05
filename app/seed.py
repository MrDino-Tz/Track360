from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Equipment, Incident


ASSETS = [
    {"code": "M01", "name": "Cutting Machine", "equipment_type": "Cutter", "location": "Production Line A"},
    {"code": "M02", "name": "Mixing Machine", "equipment_type": "Mixer", "location": "Mixing Bay"},
    {"code": "M03", "name": "Packaging Machine", "equipment_type": "Packaging", "location": "Pack Line"},
    {"code": "M04", "name": "Conveyor", "equipment_type": "Conveyor", "location": "Production Line A"},
    {"code": "GEN01", "name": "Generator", "equipment_type": "Power", "location": "Utilities"},
    {"code": "PUMP01", "name": "Water Pump", "equipment_type": "Pump", "location": "Utilities"},
    {"code": "COMP01", "name": "Air Compressor", "equipment_type": "Compressor", "location": "Utilities"},
    {"code": "COOL01", "name": "Cooling System", "equipment_type": "Cooling", "location": "Process Hall"},
    {"code": "FILL01", "name": "Filling Machine", "equipment_type": "Filler", "location": "Pack Line"},
    {"code": "SEAL01", "name": "Sealing Machine", "equipment_type": "Sealer", "location": "Pack Line"},
]


def seed_equipment(db: Session) -> dict[str, Equipment]:
    assets = [Equipment(**row) for row in ASSETS]
    db.add_all(assets)
    db.flush()
    return {item.code: item for item in assets}


def seed_demo_incidents(db: Session, by_code: dict[str, Equipment]) -> None:
    now = datetime.now(timezone.utc)

    def at(days: int = 0, hours: int = 0) -> datetime:
        return now - timedelta(days=days, hours=hours)

    rows = [
        Incident(
            equipment_id=by_code["FILL01"].id,
            sender_phone="+255754221001",
            recipient_number="20880",
            original_message="FILL01 filling nozzle blocked",
            channel="SMS",
            category="STOPPAGE",
            severity="HIGH",
            status="NEW",
            reported_at=at(hours=1),
            external_message_id="seed-fill01-new",
        ),
        Incident(
            equipment_id=by_code["COMP01"].id,
            sender_phone="+255765330214",
            recipient_number="20880",
            original_message="COMP01 pressure drop on line 2",
            channel="SMS",
            category="MECHANICAL",
            severity="MEDIUM",
            status="NEW",
            reported_at=at(hours=3),
            external_message_id="seed-comp01-new",
        ),
        Incident(
            equipment_id=by_code["M04"].id,
            sender_phone="+255712889441",
            recipient_number="20880",
            original_message="M04 sensor fault at packing transfer",
            channel="SMS",
            category="ELECTRICAL",
            severity="MEDIUM",
            status="ACKNOWLEDGED",
            reported_at=at(days=1, hours=4),
            acknowledged_at=at(days=1, hours=3),
            external_message_id="seed-m04-ack",
        ),
        Incident(
            equipment_id=by_code["M04"].id,
            sender_phone="+255754221001",
            recipient_number="20880",
            original_message="M04 conveyor jammed again",
            channel="SMS",
            category="STOPPAGE",
            severity="HIGH",
            status="UNDER_REPAIR",
            reported_at=at(days=8),
            acknowledged_at=at(days=7, hours=22),
            repair_notes="Belt inspection in progress",
            external_message_id="seed-m04-repair",
        ),
        Incident(
            equipment_id=by_code["M04"].id,
            sender_phone="+255765330214",
            recipient_number="20880",
            original_message="M04 belt slip near cutter",
            channel="SMS",
            category="MECHANICAL",
            severity="MEDIUM",
            status="RESOLVED",
            reported_at=at(days=16),
            acknowledged_at=at(days=16, hours=-1),
            resolved_at=at(days=15),
            repair_notes="Belt tensioned and rollers cleaned",
            repair_cost=Decimal("450000.00"),
            downtime_minutes=180,
            external_message_id="seed-m04-resolved-belt",
        ),
        Incident(
            equipment_id=by_code["M04"].id,
            sender_phone="+255712889441",
            recipient_number="20880",
            original_message="M04 motor overheating",
            channel="SMS",
            category="OVERHEATING",
            severity="HIGH",
            status="RESOLVED",
            reported_at=at(days=24),
            acknowledged_at=at(days=24, hours=-1),
            resolved_at=at(days=23),
            repair_notes="Motor cleaned, cooling fan replaced",
            repair_cost=Decimal("620000.00"),
            downtime_minutes=240,
            external_message_id="seed-m04-resolved-motor",
        ),
        Incident(
            equipment_id=by_code["GEN01"].id,
            sender_phone="+255754221001",
            recipient_number="20880",
            original_message="GEN01 generator overheating",
            channel="SMS",
            category="OVERHEATING",
            severity="CRITICAL",
            status="RESOLVED",
            reported_at=at(days=4),
            acknowledged_at=at(days=4, hours=-1),
            resolved_at=at(hours=5),
            repair_notes="Radiator flushed and coolant topped up",
            repair_cost=Decimal("380000.00"),
            downtime_minutes=90,
            external_message_id="seed-gen01-resolved",
        ),
        Incident(
            equipment_id=by_code["M01"].id,
            sender_phone="+255765330214",
            recipient_number="20880",
            original_message="M01 cutting blade offset",
            channel="SMS",
            category="MECHANICAL",
            severity="MEDIUM",
            status="RESOLVED",
            reported_at=at(days=12),
            acknowledged_at=at(days=12, hours=-1),
            resolved_at=at(days=11),
            repair_notes="Blade realigned",
            repair_cost=Decimal("150000.00"),
            downtime_minutes=75,
            external_message_id="seed-m01-resolved",
        ),
        Incident(
            equipment_id=by_code["M03"].id,
            sender_phone="+255712889441",
            recipient_number="20880",
            original_message="M03 packaging machine stuck",
            channel="SMS",
            category="STOPPAGE",
            severity="HIGH",
            status="RESOLVED",
            reported_at=at(days=21),
            acknowledged_at=at(days=21, hours=-1),
            resolved_at=at(days=20),
            repair_notes="Film roll replaced",
            repair_cost=Decimal("95000.00"),
            downtime_minutes=45,
            external_message_id="seed-m03-resolved",
        ),
        Incident(
            equipment_id=by_code["PUMP01"].id,
            sender_phone="+255754221001",
            recipient_number="20880",
            original_message="PUMP01 leaking at seal",
            channel="SMS",
            category="LEAK",
            severity="MEDIUM",
            status="RESOLVED",
            reported_at=at(days=40),
            acknowledged_at=at(days=40, hours=-1),
            resolved_at=at(days=39),
            repair_notes="Mechanical seal replaced",
            repair_cost=Decimal("275000.00"),
            downtime_minutes=160,
            external_message_id="seed-pump01-resolved",
        ),
        Incident(
            equipment_id=by_code["SEAL01"].id,
            sender_phone="+255765330214",
            recipient_number="20880",
            original_message="SEAL01 heat bar not reaching temperature",
            channel="SMS",
            category="ELECTRICAL",
            severity="MEDIUM",
            status="UNDER_REPAIR",
            reported_at=at(days=2),
            acknowledged_at=at(days=2, hours=-1),
            repair_notes="Heating element on order",
            external_message_id="seed-seal01-repair",
        ),
        Incident(
            equipment_id=by_code["COOL01"].id,
            sender_phone="+255712889441",
            recipient_number="20880",
            original_message="COOL01 temperature climbing on line B",
            channel="SMS",
            category="OVERHEATING",
            severity="HIGH",
            status="RESOLVED",
            reported_at=at(days=33),
            acknowledged_at=at(days=33, hours=-1),
            resolved_at=at(days=32),
            repair_notes="Filter cleaned, refrigerant topped up",
            repair_cost=Decimal("210000.00"),
            downtime_minutes=110,
            external_message_id="seed-cool01-resolved",
        ),
        Incident(
            equipment_id=None,
            sender_phone="+255754221001",
            recipient_number="20880",
            original_message="Packaging machine stopped again",
            channel="SMS",
            category="STOPPAGE",
            severity="MEDIUM",
            status="ACKNOWLEDGED",
            reported_at=at(days=6),
            acknowledged_at=at(days=6, hours=-1),
            external_message_id="seed-unassigned",
        ),
    ]
    db.add_all(rows)


def seed_if_empty(db: Session) -> None:
    if db.query(Equipment).count() > 0:
        return
    by_code = seed_equipment(db)
    seed_demo_incidents(db, by_code)
    db.commit()
