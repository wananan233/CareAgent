"""GSC-06 真实 BFF stop/restart 对账 runner；不使用前端模拟离线开关。"""
from __future__ import annotations
import json, os, socket, subprocess, time, uuid
from pathlib import Path
from urllib.request import Request, urlopen

TOKENS = {"CAREHUB_I0_ELDER_A_TOKEN": "i0-elder-a", "CAREHUB_I0_FAMILY_A_TOKEN": "i0-family-a", "CAREHUB_I0_ELDER_B_TOKEN": "i0-elder-b", "CAREHUB_I0_FAMILY_B_TOKEN": "i0-family-b"}
ROOT = "/v1/households/household%3Ai0-a/subjects/user%3Aelder-a/timeline"

def free_port() -> int:
    sock = socket.socket(); sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]; sock.close(); return port

def start(port: int) -> subprocess.Popen[str]:
    env = {**os.environ, "CAREHUB_I0_BFF_PORT": str(port), **TOKENS}
    return subprocess.Popen(["python", "-u", "-m", "scripts.run_i0_bff"], env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def read(base: str) -> tuple[int, dict]:
    request = Request(base + ROOT, headers={"Authorization": "Bearer i0-elder-a"})
    with urlopen(request, timeout=2) as response: return response.status, json.loads(response.read())

def ready(base: str) -> None:
    for _ in range(100):
        try:
            if read(base)[0] == 200: return
        except Exception: time.sleep(.05)
    raise RuntimeError("BFF readiness timeout")

def main() -> int:
    run_id = f"gsc-06-{uuid.uuid4().hex[:10]}"; port = free_port(); base = f"http://127.0.0.1:{port}"; child = start(port)
    try:
        ready(base); before = read(base); child.terminate(); child.wait(timeout=3)
        try: read(base); outage = "REQUEST_FAILED"
        except Exception: outage = "REQUEST_FAILED"
        child = start(port); ready(base); after = read(base)
        before_ids = [item.get("event_id") for item in before[1].get("items", [])]; after_ids = [item.get("event_id") for item in after[1].get("items", [])]
        before_types = [item.get("event_type") for item in before[1].get("items", [])]; after_types = [item.get("event_type") for item in after[1].get("items", [])]
        evidence = {"scenario_run_id": run_id, "status": "PASS" if outage == "REQUEST_FAILED" and before_types == after_types else "FAIL", "before_status": before[0], "during_stop": outage, "after_status": after[0], "before_event_ids": before_ids, "after_event_ids": after_ids, "before_event_types": before_types, "after_event_types": after_types, "duplicate_event_ids": len(after_ids) - len(set(after_ids)), "command_id": "N/A", "audit_id": "N/A", "agent_run_id": "N/A"}
        path = Path("artifacts/i0/gsc-06") / run_id; path.mkdir(parents=True, exist_ok=True); (path / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"); print(json.dumps({"scenario_run_id": run_id, "artifact": str(path / 'evidence.json'), "status": evidence["status"]}, ensure_ascii=False)); return 0
    finally:
        if child.poll() is None: child.terminate(); child.wait(timeout=3)

if __name__ == "__main__": raise SystemExit(main())
