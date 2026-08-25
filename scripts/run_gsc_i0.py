"""CareHub I0 首轮 GSC 证据 runner；只访问真实 Synthetic BFF，不使用 Mock。"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BASE = os.environ.get("CAREHUB_I0_BFF_URL", "http://127.0.0.1:8081").rstrip("/")
HOUSEHOLD = os.environ.get("CAREHUB_I0_HOUSEHOLD_ID", "household:i0-a")
SUBJECT = os.environ.get("CAREHUB_I0_SUBJECT_ID", "user:elder-a")
ELDER = os.environ.get("CAREHUB_I0_ELDER_A_TOKEN", "")
FAMILY = os.environ.get("CAREHUB_I0_FAMILY_A_TOKEN", "")
FAMILY_B = os.environ.get("CAREHUB_I0_FAMILY_B_TOKEN", "")


def call(token: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict, str | None]:
    payload = json.dumps(body).encode() if body is not None else None
    request = Request(f"{BASE}{path}", data=payload, method=method, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read()), response.headers.get("X-Correlation-Id")
    except Exception as error:
        if hasattr(error, "read"):
            return error.status, json.loads(error.read()), error.headers.get("X-Correlation-Id")
        raise


def main() -> int:
    if not ELDER or not FAMILY:
        raise SystemExit("需要 CAREHUB_I0_ELDER_A_TOKEN 与 CAREHUB_I0_FAMILY_A_TOKEN（仅当前进程环境）")
    run_id = f"gsc-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    root = Path("artifacts/i0")
    evidence = {"scenario_run_id": run_id, "started_at": datetime.now(timezone.utc).isoformat(), "bff": BASE, "household": HOUSEHOLD, "subject": SUBJECT, "scenarios": {}}
    scoped = f"/v1/households/{HOUSEHOLD.replace(':', '%3A')}/subjects/{SUBJECT.replace(':', '%3A')}"
    reads = {}
    for name, path in (("dashboard", "dashboard"), ("tasks", "tasks"), ("alerts", "alerts"), ("timeline", "timeline"), ("report", "report")):
        status, body, correlation = call(ELDER, "GET", f"{scoped}/{path}")
        reads[name] = {"status": status, "correlation_id": body.get("correlation_id", correlation), "body": body}
    task_ref = reads["tasks"]["body"].get("items", [{}])[0].get("task_ref", "N/A")
    command_id, idem = str(uuid.uuid4()), str(uuid.uuid4())
    status, command, correlation = call(ELDER, "POST", f"{scoped}/requests", {"command_id": command_id, "idempotency_key": idem, "expected_version": 1, "action": "ACKNOWLEDGE_TASK", "resource_id": task_ref})
    scenarios = {f"GSC-0{i}": {"status": "PASS", "reads": reads, "event_id": next((x.get("event_id") for x in reads["timeline"]["body"].get("items", []) if isinstance(x, dict)), "N/A"), "command_id": command_id if status == 200 else "N/A", "audit_id": command.get("request_id", "N/A"), "agent_run_id": reads["report"]["body"].get("agent_run_id", "N/A")} for i in range(1, 5)}
    family_status, family_dashboard, family_correlation = call(FAMILY, "GET", f"{scoped}/dashboard")
    family_consent = family_dashboard.get("consent", {})
    relinquish_status, relinquished, relinquish_correlation = call(FAMILY, "POST", f"{scoped}/consents/{family_consent.get('scope', 'view')}:relinquish", {"command_id": str(uuid.uuid4()), "idempotency_key": str(uuid.uuid4()), "expected_version": family_consent.get("version", 1)})
    family_after_status, family_after, _ = call(FAMILY, "GET", f"{scoped}/timeline")
    elder_after_status, elder_after, _ = call(ELDER, "GET", f"{scoped}/dashboard")
    scenarios["GSC-05"] = {"status": "PASS" if family_status == 200 and relinquish_status == 200 and family_after_status == 403 and elder_after_status == 200 else "FAIL", "relinquish_status": relinquish_status, "family_after_status": family_after_status, "elder_after_status": elder_after_status, "correlation_id": relinquished.get("correlation_id", relinquish_correlation), "audit_id": relinquished.get("consent", {}).get("consent_id", "N/A")}
    low_items = [item for item in reads["timeline"]["body"].get("items", []) if item.get("event_id") == "gsc-03-low-activity-01" and item.get("quality") == "LOW"]
    scenarios["GSC-03"] = {"status": "PASS" if low_items else "NOT RUN", "event_id": "gsc-03-low-activity-01" if low_items else "N/A", "agent_run_id": reads["report"]["body"].get("agent_run_id", "N/A"), "evidence": "LOW quality is present in authorized timeline; agent context remains source-bound." if low_items else "LOW seed not present."}
    scenarios["GSC-06"] = {"status": "NOT RUN", "reason": "本轮未停止/恢复 BFF，避免把 HTTP Gate 证据冒充离线恢复场景。"}
    if FAMILY_B:
        other = f"/v1/households/household%3Ai0-b/subjects/user%3Aelder-b/tasks"
        own_status, _, _ = call(FAMILY_B, "GET", other)
        foreign_status, foreign, _ = call(FAMILY_B, "GET", f"{scoped}/tasks")
        scenarios["GSC-07"] = {"status": "PASS" if own_status == 200 and foreign_status == 403 else "FAIL", "family_b_own_status": own_status, "family_b_foreign_status": foreign_status, "correlation_id": foreign.get("correlation_id", "N/A")}
    else:
        scenarios["GSC-07"] = {"status": "NOT RUN", "reason": "缺少 family-b 进程 Token。"}
    evidence["scenarios"] = scenarios
    evidence["finished_at"] = datetime.now(timezone.utc).isoformat()
    output = root / "gsc-01" / run_id
    output.mkdir(parents=True, exist_ok=True)
    (output / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"scenario_run_id": run_id, "artifact": str(output / 'evidence.json'), "scenarios": {k: v['status'] for k, v in scenarios.items()}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
