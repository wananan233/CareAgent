# CareHub 2.0 I0 自动执行规则

## 开始与边界

每次开始 I0 工作必须先执行 `git status`、`git log -5 --oneline`，并阅读本文件与 `docs/I0_WEB_PROGRESS.md`，据此确定下一个未完成 Gate。不得跳过 Gate。

禁止为通过测试放宽 PDP、恢复 SELF 隐式授权、使用万能 Token、使用 `Access-Control-Allow-Origin: *`、移除前端 `encodeURIComponent()`，或以 Mock/Fake 冒充真实联调。

## Gate 顺序

1. Synthetic protected BFF
2. Real HTTP Adapter ↔ BFF contract
3. Browser Network
4. GSC-01～07
5. Failure injection / outage
6. DeepSeek / A0
7. I0 acceptance
8. Q0
9. R0

当前 Gate 未通过前，不得开始下一项。

## 当前 Gate：Real HTTP Adapter ↔ BFF contract

必须用 TypeScript `CoreApiAdapter` 对本地真实 Python BFF 发起 HTTP 请求；不得以 fetch mock 替代。

Family 与 Elder 均须覆盖 dashboard、tasks、alerts、timeline、report、受控命令和 consent revoke。至少覆盖 Authorization、household/subject scoped URL、consent envelope/version、correlation_id、401/403/409/422/503、CORS allowed/rejected Origin、网络失败、超时及跨家庭隔离。

`apps/test-support/i0Bff.ts` 必须使用动态端口、四个仅通过子进程环境注入的 Token、带认证 readiness 轮询和总超时，并在成功或失败后可靠终止子进程。不得输出 Token。

## 每阶段验证

```bash
python -m scripts.validate_contracts
python -m pytest -q
corepack pnpm@9.15.4 --filter @carehub/elder-terminal typecheck
corepack pnpm@9.15.4 --filter @carehub/elder-terminal test
corepack pnpm@9.15.4 --filter @carehub/elder-terminal build
corepack pnpm@9.15.4 --filter @carehub/family-pwa test
corepack pnpm@9.15.4 --filter @carehub/family-pwa build
```

以 `package.json` 实际脚本为准；未运行项目必须标记 `NOT RUN`。

## Git 与停止

每个稳定 Gate：检查 diff 和 secret、提交、推送 `origin main`、确认 `main...origin/main`，再更新 `docs/I0_WEB_PROGRESS.md`。

Real HTTP contract 全部通过后停止开发并汇报，等待用户确认后才能进入 Browser Network。

## 汇报格式

只汇报修复、新增、根因、commit/push、Python/Elder/Family/Real HTTP/CORS/Cross-household 结果、当前 Gate 与下一 Gate。失败时补充 failing test、HTTP status/error、correlation_id、已排除原因和下一定位点。
