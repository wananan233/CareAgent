"""以合成、已授权事实验证 DeepSeek G4 双 purpose 边界。"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from carehub.core.event_store import EventStore
from carehub.g3 import AuthContext, ConsentLedger, ServerSidePDP
from carehub.g4 import AgentOrchestrator, create_model_gateway_from_env


TENANT_ID = "tenant:g4-smoke"
HOUSEHOLD_ID = "household:g4-smoke"
SUBJECT_ID = "user:g4-smoke"
FACTS = [
    {"text": "MEDICATION_DUE 于 2026-08-27T09:00:00+08:00 记录，证据状态为 UNKNOWN。", "source_refs": ["evt-g4-smoke-1"]},
]
PURPOSES = ("TODAY_STATUS", "DAILY_SUMMARY", "WEEKLY_TREND", "CHANGE_EXPLANATION", "READ_ONLY_QA")


def main() -> None:
    gateway = create_model_gateway_from_env()
    if gateway.provider.__class__.__name__ != "DeepSeekProvider":
        raise RuntimeError("请以 CAREHUB_MODEL_PROVIDER=deepseek 运行本 smoke")

    with TemporaryDirectory(prefix="carehub-g4-deepseek-") as directory:
        store = EventStore(Path(directory) / "smoke.db")
        try:
            store.register_scope(tenant_id=TENANT_ID, household_id=HOUSEHOLD_ID, subject_id=SUBJECT_ID,
                                 principal_id=SUBJECT_ID, role="SELF")
            ledger = ConsentLedger(store)
            for purpose in PURPOSES:
                consent = ledger.grant(owner=SUBJECT_ID, grantee=SUBJECT_ID, household_id=HOUSEHOLD_ID,
                                       scope="agent_view", purpose=purpose, tenant_id=TENANT_ID)
                ledger.activate(consent["consent_id"], actor=SUBJECT_ID, expected_version=1)

            agent = AgentOrchestrator(store, ServerSidePDP(store, ledger), gateway=gateway)
            for purpose in PURPOSES:
                response = agent.run(context=AuthContext(SUBJECT_ID, TENANT_ID), household_id=HOUSEHOLD_ID,
                                     subject_id=SUBJECT_ID, purpose=purpose,
                                     minimal_context={"facts": FACTS, "question": "今天有哪些已授权记录？"} if purpose == "READ_ONLY_QA" else {"facts": FACTS})
                run = store.agent_run(response["agent_run_id"])
                if response["fallback"] != "NONE" or response["facts"] == []:
                    raise RuntimeError(f"{purpose} 未获得受控模型响应：{response['reason_code']}")
                if any(ref not in FACTS[0]["source_refs"] for fact in response["facts"] for ref in fact["source_refs"]):
                    raise RuntimeError(f"{purpose} 返回了未授权 source_refs")
                if not run or run["status"] != "COMPLETED" or run["source_refs"] != FACTS[0]["source_refs"]:
                    raise RuntimeError(f"{purpose} AgentRun 校验失败")
                print(json.dumps({"purpose": purpose, "fallback": response["fallback"],
                                  "generator_version": response["generator_version"],
                                  "source_ref_count": len(run["source_refs"]), "agent_run_status": run["status"]},
                                 ensure_ascii=False))
        finally:
            store.close()


if __name__ == "__main__":
    main()
