"""G1 投影到 G2 聊天快照的端到端模拟器测试。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from carehub.core.service import CareCore
from carehub.g2 import ChatService
from carehub.simulators.devices import DeviceSimulator


class _ContextCapturingGenerator:
    def __init__(self) -> None:
        self.context: dict | None = None

    def generate(self, *, message: str, context_snapshot: dict, history: tuple = ()) -> dict:
        self.context = context_snapshot
        return {
            "message": "我已根据授权的模拟状态整理提醒和告警。",
            "facts": [],
            "fallback": "NONE",
            "generator_version": "context-test.v1",
        }


def test_simulator_events_become_authorized_chat_facts(tmp_path) -> None:
    core = CareCore(tmp_path / "g1-g2.db")
    simulator = DeviceSimulator()
    core.ingest(simulator.medication_due("morning", 1))
    core.ingest(simulator.event("safe-01", 1, "SMOKE_DETECTED"))
    snapshot = core.build_chat_context(
        subject_id="user:synthetic-01",
        consent_expires_at=(datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
    )
    generator = _ContextCapturingGenerator()
    response = ChatService(generator).respond(message="我现在有什么情况？", context_snapshot=snapshot)
    core.close()

    assert response["fallback"] == "NONE"
    assert {fact["text"] for fact in snapshot["facts"]} == {
        "活动安全告警：SMOKE_GAS，安全等级 S-1。",
        "服药任务 task:morning 当前状态：DUE；证据状态：UNKNOWN。",
    }
    assert snapshot["unknowns"] == [
        {"field": "medication_evidence:task:morning", "reason": "UNKNOWN"}
    ]
    assert generator.context == snapshot
    assert all(ref in snapshot["source_event_ids"] for fact in snapshot["facts"] for ref in fact["source_refs"])


def test_chat_context_never_mixes_subjects_or_households(tmp_path) -> None:
    core = CareCore(tmp_path / "tenant-context.db")
    alice = DeviceSimulator(subject_id="user:alice", household_id="household:home-a")
    bob = DeviceSimulator(subject_id="user:bob", household_id="household:home-b")
    core.ingest(alice.medication_due("morning", 1))
    core.ingest(bob.event("safe-b", 1, "SMOKE_DETECTED"))

    snapshot = core.build_chat_context(
        subject_id="user:alice",
        household_id="household:home-a",
        consent_expires_at=(datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
    )
    core.close()

    assert [fact["text"] for fact in snapshot["facts"]] == [
        "服药任务 task:morning 当前状态：DUE；证据状态：UNKNOWN。"
    ]
    assert all("SMOKE_GAS" not in fact["text"] for fact in snapshot["facts"])
