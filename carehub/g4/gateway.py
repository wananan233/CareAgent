"""只接受最小化事实副本的 G4 Model Gateway；不持有数据库、设备或 Skill。"""
from __future__ import annotations

import json
import re
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
from typing import Any, Mapping, Protocol


ALLOWED_PURPOSES = frozenset({"TODAY_STATUS", "DAILY_SUMMARY", "WEEKLY_TREND", "CHANGE_EXPLANATION", "READ_ONLY_QA"})
FORBIDDEN_TERMS = ("诊断", "处方", "剂量", "加药", "减药", "停药", "已吞服", "已服药", "立即拨打", "触发SOS", "调用工具")
PII_PATTERN = re.compile(r"(?:1[3-9]\d{9}|(?:0\d{2,3}-?)?\d{7,8}|[\w.+-]+@[\w-]+\.[\w.-]+|\b\d{15,18}[0-9Xx]\b|(?:姓名|电话|地址|家庭成员|家属|住址|未授权正文|原始病历)\s*[:：])")
TEMPLATES = {
    "TODAY_STATUS": "当前可确认的信息如下，请按页面中的来源和时间查看详情。",
    "DAILY_SUMMARY": "今日摘要暂时无法生成，请以已确认的时间线记录为准。",
    "WEEKLY_TREND": "本周趋势暂时无法生成，请以带来源的时间线记录为准。",
    "CHANGE_EXPLANATION": "当前无法解释变化，请先查看已确认的来源记录。",
    "READ_ONLY_QA": "没有足够的已授权信息可以回答这个问题。",
}


class ModelGatewayError(RuntimeError):
    """Provider 或输出不满足受控边界。"""


class Provider(Protocol):
    version: str
    def generate(self, *, purpose: str, facts: list[dict[str, Any]], question: str | None = None) -> str: ...


@dataclass
class FakeProvider:
    """离线 CI 默认 Provider，不保存输入，也不执行网络请求。"""
    version: str = "fake-llm.g4.v1"
    malformed: bool = False
    blocked: bool = False

    def generate(self, *, purpose: str, facts: list[dict[str, Any]], question: str | None = None) -> str:
        del purpose, question
        if self.malformed:
            return "不是 JSON"
        message = "诊断结果" if self.blocked else "以下内容仅基于已授权且有来源的记录。"
        return json.dumps({"message": message, "fact_indexes": list(range(len(facts)))}, ensure_ascii=False)


class ModelGateway:
    """Provider 仅能看到去标识化事实，输出永远先过 schema 与安全扫描。"""

    def __init__(self, provider: Provider | None = None, *, cancelled: callable | None = None, budget_seconds: float = 2.0) -> None:
        self.provider = provider or FakeProvider()
        self.cancelled, self.budget_seconds = cancelled or (lambda: False), budget_seconds
        self._cache: dict[str, dict[str, Any]] = {}
        self.metrics = {"provider_calls": 0, "cache_hits": 0, "fallbacks": 0, "latency_ms": [], "token_estimate": 0}
        self._failures, self._circuit = 0, "CLOSED"
        self._opened_at, self._half_open_inflight = 0.0, False

    def generate(self, *, purpose: str, minimal_context: Mapping[str, Any], authorization_fingerprint: str = "") -> dict[str, Any]:
        if purpose not in ALLOWED_PURPOSES:
            return self._fallback(purpose, "PURPOSE_DENIED", [])
        cache_key = hashlib.sha256(json.dumps({"purpose": purpose, "facts": minimal_context.get("facts"), "question": minimal_context.get("question"), "authorization": authorization_fingerprint}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        if authorization_fingerprint and cache_key in self._cache:
            self.metrics["cache_hits"] += 1
            return dict(self._cache[cache_key])
        if self._circuit == "OPEN":
            if time.monotonic() - self._opened_at < 1.0:
                self.metrics["fallbacks"] += 1
                return self._fallback(purpose, "CIRCUIT_OPEN", [])
            if self._half_open_inflight:
                self.metrics["fallbacks"] += 1
                return self._fallback(purpose, "CIRCUIT_OPEN", [])
            self._circuit, self._half_open_inflight = "HALF_OPEN", True
        try:
            facts = self._minimize(minimal_context)
            started = time.monotonic()
            self.metrics["token_estimate"] += sum((len(fact["text"]) + 3) // 4 for fact in facts)
            if self.cancelled(): raise ModelGatewayError("CANCELLED")
            try:
                executor = ThreadPoolExecutor(max_workers=1)
                question = minimal_context.get("question")
                if question is not None and (not isinstance(question, str) or not question.strip() or len(question) > 280):
                    raise ModelGatewayError("QUESTION_INVALID")
                if question is not None and PII_PATTERN.search(question):
                    raise ModelGatewayError("QUESTION_DLP_BLOCKED")
                provider_args = {"purpose": purpose, "facts": facts}
                if question is not None:
                    provider_args["question"] = question
                self.metrics["provider_calls"] += 1
                future = executor.submit(self.provider.generate, **provider_args)
                try:
                    raw = future.result(timeout=max(0.0, self.budget_seconds - (time.monotonic() - started)))
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)
            except (TimeoutError, FutureTimeout, OSError) as error:
                if self.cancelled() or time.monotonic() - started >= self.budget_seconds: raise ModelGatewayError("CANCELLED" if self.cancelled() else "BUDGET_EXCEEDED") from error
                executor = ThreadPoolExecutor(max_workers=1)
                future = executor.submit(self.provider.generate, **provider_args)
                try:
                    raw = future.result(timeout=max(0.0, self.budget_seconds - (time.monotonic() - started)))
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)
            if self.cancelled() or time.monotonic() - started > self.budget_seconds: raise ModelGatewayError("CANCELLED" if self.cancelled() else "BUDGET_EXCEEDED")
            payload = self._parse(raw, facts)
            if self.cancelled(): raise ModelGatewayError("CANCELLED")
            if any(term in payload["message"] for term in FORBIDDEN_TERMS):
                raise ModelGatewayError("SAFETY_SCAN_BLOCKED")
            result = {"message": payload["message"], "facts": [facts[index] for index in payload["fact_indexes"]],
                    "fallback": "NONE", "generator_version": self.provider.version, "reason_code": "ALLOW"}
            self._failures, self._circuit, self._half_open_inflight = 0, "CLOSED", False
            if authorization_fingerprint: self._cache[cache_key] = dict(result)
            self.metrics["latency_ms"].append(round((time.monotonic() - started) * 1000))
            return result
        except ModelGatewayError as error:
            self._failures += 1; self._circuit = "OPEN" if self._failures >= 3 or self._circuit == "HALF_OPEN" else "CLOSED"; self._opened_at = time.monotonic() if self._circuit == "OPEN" else self._opened_at; self._half_open_inflight = False; self.metrics["fallbacks"] += 1
            return self._fallback(purpose, str(error) or "MODEL_UNAVAILABLE", [])
        except (TimeoutError, OSError, ValueError, TypeError, json.JSONDecodeError):
            # Provider/传输实现细节不得成为响应或审计中的不受控错误文本。
            self._failures += 1
            self._circuit = "OPEN" if self._failures >= 3 or self._circuit == "HALF_OPEN" else "CLOSED"
            if self._circuit == "OPEN": self._opened_at = time.monotonic()
            self._half_open_inflight = False
            self.metrics["fallbacks"] += 1
            return self._fallback(purpose, "MODEL_UNAVAILABLE", [])

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
