# B0 Dependency Inventory

The application lockfile is the authoritative resolved dependency graph. This inventory records direct development dependencies at the B0 baseline; it does not replace the lockfile or an SBOM generated at release time.

| Component | Locked version | Purpose | License source | Removal |
| --- | ---: | --- | --- | --- |
| Python `jsonschema` | `>=4.25,<5` | Contract validation | Package metadata at install time | Remove from `requirements-dev.txt` if the validator is replaced. |
| Python `pytest` | `>=8,<9` | Core tests | Package metadata at install time | Remove from `requirements-dev.txt` if tests are replaced. |
| Vue | 3.5.41 | Family-PWA UI | `node_modules/vue/package.json` | Remove from PWA dependencies. |
| Vue Router | 5.2.0 | Family-PWA routing | `node_modules/vue-router/package.json` | Remove from PWA dependencies. |
| Pinia | 4.0.3 | Family-PWA state | `node_modules/pinia/package.json` | Remove from PWA dependencies. |
| Vite / Vue plugin | 8.2.1 / 6.0.8 | Build and Vue compilation | Respective package metadata | Remove build configuration and dependencies. |
| Vitest / Vue Test Utils / jsdom | 4.1.10 / 2.4.11 / 30.0.1 | Browser-unit testing | Respective package metadata | Remove test setup and dependencies. |
| Playwright | 1.62.1 | End-to-end browser checks | `node_modules/@playwright/test/package.json` | Remove E2E configuration and dependency. |
| vite-plugin-pwa | 1.3.0 | PWA manifest and service worker | `node_modules/vite-plugin-pwa/package.json` | Remove PWA plugin configuration. |

No new dependency is installed by this B0 change. `tools/bootstrap-d.ps1 -Install` keeps all installation caches and browser binaries on D:. A release-phase SBOM must derive exact transitive licenses from the frozen lockfile in CI.
