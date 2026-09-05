from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Equipment(Base):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    equipment_type: Mapped[str] = mapped_column(String(64))
    location: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(32), default="OPERATIONAL")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    incidents: Mapped[list["Incident"]] = relationship(back_populates="equipment")


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        UniqueConstraint("external_message_id", name="uq_incidents_external_message_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    equipment_id: Mapped[int | None] = mapped_column(ForeignKey("equipment.id"), nullable=True, index=True)
    sender_phone: Mapped[str] = mapped_column(String(32), index=True)
    recipient_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    original_message: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(16), default="SMS")
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    severity: Mapped[str] = mapped_column(String(16), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(32), default="NEW", index=True)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    repair_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    repair_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    downtime_minutes: Mapped[int | None] = mapped_column(nullable=True)
    external_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    equipment: Mapped[Equipment | None] = relationship(back_populates="incidents")

    rewards: Mapped[list["Reward"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )


class Reward(Base):
    """A motivational payout (airtime or mobile money) sent to a reporter."""

    __tablename__ = "rewards"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int | None] = mapped_column(
        ForeignKey("incidents.id"), nullable=True, index=True
    )
    sender_phone: Mapped[str] = mapped_column(String(32), index=True)
    method: Mapped[str] = mapped_column(String(32))
    currency: Mapped[str] = mapped_column(String(8))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    provider_status: Mapped[str] = mapped_column(String(32), default="QUEUED")
    provider_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    incident: Mapped[Incident | None] = relationship(back_populates="rewards")
