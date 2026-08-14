"""G2 固定响应模板与安全扫描；不调用模型。"""
from __future__ import annotations
import uuid
from typing import Any

FORBIDDEN = ("诊断", "剂量", "加药", "减药", "已吞服", "已服药", "处方", "立即拨打")
FALLBACK = "当前信息需要按本地照护流程确认。"

class ResponseEngine:
    def render(self, *, agent_run_id: str, channel: str, template: str, facts: list[dict[str, Any]]) -> dict[str, Any]:
        if not facts or any(not item.get("source_refs") for item in facts):
            return self._fallback(agent_run_id, channel, "FACTS_INVALID")
        if any(term in template for term in FORBIDDEN):
            return self._fallback(agent_run_id, channel, "SAFETY_SCAN_BLOCKED")
        return {"schema_version":"AgentResponseV1","response_id":f"response-{uuid.uuid4()}","agent_run_id":agent_run_id,"channel":channel,"message":template,"facts":facts,"fallback":"NONE","generator_version":"response-template-g2.v1"}
    def _fallback(self, run_id: str, channel: str, reason: str) -> dict[str, Any]:
        return {"schema_version":"AgentResponseV1","response_id":f"response-{uuid.uuid4()}","agent_run_id":run_id,"channel":channel,"message":FALLBACK,"facts":[{"text":reason,"source_refs":["system:response-engine"]}],"fallback":"TEMPLATE_FALLBACK","generator_version":"response-template-g2.v1"}
