"""A0 能力的确定性上下文：模型只能表述，不能计算趋势或推断原因。"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Any


def trend_context(items: list[dict[str, Any]]) -> dict[str, Any]:
    """从已授权 timeline 计算最近/此前两个七日窗口及其可追溯事实。"""
    parsed = [(item, _time(item.get("occurred_at"))) for item in items if item.get("event_id")]
    if not parsed:
        return {"facts": [], "unknowns": [{"field": "weekly_timeline", "reason": "NO_AUTHORIZED_RECORDS"}],
                "why_it_matters": ["当前没有足够的已授权记录用于比较。"],
                "suggested_safe_actions": ["查看时间线或联系已授权照护人员确认。"]}
    end = max(value for _, value in parsed)
    recent_start, previous_start = end - timedelta(days=6), end - timedelta(days=13)
    recent = [item for item, value in parsed if recent_start <= value <= end]
    previous = [item for item, value in parsed if previous_start <= value < recent_start]
    recent_counts, previous_counts = Counter(item.get("event_type", "UNKNOWN") for item in recent), Counter(item.get("event_type", "UNKNOWN") for item in previous)
    facts = []
    for event_type in sorted(set(recent_counts) | set(previous_counts)):
        change = recent_counts[event_type] - previous_counts[event_type]
        refs = [item["event_id"] for item in recent + previous if item.get("event_type", "UNKNOWN") == event_type]
        facts.append({"text": f"最近7天 {event_type} 有 {recent_counts[event_type]} 条，较此前7天变化 {change:+d} 条。", "source_refs": refs})
    unknowns = [{"field": f"event_quality:{item['event_id']}", "reason": str(item.get("quality", "UNKNOWN"))}
                for item in recent if item.get("quality") not in {None, "VALID", "HIGH"}]
    return {"facts": facts, "unknowns": unknowns,
            "why_it_matters": ["该比较仅反映已授权记录数量的变化，不代表医疗结论。"],
            "suggested_safe_actions": ["查看带来源的时间线确认变化。", "如记录存在未知或冲突，请联系已授权照护人员确认。"]}


def _time(value: Any) -> datetime:
    if not isinstance(value, str):
        return datetime.min.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
