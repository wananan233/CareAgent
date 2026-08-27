# CareHub 2.0 I0 网页端联调进度

## 代码基线

- 分支：`main`
- HEAD：生产 Mock 构建隔离修复检查点。
- 已固化授权、BFF/CORS、合成 protected BFF launcher 与双端真实 HTTP contract 修复。

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
- `python -m scripts.run_i0_bff` 可用四个仅由当前进程环境注入的独立 Token 启动两家庭合成 protected BFF；readiness 会验证 `family-a` 可见 `household:i0-a`。
- BFF 统一按 segment 单次解码 URL；前端保留 `encodeURIComponent`。编码 ID 与未编码 ID 读取语义一致，跨家庭编码路径仍由 PDP 拒绝。
- 共享 ephemeral-port harness 已让 Elder/Family `CoreApiAdapter` 经真实 HTTP 调用 Python BFF；测试中不以 fetch mock 替代。

## 网页端配置（浏览器联调待运行）

```text
VITE_CAREHUB_BFF_URL=http://127.0.0.1:8081
VITE_CAREHUB_TOKEN=<仅当前进程注入的演示 Token>
VITE_CAREHUB_HOUSEHOLD_ID=household:synthetic-i0
```

不要设置 `VITE_DEMO_MODE=mock`。不得将 Token、DeepSeek API Key 或其他模型密钥写入仓库、浏览器 bundle、日志或截图。

## 未运行与阻塞

- 已使用锁定的 `pnpm 9.15.4`：老人端类型检查、96 个单测与构建通过；家属端 32 个单测与构建通过。
- Real HTTP contracts：PASS。Family 7 条、Elder 11 条通过，覆盖受保护读取、命令、relinquish/self revoke、401、403、409、422、真实 BFF 503、CORS、本地网络不可达及真实延迟触发的 Adapter timeout/cancel。503/延迟故障仅通过合成 BFF 子进程环境注入，默认关闭且不暴露给浏览器。
- Browser Network：ACCEPTED。真实浏览器已验证双端 scoped GET、Family relinquish、401/403/409/422 ErrorEnvelope、503 correlation_id UI 展示及 CORS exposed correlation header；未发现 silent Mock fallback。
- GSC 首轮：GSC-01/02/03/04/05/07 PASS；GSC-06 通过独立 stop/restart 对账 runner PASS。GSC-03 证据：`artifacts/i0/gsc-01/gsc-20260825T160540Z-7f7069ba/evidence.json`；GSC-06 证据：`artifacts/i0/gsc-06/gsc-06-5a84ca8dfa/evidence.json`。
- GSC ×3：三轮均独立 reset Synthetic BFF；GSC-01/02/03/04/05/07 与独立 GSC-06 均 PASS。汇总：`artifacts/i0/repeat/repeat-a0207a8f99.json`。
- 生产构建 Mock 泄漏检查：PASS。Elder/Family production dist 均不含 `MockCoreAdapter`、Mock 故障类型、fixture Agent、DeepSeek 密钥名或 Token 值；开发/测试仍通过构建期别名使用 Mock，生产入口使用禁用桩且不会静默回落。
- I0-05 故障演示：已有 GSC-06 stop/restart 对账证据；最终双端 outage 证据包待收口。
- 尚未运行真实 DeepSeek；未读取或设置 `DEEPSEEK_API_KEY`。
- 双端 BFF outage：PASS；同端口 stop/restart、自动 GET 恢复、零 command 自动重放均已由真实测试覆盖。

## I0 验收矩阵

| 项目 | 结果 | 证据 |
| --- | --- | --- |
| Elder → BFF | PASS（真实 HTTP） | 9 条真实 Adapter ↔ BFF 合约测试 |
| Family → BFF | PASS（真实 HTTP） | 7 条真实 Adapter ↔ BFF 合约测试 |
| Auth | PASS（合约层） | 四独立 Token、401 与 cross-household 403 |
| Scope isolation | PASS（合约层） | 编码路径、跨 household、SELF revoke 与 family relinquish |
| Controlled command | PASS（合约层） | 双端真实 JSON POST 与命令回执 |
| Idempotency | PASS | 后端测试 |
| Consent revoke | PASS（合约层） | SELF revoke 与 Family relinquish 后下一次读取拒绝 |
| Real HTTP contracts | PASS | Family 7 条、Elder 11 条，完整回归通过 |
| Browser Network | ACCEPTED | 双端真实浏览器请求、Family relinquish、错误映射与 correlation_id |
| Agent citations | PASS | 后端测试 |
| DeepSeek real provider | NOT RUN | 未配置进程密钥 |
| BFF outage | PASS | Elder/Family 同端口真实 stop/restart 自动 GET 恢复；`artifacts/i0/final/manifest.json` |
| Mock bundle leakage | PASS | 两端 production dist 静态扫描 |

## 建议修复顺序

1. **P1**：收口双端 BFF outage evidence manifest 与回滚材料。
2. **P1**：在允许本地监听的 Linux 环境重跑 Python socket 回归并归档完整结果。
3. **P2**：DeepSeek/A0 仍未运行。
