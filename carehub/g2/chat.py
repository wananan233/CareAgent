"""G2 基础聊天层。

此模块不依赖 EventStore、设备适配器或 Skill。模型适配器只能接收经过
契约校验的上下文快照，并且只能返回用于构造 AgentResponseV1 的文本草稿。
"""

from __future__ import annotations

import hashlib
from http.client import HTTPException
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "contracts" / "schemas"
CHANNELS = frozenset({"TERMINAL", "TTS", "FAMILY"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical_hash(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _load_validator(name: str) -> Draft202012Validator:
    with (SCHEMAS / name).open(encoding="utf-8") as source:
        return Draft202012Validator(json.load(source), format_checker=FormatChecker())


def _validate(validator: Draft202012Validator, value: Mapping[str, Any], label: str) -> None:
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.path))
    if errors:
        raise ValueError(f"{label} 不符合契约: {errors[0].message}")


def build_context_snapshot(
    *,
    subject_id: str,
    source_event_ids: list[str],
    consent_scopes: list[str],
    consent_expires_at: str,
    unknowns: list[dict[str, str]] | None = None,
    facts: list[dict[str, Any]] | None = None,
    as_of: str | None = None,
) -> dict[str, Any]:
    """构造只含授权元数据与来源引用的 CHAT 快照，不携带原始事件载荷。"""
    snapshot = {
        "schema_version": "ContextSnapshotV1",
        "snapshot_id": f"snapshot-{uuid.uuid4()}",
        "subject_id": subject_id,
        "purpose": "CHAT",
        "as_of": as_of or _utc_now(),
        "consent": {"scopes": consent_scopes, "expires_at": consent_expires_at},
        "facts": facts or [],
        "unknowns": unknowns or [],
        "source_event_ids": source_event_ids,
    }
    snapshot["hash"] = _canonical_hash(snapshot)
    _validate(_load_validator("context-snapshot.v1.json"), snapshot, "上下文快照")
    return snapshot


class ResponseGenerator(Protocol):
    """模型网关的最小接口，不能取得服务、数据库或设备对象。"""

    def generate(
        self,
        *,
        message: str,
        context_snapshot: Mapping[str, Any],
        history: Sequence[Mapping[str, str]] = (),
    ) -> Mapping[str, Any]: ...


class FakeLLM:
    """确定性测试替身；不访问网络，也不保存用户输入。"""

    generator_version = "fake-llm.g2.v1"

    def generate(
        self,
        *,
        message: str,
        context_snapshot: Mapping[str, Any],
        history: Sequence[Mapping[str, str]] = (),
    ) -> Mapping[str, Any]:
        del message, context_snapshot, history
        return {
            "message": "我可以协助查看提醒和当前安全状态。请告诉我您想了解哪一项。",
            "facts": [],
            "fallback": "TEMPLATE_FALLBACK",
            "generator_version": self.generator_version,
        }


class DeepSeekGenerator:
    """DeepSeek Chat Completions 的无工具、无状态适配器。

    密钥只在实际请求时从 ``DEEPSEEK_API_KEY`` 读取，绝不会写入事件、日志或
    聊天响应。该适配器不声明 tools，因而模型不能请求执行任何外部操作。
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "deepseek-v4-flash",
        base_url: str = "https://api.deepseek.com",
        timeout_seconds: float = 15.0,
        opener: Any = urlopen,
    ) -> None:
        self._api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._opener = opener

    def generate(
        self,
        *,
        message: str,
        context_snapshot: Mapping[str, Any],
        history: Sequence[Mapping[str, str]] = (),
    ) -> Mapping[str, Any]:
        api_key = self._api_key or __import__("os").environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("未设置 DEEPSEEK_API_KEY，无法调用 DeepSeek")

        system_message = (
            "你是 CareHub 的只读照护聊天助手。仅基于提供的上下文回答；"
            "未知信息必须明确说明未知。不得给出医疗诊断、剂量调整、紧急处置指令，"
            "不得声称已执行动作，也不得调用或建议调用工具。回复使用简体中文，限 280 字。"
            "必须输出 json 对象：{\"message\":\"回复\",\"fact_indexes\":[0]}。"
            "fact_indexes 只能列出授权上下文 facts 数组中实际用到的从 0 开始的索引；无引用时使用空数组。"
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "system", "content": f"授权上下文快照：{json.dumps(dict(context_snapshot), ensure_ascii=False, sort_keys=True)}"},
                *history,
                {"role": "user", "content": message},
            ],
            "temperature": 0.2,
            "max_tokens": 280,
            "stream": False,
            "response_format": {"type": "json_object"},
        }
        request = Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._opener(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, HTTPException, OSError, TimeoutError, json.JSONDecodeError) as error:
            raise RuntimeError("DeepSeek 模型调用失败") from error

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("DeepSeek 返回内容不符合预期") from error
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("DeepSeek 返回了空回复")
        try:
            structured = json.loads(content)
            message = structured["message"]
            indexes = structured.get("fact_indexes", [])
            facts = context_snapshot.get("facts", [])
            if not isinstance(message, str) or not isinstance(indexes, list):
                raise ValueError
            if any(not isinstance(index, int) or isinstance(index, bool) or index < 0 or index >= len(facts) for index in indexes):
                raise ValueError
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            raise RuntimeError("DeepSeek 返回的引用格式不符合预期") from None
        return {
            "message": message.strip(),
            "facts": [facts[index] for index in dict.fromkeys(indexes)],
            "fallback": "NONE",
            "generator_version": f"deepseek:{self.model}",
        }


class ChatService:
    """将聊天输入约束为只读快照和 AgentResponseV1。"""

    def __init__(self, generator: ResponseGenerator | None = None) -> None:
        self._generator = generator or FakeLLM()
        self._context_validator = _load_validator("context-snapshot.v1.json")
        self._response_validator = _load_validator("agent-response.v1.json")

    def respond(
        self,
        *,
        message: str,
        context_snapshot: Mapping[str, Any],
        channel: str = "TERMINAL",
        agent_run_id: str | None = None,
        history: Sequence[Mapping[str, str]] = (),
    ) -> dict[str, Any]:
        """返回已校验的只读回复，不写事件、不生成 ActionIntent、不执行任何动作。"""
        if not isinstance(message, str) or not message.strip() or len(message) > 500:
            raise ValueError("聊天消息必须是 1 到 500 个字符的非空文本")
        if channel not in CHANNELS:
            raise ValueError(f"不支持的聊天渠道: {channel}")

        safe_context = json.loads(json.dumps(dict(context_snapshot), ensure_ascii=False))
        _validate(self._context_validator, safe_context, "上下文快照")
        snapshot_for_hash = {key: value for key, value in safe_context.items() if key != "hash"}
        if safe_context["hash"] != _canonical_hash(snapshot_for_hash):
            raise ValueError("聊天上下文快照哈希不匹配")
        if safe_context["purpose"] != "CHAT":
            raise ValueError("聊天仅接受 purpose=CHAT 的上下文快照")
        if "chat" not in safe_context["consent"]["scopes"]:
            raise ValueError("聊天需要有效的 chat 同意范围")
        expires_at = datetime.fromisoformat(safe_context["consent"]["expires_at"].replace("Z", "+00:00"))
        if expires_at <= datetime.now(timezone.utc):
            raise ValueError("聊天上下文的同意已过期")
        safe_history = self._validate_history(history)

        draft = self._generator.generate(
            message=message.strip(), context_snapshot=safe_context, history=safe_history
        )
        response = {
            "schema_version": "AgentResponseV1",
            "response_id": f"response-{uuid.uuid4()}",
            "agent_run_id": agent_run_id or f"run-{uuid.uuid4()}",
            "channel": channel,
            "message": draft.get("message"),
            "facts": draft.get("facts", []),
            "fallback": draft.get("fallback", "DETERMINISTIC_FALLBACK"),
            "generator_version": draft.get("generator_version", "unknown"),
        }
        self._assert_fact_sources(response["facts"], safe_context["source_event_ids"])
        _validate(self._response_validator, response, "聊天回复")
        return response

    @staticmethod
    def _assert_fact_sources(facts: Any, source_event_ids: list[str]) -> None:
        if not isinstance(facts, list):
            raise ValueError("聊天事实必须是列表")
        allowed_sources = set(source_event_ids)
        for fact in facts:
            if not isinstance(fact, dict) or not set(fact.get("source_refs", [])).issubset(allowed_sources):
                raise ValueError("聊天事实只能引用上下文快照中的来源事件")

    @staticmethod
    def _validate_history(history: Sequence[Mapping[str, str]]) -> tuple[dict[str, str], ...]:
        if len(history) > 6:
            raise ValueError("聊天历史最多包含最近 3 轮")
        safe_history: list[dict[str, str]] = []
        for item in history:
            if set(item) != {"role", "content"} or item["role"] not in {"user", "assistant"}:
                raise ValueError("聊天历史格式无效")
            if not isinstance(item["content"], str) or not item["content"].strip() or len(item["content"]) > 500:
                raise ValueError("聊天历史消息无效")
            safe_history.append({"role": item["role"], "content": item["content"].strip()})
        return tuple(safe_history)


class ChatSession:
    """仅在进程内保存最近几轮对话，退出后自动丢弃。"""

    def __init__(
        self,
        service: ChatService,
        context_snapshot: Mapping[str, Any],
        *,
        max_turns: int = 3,
    ) -> None:
        if max_turns < 1:
            raise ValueError("max_turns 至少为 1")
        self._service = service
        self._context_snapshot = dict(context_snapshot)
        self._max_turns = max_turns
        self._history: list[dict[str, str]] = []

    @property
    def history(self) -> tuple[dict[str, str], ...]:
        return tuple(dict(item) for item in self._history)

    def ask(self, message: str, *, channel: str = "TERMINAL") -> dict[str, Any]:
        response = self._service.respond(
            message=message,
            context_snapshot=self._context_snapshot,
            channel=channel,
            history=self._history,
        )
        self._history.extend(
            [
                {"role": "user", "content": message.strip()},
                {"role": "assistant", "content": response["message"]},
            ]
        )
        del self._history[: max(0, len(self._history) - self._max_turns * 2)]
        return response
