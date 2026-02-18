from __future__ import annotations

import json
from sqlalchemy.orm import Session

from app.audit_utils import merge_audit_meta
from app.models import AuditLog


def handle_nc_created(session: Session, payload_json: str) -> None:
    payload = json.loads(payload_json)

    session.add(
        AuditLog(
            actor="system",
            action="NC_CREATED_HANDLED",
            entity_type="NonConformity",
            entity_id=str(payload["nc_id"]),
            meta_json=merge_audit_meta(payload),
        )
    )


def handle_nc_closed(session: Session, payload_json: str) -> None:
    payload = json.loads(payload_json)

    session.add(
        AuditLog(
            actor="system",
            action="NC_CLOSED_HANDLED",
            entity_type="NonConformity",
            entity_id=str(payload["nc_id"]),
            meta_json=merge_audit_meta(payload),
        )
    )


def handle_supplier_cert_updated(session: Session, payload_json: str) -> None:
    payload = json.loads(payload_json)

    session.add(
        AuditLog(
            actor="system",
            action="SUPPLIER_CERT_UPDATED_HANDLED",
            entity_type="Supplier",
            entity_id=str(payload["supplier_id"]),
            meta_json=merge_audit_meta(payload),
        )
    )
