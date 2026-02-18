from __future__ import annotations

import json
from typing import Any

from app.logging_utils import get_request_id


def merge_audit_meta(meta: dict[str, Any] | None = None) -> str:
    """
    Merge provided meta with request_id (from contextvar) if missing.
    Return JSON string.
    """
    base: dict[str, Any] = dict(meta or {})

    rid = get_request_id()
    if rid and "request_id" not in base:
        base["request_id"] = rid

    return json.dumps(base, ensure_ascii=False)
