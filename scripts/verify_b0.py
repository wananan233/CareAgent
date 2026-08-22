"""B0 baseline checks that must stay explicit until the elder terminal arrives."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FAMILY_FILES = (
    "apps/family-pwa/package.json",
    "apps/family-pwa/README.md",
    "apps/shared-contracts/package.json",
    "pnpm-workspace.yaml",
    "pnpm-lock.yaml",
)
REQUIRED_ELDER_FILES = (
    "apps/elder-terminal/package.json",
    "apps/elder-terminal/README.md",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-elder-terminal", action="store_true")
    args = parser.parse_args()

    missing = [path for path in REQUIRED_FAMILY_FILES if not (ROOT / path).is_file()]
    manifest = json.loads((ROOT / "baseline.json").read_text(encoding="utf-8"))
    if manifest["b0_status"] not in {"BLOCKED", "READY_FOR_REVIEW"}:
        missing.append("baseline.json has an invalid b0_status")

    elder_missing = [path for path in REQUIRED_ELDER_FILES if not (ROOT / path).is_file()]
    if args.require_elder_terminal and elder_missing:
        missing.extend(elder_missing)

    if missing:
        print("B0 verification failed; missing or invalid:")
        print("\n".join(f"- {path}" for path in missing))
        if elder_missing:
            print("Elder-terminal source is a B0 blocker; see docs/B0_BLOCKERS.md.")
        return 1

    print("B0 file-presence checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
