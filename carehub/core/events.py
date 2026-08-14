"""事件构造与摘要哈希。所有示例数据均为合成数据。"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def checksum(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def new_event(
    *,
    aggregate: str,
    sequence: int,
    event_type: str,
    payload: dict[str, Any] | None = None,
    source: str = "SIMULATOR",
    quality: str = "HIGH",
    privacy: str = "INTERNAL",
    correlation_id: str | None = None,
    causation_id: str | None = None,
    event_id: str | None = None,
    occurred_at: str | None = None,
) -> dict[str, Any]:
    """生成符合 CareEventV1 最小字段集的不可变事件。"""
    body = {"event_type": event_type, **(payload or {})}
    time = occurred_at or utc_now()
    return {
        "schema_version": "CareEventV1",
        "event_id": event_id or f"evt-{uuid.uuid4()}",
        "aggregate": aggregate,
        "sequence": sequence,
        "occurred_at": time,
        "received_at": utc_now(),
        "source": source,
        "quality": quality,
        "privacy": privacy,
        "payload": body,
        "checksum": checksum(body),
        "correlation_id": correlation_id or f"corr-{uuid.uuid4()}",
        "causation_id": causation_id,
        "trace_id": f"trace-{uuid.uuid4()}",
    }
