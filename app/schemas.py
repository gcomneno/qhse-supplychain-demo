from __future__ import annotations

from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


Severity = Literal["low", "medium", "high"]


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    certification_expiry: Optional[str] = Field(default=None, description="YYYY-MM-DD (demo)")


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    certification_expiry: Optional[str]


class NCCreate(BaseModel):
    supplier_id: int
    severity: Severity
    description: str = Field(min_length=1)


class NCOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_id: int
    severity: str
    status: str
    description: str


class SupplierDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    certification_expiry: Optional[str]

    nc_total: int
    nc_open: int
    nc_open_high: int
    is_at_risk: bool


class SupplierCertUpdate(BaseModel):
    certification_expiry: Optional[str] = Field(default=None, description="YYYY-MM-DD (demo)")


class AuditLogOut(BaseModel):
    id: int
    actor: str
    action: str
    entity_type: str
    entity_id: str
    meta_json: str
    created_at: datetime

    model_config = {"from_attributes": True}
