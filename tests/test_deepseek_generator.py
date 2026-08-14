"""DeepSeek 适配器测试：不发起真实网络请求，也不使用真实密钥。"""

from __future__ import annotations

import json
from http.client import RemoteDisconnected

import pytest

from carehub.g2 import DeepSeekGenerator


class _Response:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload, ensure_ascii=False).encode("utf-8")


def test_deepseek_generator_uses_compatible_endpoint_without_tools() -> None:
    captured: dict = {}

    def opener(request: object, *, timeout: float) -> _Response:
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _Response({"choices": [{"message": {"content": '{"message":"这是安全的只读回复。","fact_indexes":[0]}'}}]})

    generator = DeepSeekGenerator(api_key="test-key", opener=opener)
    context = {"purpose": "CHAT", "facts": [{"text": "模拟事实", "source_refs": ["evt-1"]}]}
    draft = generator.generate(
        message="你好",
        context_snapshot=context,
        history=[{"role": "user", "content": "上一轮问题"}],
    )

    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["payload"]["model"] == "deepseek-v4-flash"
    assert "tools" not in captured["payload"]
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["messages"][-2:] == [
        {"role": "user", "content": "上一轮问题"},
        {"role": "user", "content": "你好"},
    ]
    assert draft == {
        "message": "这是安全的只读回复。",
        "facts": [{"text": "模拟事实", "source_refs": ["evt-1"]}],
        "fallback": "NONE",
        "generator_version": "deepseek:deepseek-v4-flash",
    }


def test_deepseek_generator_requires_environment_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        DeepSeekGenerator().generate(message="你好", context_snapshot={"purpose": "CHAT"})


def test_deepseek_generator_normalizes_transport_failure() -> None:
    def failing_opener(request: object, *, timeout: float) -> _Response:
        raise RemoteDisconnected("simulated disconnect")

    with pytest.raises(RuntimeError, match="模型调用失败"):
        DeepSeekGenerator(api_key="test-key", opener=failing_opener).generate(
            message="你好", context_snapshot={"purpose": "CHAT"}
        )
