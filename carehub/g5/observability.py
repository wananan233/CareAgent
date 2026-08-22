"""不含敏感正文的 trace/metrics，以及从事件库重建的重放报告。"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import quantiles
from typing import Any, Iterable

from carehub.core.projections import Projections


@dataclass(frozen=True)
class TraceSpan:
    trace_id: str
    operation: str
    duration_ms: float
    outcome: str
    reason_code: str


class TraceRecorder:
    """只记录关联 ID、操作、耗时、结果和原因码；禁止写入消息/健康正文。"""
    def __init__(self) -> None:
        self._spans: list[TraceSpan] = []

    def record(self, *, trace_id: str, operation: str, duration_ms: float, outcome: str, reason_code: str) -> None:
        if not trace_id.startswith("trace-") or duration_ms < 0 or not all(isinstance(item, str) and item for item in (operation, outcome, reason_code)):
            raise ValueError("trace 字段无效")
        self._spans.append(TraceSpan(trace_id, operation, duration_ms, outcome, reason_code))

    def spans(self) -> tuple[TraceSpan, ...]:
        return tuple(self._spans)


class Metrics:
    def __init__(self, traces: TraceRecorder) -> None:
        self._traces = traces

    def snapshot(self) -> dict[str, dict[str, float | int]]:
        grouped: dict[str, list[float]] = {}
        for span in self._traces.spans():
            grouped.setdefault(span.operation, []).append(span.duration_ms)
        result = {}
        for operation, values in grouped.items():
            values.sort()
            p95 = values[0] if len(values) == 1 else quantiles(values, n=100, method="inclusive")[94]
            result[operation] = {"count": len(values), "p95_ms": p95, "max_ms": values[-1]}
        return result


@dataclass(frozen=True)
class ReplayReport:
    event_count: int
    projection_digest: str
    duplicate_event_ids: int
    safety_alerts: int


def replay_report(events: Iterable[dict[str, Any]]) -> ReplayReport:
    """固定顺序重建投影并给出可比较摘要；不触发规则或任何副作用。"""
    items = list(events)
    projection = Projections.rebuild(items)
    event_ids = [item["event_id"] for item in items]
    return ReplayReport(
        event_count=len(items), projection_digest=projection.digest(),
        duplicate_event_ids=len(event_ids) - len(set(event_ids)),
        safety_alerts=sum(1 for alert in projection.alerts.values() if alert.get("safety_level") in {"S-1", "S0"}),
    )
