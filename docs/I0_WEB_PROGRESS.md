# CareHub 2.0 I0 网页端联调进度

## 代码基线

- 分支：`main`
- HEAD：`e918278`（提交后将更新）
- 已固化授权、BFF/CORS 与双端 Adapter 修复；Synthetic launcher 与 HTTP contract tests 尚未开始。

## 已确认通过

- `python -m scripts.validate_contracts` 通过。
- `python -m pytest -q`：`317 passed, 3 skipped`。
- BFF 后端测试已覆盖受保护读取、JSON POST 命令转发、命令幂等、Agent 来源引用和 consent 撤销接口。
- 老人端已有真实 BFF Adapter；生产环境缺少 BFF 配置会失败，不会静默切换 Mock。

## 真实联调结论

- BFF 已具备 dashboard、tasks、alerts、timeline、日报 Agent、受控确认命令和按 scope 撤销 consent 的路由。
- Agent 报告由已授权时间线构造事实，`facts` 包含 `source_refs`；“已看到提醒”不等于“已服药”。
- SELF consent 撤销已修复：撤销后 dashboard、tasks、alerts、timeline、report 与 SSE 的下一次读取均拒绝。
- BFF 已支持显式 Origin 白名单的 OPTIONS/CORS 预检；不使用通配符 Origin。
- 双端 Adapter 已对齐 BFF scoped 写路由、consent envelope 与 PDP 错误映射。
- 当前没有可一键启动“受保护 BFF + 内存合成 tenant/household/subject/token/active consent”的脚本。

## 网页端配置（浏览器联调待运行）

```text
VITE_CAREHUB_BFF_URL=http://127.0.0.1:8081
VITE_CAREHUB_TOKEN=<仅当前进程注入的演示 Token>
VITE_CAREHUB_HOUSEHOLD_ID=household:synthetic-i0
```

不要设置 `VITE_DEMO_MODE=mock`。不得将 Token、DeepSeek API Key 或其他模型密钥写入仓库、浏览器 bundle、日志或截图。

## 未运行与阻塞

- 已使用锁定的 `pnpm 9.15.4`：老人端类型检查、96 个单测与构建通过；家属端 32 个单测与构建通过。
- 尚未启动浏览器并检查 Network 面板真实请求。
- 尚未运行真实 DeepSeek；未读取或设置 `DEEPSEEK_API_KEY`。
- 尚未完成 BFF 停止后的双端故障演示。

## I0 验收矩阵

| 项目 | 结果 | 证据 |
| --- | --- | --- |
| Elder → BFF | PASS（单元/构建） | 96 个单测、类型检查与构建通过 |
| Family → BFF | PASS（单元/构建） | 32 个单测与构建通过 |
| Auth | PARTIAL | 后端基础实现存在，网页端未验证 |
| Scope isolation | PARTIAL | 跨 household 测试存在；SELF 撤销绕过 |
| Controlled command | PARTIAL | 后端 JSON POST 与幂等测试通过；网页端未验证 |
| Idempotency | PASS | 后端测试 |
| Consent revoke | PASS（代码/回归） | SELF 撤销后 BFF、Agent 与 SSE 均拒绝 |
| Agent citations | PASS | 后端测试 |
| DeepSeek real provider | NOT RUN | 未配置进程密钥 |
| BFF outage | NOT RUN | 未完成双端故障演示 |

## 建议修复顺序

1. **P1**：补充内存合成 BFF 启动脚本，Token 只由 Linux 进程环境提供。
2. **P1**：增加双端真实 HTTP Adapter ↔ BFF 契约测试。
3. **P2**：完成浏览器 Network、BFF outage 与 GSC-01～07 联调。
