# B0 Blocking Evidence and Decision Register

Status at 2026-08-25: **READY FOR REVIEW**. This register intentionally distinguishes missing inputs from completed code.

| ID | Owner | Status | Required resolution | Blocks |
| --- | --- | --- | --- | --- |
| D-B0-01 | 项目负责人 | RESOLVED | 老人端已随 GitHub `main` 的提交 `2146419721007d6c65f96d2634a87d997cd4bdc0` 交付至 `apps/elder-terminal`，包含 lockfile、README、测试和构建命令。 | — |
| D-B0-02 | 技术负责人 | RESOLVED | GitHub `https://github.com/wananan233/CareAgent.git` 的 `main` 确认为当前单仓库规范主线。 | — |
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

- Completed locally: fixed direct dependency versions; D: bootstrap/verification scripts; baseline manifest; canonical monorepo confirmation; Python contracts/tests; family and elderly terminal unit tests; elderly terminal typecheck and production build.
- Remaining review evidence: a green GitHub Actions run on the canonical commit, including both terminals' E2E suites.
- Rollback: use `baseline.json` 的 `baseline_commit` 在独立干净检出中回退；保留当前工作区。
