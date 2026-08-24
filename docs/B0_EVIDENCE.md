# B0 Local Evidence

Recorded on 2026-08-22 from `D:\he\careagent_repo_review_20260814`.

| Check | Command | Result |
| --- | --- | --- |
| Contract validation | `python -m scripts.validate_contracts` | PASS |
| Core tests | `python -m pytest -q` | PASS: 262 tests |
| Family-PWA unit tests | `pnpm --filter @carehub/family-pwa test` | PASS: 6 files, 15 tests |
| Family-PWA production build | `pnpm --filter @carehub/family-pwa build` | PASS |
| B0 local file gate | `tools/verify.ps1 -SkipTests` | PASS for existing baseline files; it does not approve the elder-terminal handoff |
| Elder-terminal gate | `python -m scripts.verify_b0 --require-elder-terminal` | EXPECTED FAIL: `apps/elder-terminal/package.json` and `README.md` are absent |

The Python run used the existing D: review dependency directory because the bundled runtime does not include the project test packages. The front-end run used a frozen-lockfile installation with npm and pnpm caches directed to D:. No test result above overrides the B0 blocker described in `docs/B0_BLOCKERS.md`.

## Not run locally

- Playwright E2E was not rerun after the lockfile installation because the Chromium binary was not installed in this session. CI installs Chromium explicitly before executing it.
- Elder-terminal typecheck, unit tests, build and E2E cannot run until its source handoff is supplied.
