"""I0 本地受保护 BFF：仅内存合成数据，演示 Token 只来自当前进程环境。"""
from __future__ import annotations

import os
from typing import Mapping

from carehub.bff import CareBff, serve_bff_local
from carehub.core.scenario import ScenarioService
from carehub.core.service import CareCore
from carehub.g2 import StaticTokenAuthenticator
from carehub.g3 import ConsentLedger

TENANT = "tenant:i0-demo"
HOUSEHOLDS = (("household:i0-a", "user:elder-a", "user:family-a"), ("household:i0-b", "user:elder-b", "user:family-b"))


def build(tokens: Mapping[str, str]) -> CareBff:
    required = {"elder_a": "user:elder-a", "family_a": "user:family-a", "elder_b": "user:elder-b", "family_b": "user:family-b"}
    if set(tokens) != set(required) or not all(tokens.values()) or len(set(tokens.values())) != len(tokens):
        raise ValueError("必须提供四个互不相同的 I0 演示 Token")
    core = CareCore(":memory:")
    for index, (household, elder, family) in enumerate(HOUSEHOLDS, 1):
        for actor, role in ((elder, "SELF"), (family, "FAMILY")):
            core.store.register_scope(tenant_id=TENANT, household_id=household, subject_id=elder, principal_id=actor, role=role)
            ledger = ConsentLedger(core.store)
            for scope, purpose, channel in (("view", "view", "TERMINAL"), ("view", "stream", "SSE"), ("agent_view", "DAILY_SUMMARY", "TERMINAL")):
                consent = ledger.grant(owner=elder, grantee=actor, household_id=household, scope=scope, purpose=purpose, channel=channel, tenant_id=TENANT)
                ledger.activate(consent["consent_id"], actor=elder, expected_version=1)
        scenario = ScenarioService(core)
        scenario.run(scenario="DOSE", seed=index, tenant_id=TENANT, household_id=household, subject_id=elder)
        scenario.run(scenario="SAFETY", seed=index, tenant_id=TENANT, household_id=household, subject_id=elder)
    return CareBff(core=core, authenticator=StaticTokenAuthenticator({tokens[name]: actor for name, actor in required.items()}, tenant_id=TENANT))


if __name__ == "__main__":
    tokens = {"elder_a": os.environ.get("CAREHUB_I0_ELDER_A_TOKEN", ""), "family_a": os.environ.get("CAREHUB_I0_FAMILY_A_TOKEN", ""), "elder_b": os.environ.get("CAREHUB_I0_ELDER_B_TOKEN", ""), "family_b": os.environ.get("CAREHUB_I0_FAMILY_B_TOKEN", "")}
    port = int(os.environ.get("CAREHUB_I0_BFF_PORT", "8081"))
    origins = tuple(item for item in os.environ.get("CAREHUB_I0_ALLOWED_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173").split(",") if item)
    test_fault_status = int(os.environ["CAREHUB_I0_TEST_FAULT_STATUS"]) if os.environ.get("CAREHUB_I0_TEST_FAULT_STATUS") else None
    test_delay_seconds = float(os.environ.get("CAREHUB_I0_TEST_DELAY_SECONDS", "0"))
    bff = build(tokens); server = serve_bff_local(bff, port=port, allowed_origins=origins, test_fault_status=test_fault_status, test_delay_seconds=test_delay_seconds)
    print(f"I0 BFF: http://127.0.0.1:{port}; household:i0-a/user:elder-a", flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close(); bff.core.close()
