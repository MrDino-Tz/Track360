from sqlalchemy.orm import Session

from app.models import Equipment


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


def seed_if_empty(db: Session) -> None:
    if db.query(Equipment).count() > 0:
        return
    seed_equipment(db)
    db.commit()
