"""只接受最小化事实副本的 G4 Model Gateway；不持有数据库、设备或 Skill。"""
from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
from typing import Any, Mapping, Protocol


ALLOWED_PURPOSES = frozenset({"TODAY_STATUS", "DAILY_SUMMARY"})
FORBIDDEN_TERMS = ("诊断", "处方", "剂量", "加药", "减药", "停药", "已吞服", "已服药", "立即拨打", "触发SOS", "调用工具")
PII_PATTERN = re.compile(r"(?:1[3-9]\d{9}|(?:0\d{2,3}-?)?\d{7,8}|[\w.+-]+@[\w-]+\.[\w.-]+|\b\d{15,18}[0-9Xx]\b|(?:姓名|电话|地址|家庭成员|家属|住址|未授权正文|原始病历)\s*[:：])")
TEMPLATES = {
    "TODAY_STATUS": "当前可确认的信息如下，请按页面中的来源和时间查看详情。",
    "DAILY_SUMMARY": "今日摘要暂时无法生成，请以已确认的时间线记录为准。",
}


class ModelGatewayError(RuntimeError):
    """Provider 或输出不满足受控边界。"""


class Provider(Protocol):
    version: str
    def generate(self, *, purpose: str, facts: list[dict[str, Any]]) -> str: ...


@dataclass
class FakeProvider:
    """离线 CI 默认 Provider，不保存输入，也不执行网络请求。"""
    version: str = "fake-llm.g4.v1"
    malformed: bool = False
    blocked: bool = False

    def generate(self, *, purpose: str, facts: list[dict[str, Any]]) -> str:
        del purpose
        if self.malformed:
            return "不是 JSON"
        message = "诊断结果" if self.blocked else "以下内容仅基于已授权且有来源的记录。"
        return json.dumps({"message": message, "fact_indexes": list(range(len(facts)))}, ensure_ascii=False)


class ModelGateway:
    """Provider 仅能看到去标识化事实，输出永远先过 schema 与安全扫描。"""

    def __init__(self, provider: Provider | None = None, *, cancelled: callable | None = None, budget_seconds: float = 2.0) -> None:
        self.provider = provider or FakeProvider()
        self.cancelled, self.budget_seconds = cancelled or (lambda: False), budget_seconds

    def generate(self, *, purpose: str, minimal_context: Mapping[str, Any]) -> dict[str, Any]:
        if purpose not in ALLOWED_PURPOSES:
            return self._fallback(purpose, "PURPOSE_DENIED", [])
        try:
            facts = self._minimize(minimal_context)
            started = time.monotonic()
            if self.cancelled(): raise ModelGatewayError("CANCELLED")
            try:
                executor = ThreadPoolExecutor(max_workers=1)
                future = executor.submit(self.provider.generate, purpose=purpose, facts=facts)
                try:
                    raw = future.result(timeout=max(0.0, self.budget_seconds - (time.monotonic() - started)))
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)
            except (TimeoutError, FutureTimeout, OSError) as error:
                if self.cancelled() or time.monotonic() - started >= self.budget_seconds: raise ModelGatewayError("CANCELLED" if self.cancelled() else "BUDGET_EXCEEDED") from error
                executor = ThreadPoolExecutor(max_workers=1)
                future = executor.submit(self.provider.generate, purpose=purpose, facts=facts)
                try:
                    raw = future.result(timeout=max(0.0, self.budget_seconds - (time.monotonic() - started)))
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)
            if self.cancelled() or time.monotonic() - started > self.budget_seconds: raise ModelGatewayError("CANCELLED" if self.cancelled() else "BUDGET_EXCEEDED")
            payload = self._parse(raw, facts)
            if self.cancelled(): raise ModelGatewayError("CANCELLED")
            if any(term in payload["message"] for term in FORBIDDEN_TERMS):
                raise ModelGatewayError("SAFETY_SCAN_BLOCKED")
            return {"message": payload["message"], "facts": [facts[index] for index in payload["fact_indexes"]],
                    "fallback": "NONE", "generator_version": self.provider.version, "reason_code": "ALLOW"}
        except (ModelGatewayError, TimeoutError, OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            return self._fallback(purpose, str(error) or "MODEL_UNAVAILABLE", [])

    @staticmethod
    def _minimize(context: Mapping[str, Any]) -> list[dict[str, Any]]:
        # 只让 provider 接收已授权显示事实及其来源；丢弃 subject、家庭、原始事件和对话文本。
        facts = context.get("facts")
        if not isinstance(facts, list) or len(facts) > 50:
            raise ModelGatewayError("CONTEXT_INVALID")
        result = []
        for fact in facts:
            if set(fact) != {"text", "source_refs"} or not isinstance(fact["text"], str) or not isinstance(fact["source_refs"], list) or not fact["source_refs"]:
                raise ModelGatewayError("CONTEXT_INVALID")
            if PII_PATTERN.search(fact["text"]):
                raise ModelGatewayError("DLP_BLOCKED")
            result.append({"text": fact["text"][:280], "source_refs": list(fact["source_refs"])})
        return result

    @staticmethod
    def _parse(raw: str, facts: list[dict[str, Any]]) -> dict[str, Any]:
        try:
            value = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as error:
            raise ModelGatewayError("INVALID_JSON") from error
        if set(value) != {"message", "fact_indexes"} or not isinstance(value["message"], str) or not value["message"].strip() or len(value["message"]) > 280 or not isinstance(value["fact_indexes"], list):
            raise ModelGatewayError("SCHEMA_INVALID")
        indexes = value["fact_indexes"]
        if any(not isinstance(index, int) or isinstance(index, bool) or index < 0 or index >= len(facts) for index in indexes):
            raise ModelGatewayError("SOURCE_REF_INVALID")
        return {"message": value["message"].strip(), "fact_indexes": list(dict.fromkeys(indexes))}

    @staticmethod
    def _fallback(purpose: str, reason: str, facts: list[dict[str, Any]]) -> dict[str, Any]:
        return {"message": TEMPLATES.get(purpose, "当前请求无法处理。"), "facts": facts,
                "fallback": "TEMPLATE_FALLBACK", "generator_version": "response-template-g4.v1", "reason_code": reason}
