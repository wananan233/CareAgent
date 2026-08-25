"""GSC-01～07 连续三轮编排；每轮使用独立 Synthetic BFF 进程。"""
from __future__ import annotations
import json, os, subprocess, time, uuid
from pathlib import Path

TOKENS = {"CAREHUB_I0_ELDER_A_TOKEN":"i0-elder-a", "CAREHUB_I0_FAMILY_A_TOKEN":"i0-family-a", "CAREHUB_I0_ELDER_B_TOKEN":"i0-elder-b", "CAREHUB_I0_FAMILY_B_TOKEN":"i0-family-b"}

def run() -> int:
    root = Path("artifacts/i0/repeat"); root.mkdir(parents=True, exist_ok=True); rounds=[]
    for index in range(1, 4):
        port = 8090 + index; env={**os.environ, **TOKENS, "CAREHUB_I0_BFF_PORT":str(port), "CAREHUB_I0_TEST_SEED":"LOW", "CAREHUB_I0_BFF_URL":f"http://127.0.0.1:{port}"}
        child = subprocess.Popen(["python","-u","-m","scripts.run_i0_bff"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            time.sleep(.5)
            result = subprocess.run(["python","-m","scripts.run_gsc_i0"], env=env, capture_output=True, text=True, check=True)
            summary = json.loads(result.stdout.strip().splitlines()[-1]); gsc06 = subprocess.run(["python","-m","scripts.run_gsc06_reconcile"], env=env, capture_output=True, text=True, check=True)
            gsc06_summary = json.loads(gsc06.stdout.strip().splitlines()[-1]); rounds.append({"round":index,"gsc":summary,"gsc06":gsc06_summary})
        finally:
            child.terminate(); child.wait(timeout=3)
    output=root / f"repeat-{uuid.uuid4().hex[:10]}.json"; output.write_text(json.dumps({"rounds":rounds},ensure_ascii=False,indent=2)+"\n"); print(json.dumps({"artifact":str(output),"rounds":len(rounds)},ensure_ascii=False)); return 0

if __name__ == "__main__": raise SystemExit(run())
