# app/models.py
from __future__ import annotations

from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)

    # YYYY-MM-DD as string for demo simplicity (could be Date)
    certification_expiry: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    ncs: Mapped[list["NonConformity"]] = relationship(back_populates="supplier")


class NonConformity(Base):
    __tablename__ = "nonconformities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. low/medium/high
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")  # OPEN/CLOSED
    description: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    supplier: Mapped["Supplier"] = relationship(back_populates="ncs")

    __table_args__ = (
        Index("ix_ncs_supplier_id", "supplier_id"),
        Index("ix_ncs_status", "status"),
    )


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Unique event id for idempotency + dedupe (string UUID later; for demo we use string)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. NC_CREATED
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)

    # PENDING / PROCESSING / DONE / FAILED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Lock/claim metadata (for multi-worker safety)
    locked_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_outbox_status", "status"),
        Index("ix_outbox_created_at", "created_at"),
        Index("ix_outbox_status_locked_at", "status", "locked_at"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    actor: Mapped[str] = mapped_column(String(100), nullable=False, default="system")
    action: Mapped[str] = mapped_column(String(100), nullable=False)

    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)

    meta_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_created_at", "created_at"),
    )


class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    __table_args__ = (
        Index("ix_processed_event_id", "event_id"),
    )
