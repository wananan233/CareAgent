# B0 Blocking Evidence and Decision Register

Status at 2026-08-22: **BLOCKED**. This register intentionally distinguishes missing inputs from completed code.

| ID | Owner | Status | Required resolution | Blocks |
| --- | --- | --- | --- | --- |
| D-B0-01 | 项目负责人 | OPEN | Provide the elderly-terminal repository URL, branch and immutable commit (or add its source under `apps/elder-terminal` with lockfile, tests and README). | B0, E0 |
| D-B0-02 | 技术负责人 | OPEN | Select the canonical single/multi-repository model and release branch. | B0 |
| D-G0-01 | 医疗 / 产品 | OPEN | Approve medication deferral and escalation rules. | Real medication integration |
| D-G0-02 | 安全 / 产品 | OPEN | Approve immobility and no-response escalation rules. | Real alert integration |
| D-G0-03 | Medication owner | OPEN | Approve medication-evidence conflict matrix. | Real medication evidence |
| D-G0-04 | 法务 / 合规 | OPEN | Approve anthropomorphic AI boundary and data rights. | Production model/productization |
| D-C1-01 | 安全 / 技术 | OPEN | Select demo identity provider and token lifetime. | C1, C2 |
| D-R0-01 | 项目 / 隐私 | OPEN | Select demo deployment target and data-retention period. | R0 |
| D-X0-01 | 项目负责人 | OPEN | Select Android package, minSdk, signing and AAB requirement. | X0 |

## Elder-terminal re-delivery checklist

The elderly-terminal handoff must include source code, lockfile, automated tests, README, a reproducible build command, and the exact source commit. A screenshot, document preview or APK without the corresponding source does not satisfy B0-01.

## B0 review record

- Completed locally: fixed direct dependency versions; CI now covers Python contracts/tests and the tracked family PWA; D: bootstrap/verification scripts; baseline manifest; decision register.
- Not complete: source-control commit/tag of the existing dirty worktree, elderly-terminal handoff, canonical repository decision, and a green CI run containing the elderly-terminal checks.
- Rollback: use the baseline commit in `BASELINE.md` in a separate clean checkout. Preserve this worktree.
