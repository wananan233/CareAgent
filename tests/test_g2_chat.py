"""G2 受控基础聊天测试。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from carehub.g2.chat import ChatService, ChatSession, _canonical_hash, build_context_snapshot


def _snapshot() -> dict:
    return build_context_snapshot(
        subject_id="user:synthetic-01",
        source_event_ids=["evt-synthetic-01"],
        consent_scopes=["chat"],
        consent_expires_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        unknowns=[{"field": "medication_evidence", "reason": "NOT_RECORDED"}],
    )


def test_chat_returns_structured_template_response_without_side_effects() -> None:
    response = ChatService().respond(message="我现在有什么提醒？", context_snapshot=_snapshot())

    assert response["schema_version"] == "AgentResponseV1"
    assert response["channel"] == "TERMINAL"
    assert response["fallback"] == "TEMPLATE_FALLBACK"
    assert response["facts"] == []
    assert "提醒" in response["message"]


class _SourcedGenerator:
    def generate(self, *, message: str, context_snapshot: dict, history: tuple = ()) -> dict:
        return {
            "message": "您有一条待确认的提醒。",
            "facts": [{"text": "提醒状态待确认", "source_refs": ["evt-synthetic-01"]}],
            "fallback": "NONE",
            "generator_version": "test-generator.v1",
        }


def test_chat_accepts_facts_within_snapshot_provenance() -> None:
    response = ChatService(_SourcedGenerator()).respond(message="提醒状态", context_snapshot=_snapshot())

    assert response["facts"] == [{"text": "提醒状态待确认", "source_refs": ["evt-synthetic-01"]}]


class _UntrustedGenerator:
    def generate(self, *, message: str, context_snapshot: dict, history: tuple = ()) -> dict:
        return {
            "message": "我已操作设备。",
            "facts": [{"text": "未经授权的事实", "source_refs": ["evt-not-authorized"]}],
            "fallback": "NONE",
            "generator_version": "test-generator.v1",
            "action_intent": {"capability": "gpio_control"},
        }


def test_chat_rejects_facts_outside_authorized_snapshot() -> None:
    with pytest.raises(ValueError, match="来源事件"):
        ChatService(_UntrustedGenerator()).respond(message="执行操作", context_snapshot=_snapshot())


class _ActionDraftGenerator:
    def generate(self, *, message: str, context_snapshot: dict, history: tuple = ()) -> dict:
        return {
            "message": "我只能提供信息，不能执行设备操作。",
            "facts": [],
            "fallback": "NONE",
            "generator_version": "test-generator.v1",
            "action_intent": {"capability": "gpio_control"},
        }


def test_chat_drops_model_action_fields_from_final_response() -> None:
    response = ChatService(_ActionDraftGenerator()).respond(message="开门", context_snapshot=_snapshot())

    assert "action_intent" not in response
    assert set(response) == {
        "schema_version",
        "response_id",
        "agent_run_id",
        "channel",
        "message",
        "facts",
        "fallback",
        "generator_version",
    }


def test_chat_rejects_non_chat_snapshot_and_invalid_input() -> None:
    snapshot = _snapshot()
    snapshot["purpose"] = "DAILY_SUMMARY"
    snapshot["hash"] = _canonical_hash({key: value for key, value in snapshot.items() if key != "hash"})

    with pytest.raises(ValueError, match="purpose=CHAT"):
        ChatService().respond(message="你好", context_snapshot=snapshot)
    with pytest.raises(ValueError, match="1 到 500"):
        ChatService().respond(message="", context_snapshot=_snapshot())


def test_chat_rejects_tampered_context_snapshot() -> None:
    snapshot = _snapshot()
    snapshot["consent"]["scopes"] = ["chat", "tampered"]

    with pytest.raises(ValueError, match="哈希不匹配"):
        ChatService().respond(message="你好", context_snapshot=snapshot)


def test_chat_requires_unexpired_chat_consent() -> None:
    no_chat_scope = _snapshot()
    no_chat_scope["consent"]["scopes"] = ["daily_summary"]
    no_chat_scope["hash"] = _canonical_hash(
        {key: value for key, value in no_chat_scope.items() if key != "hash"}
    )
    with pytest.raises(ValueError, match="chat 同意范围"):
        ChatService().respond(message="你好", context_snapshot=no_chat_scope)

    expired = build_context_snapshot(
        subject_id="user:synthetic-01",
        source_event_ids=["evt-synthetic-01"],
        consent_scopes=["chat"],
        consent_expires_at=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
    )
    with pytest.raises(ValueError, match="同意已过期"):
        ChatService().respond(message="你好", context_snapshot=expired)


class _HistoryGenerator:
    def __init__(self) -> None:
        self.received_history: list[tuple[dict[str, str], ...]] = []

    def generate(self, *, message: str, context_snapshot: dict, history: tuple[dict[str, str], ...] = ()) -> dict:
        self.received_history.append(history)
        return {
            "message": f"已收到：{message}",
            "facts": [],
            "fallback": "NONE",
            "generator_version": "history-test.v1",
        }


def test_chat_session_keeps_only_recent_turns_in_memory() -> None:
    generator = _HistoryGenerator()
    session = ChatSession(ChatService(generator), _snapshot(), max_turns=2)

    session.ask("第一句")
    session.ask("第二句")
    session.ask("第三句")

    assert generator.received_history[0] == ()
    assert generator.received_history[2] == (
        {"role": "user", "content": "第一句"},
        {"role": "assistant", "content": "已收到：第一句"},
        {"role": "user", "content": "第二句"},
        {"role": "assistant", "content": "已收到：第二句"},
    )
    assert session.history == (
        {"role": "user", "content": "第二句"},
        {"role": "assistant", "content": "已收到：第二句"},
        {"role": "user", "content": "第三句"},
        {"role": "assistant", "content": "已收到：第三句"},
    )
