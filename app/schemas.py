from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class EquipmentCreate(BaseModel):
    code: str
    name: str
    equipment_type: str
    location: str
    status: str = "OPERATIONAL"


class EquipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    equipment_type: str
    location: str
    status: str
    created_at: datetime


class EquipmentHistoryOut(EquipmentOut):
    incident_count: int
    open_count: int
    total_repair_cost: Decimal
    total_downtime_minutes: int


class IncidentUpdate(BaseModel):
    equipment_id: int | None = None
    category: str | None = None
    severity: str | None = None
    status: str | None = None
    repair_notes: str | None = None
    repair_cost: Decimal | None = None
    downtime_minutes: int | None = Field(default=None, ge=0)


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipment_id: int | None
    equipment: EquipmentOut | None = None
    sender_phone: str
    recipient_number: str | None
    original_message: str
    channel: str
    category: str | None
    severity: str
    status: str
    reported_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    repair_notes: str | None
    repair_cost: Decimal | None
    downtime_minutes: int | None
    external_message_id: str | None
    created_at: datetime
    updated_at: datetime


class FailingEquipment(BaseModel):
    equipment_id: int
    code: str
    name: str
    incident_count: int
    total_repair_cost: Decimal
    total_downtime_minutes: int


class CategoryCount(BaseModel):
    category: str
    count: int


class DashboardSummary(BaseModel):
    total_equipment: int
    new_incidents: int
    open_incidents: int
    under_repair: int
    resolved_today: int
    incidents_this_month: int
    maintenance_cost: Decimal
    total_downtime_minutes: int
    insights: list[str]
    failing_equipment: list[FailingEquipment]
    recurring_categories: list[CategoryCount]


class WebhookAck(BaseModel):
    duplicate: bool
    incident_id: int | None = None
