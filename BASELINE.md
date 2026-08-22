# B0 Baseline Manifest

This manifest freezes the observed starting point for the B0 code-takeover phase. It is not a release tag and does not approve the existing modified worktree for production.

## Source baseline

- Repository: `https://github.com/wananan233/CareAgent.git`
- Observed branch: `main`
- Baseline commit: `99b7dbad0e5f04ed176f131ca6406f2dafe882c4`
- Core source, contracts and the family PWA are co-located in this working tree.
- `apps/elder-terminal` was absent when this baseline was recorded. The exact repository URL, branch and commit must be supplied before B0 can pass.
- The project owner must also choose the canonical single-repository or multi-repository release model.

## Reproducibility policy

Run `tools/bootstrap-d.ps1` from a D: checkout. It places pnpm, npm, pip, Playwright and temporary caches under `.carehub-toolchain/` on D: and stops if the checkout or configured paths resolve elsewhere. Use `-Install` only when installing the locked dependencies and Chromium is intended.

`tools/verify.ps1` validates contracts and B0 file presence, then runs the available Python and family-PWA checks unless `-SkipTests` is supplied. The elder-terminal gate is intentionally separate and must not be waived by a successful family-PWA check.

## Current B0 outcome

`BLOCKED`: the repository contains uncommitted work and the elderly-terminal source is not available. Do not start C0 until D-B0-01 and D-B0-02 are resolved and B0 is reviewed by the project owner.

## Rollback point

Restore a separate clean checkout to commit `99b7dbad0e5f04ed176f131ca6406f2dafe882c4`; do not delete or reset this existing worktree, which contains user changes.
