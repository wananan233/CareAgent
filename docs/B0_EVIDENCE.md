# B0 Local Evidence

Updated on 2026-08-25 from a clean detached worktree at GitHub `main` commit `2146419721007d6c65f96d2634a87d997cd4bdc0`.

| Check | Command | Result |
| --- | --- | --- |
| Contract validation | `python -m scripts.validate_contracts` | PASS |
| Core tests | `python -m pytest -q` | PASS: 288 tests |
| Family-PWA unit tests | `pnpm --filter @carehub/family-pwa test` | PASS: 8 files, 32 tests |
| Elder-terminal typecheck | `pnpm --filter @carehub/elder-terminal typecheck` | PASS |
| Elder-terminal unit tests | `pnpm --filter @carehub/elder-terminal test` | PASS: 23 files, 95 tests |
| Elder-terminal production build | `pnpm --filter @carehub/elder-terminal build` | PASS |
| Elder-terminal Playwright E2E | `pnpm --filter @carehub/elder-terminal test:e2e` | PASS: 22 tests |
| Family-PWA Playwright E2E | `pnpm --filter @carehub/family-pwa test:e2e` | PASS: 5 tests |
| Elder-terminal source gate | `python -m scripts.verify_b0 --require-elder-terminal` | PASS |

The Python run used the existing D: review dependency directory because the bundled runtime does not include the project test packages. The front-end run used `pnpm install --frozen-lockfile`; Chromium was installed into the D: project tool directory only for E2E validation. The elderly-terminal source handoff and canonical repository decisions are resolved. Release still requires the canonical GitHub Actions run to reproduce this evidence.
