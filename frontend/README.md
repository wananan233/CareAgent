# CareHub 2.0

纯软件、纯合成数据的养老看护演示项目。老人端（`apps/elder-terminal`）为面向老年人的
大屏 PWA；`apps/shared-contracts` 为双端共享的版本化 DTO、运行时 guard 与 mock builders；
`contracts/*.schema.json` 为声明式契约事实源。

> 当前阶段（E0–E6）已完成并通过验收；真实 Core/BFF 接入属后续 C0–C4 阶段，
> 现唯一数据源为 `MockCoreAdapter`（合成数据），界面全局携带“模拟数据”标识。

## 一键启动

```bash
npm install     # 安装（首次）
npm run dev     # 启动老人端 dev server → http://localhost:5173
```

其他命令：

```bash
npm run build        # 类型检查 + 生产构建（产出 apps/elder-terminal/dist/）
npm run test         # 全部工作区单元/组件测试（Vitest）
npm run typecheck    # 仅类型检查
```

端到端测试（Playwright，自动拉起 dev server，需系统 Chrome）：

```bash
cd apps/elder-terminal && npm run test:e2e
```

## 目录

```
apps/elder-terminal/   # 老人端 Vue3/TS/PWA 应用（含测试、README）
apps/shared-contracts/ # 共享 DTO / guard / builders
contracts/             # JSON Schema 契约事实源
docs/                  # ADR、验收报告、版本/回滚、适配器兼容报告、截图
```

## 文档

- [老人端 README](apps/elder-terminal/README.md) — 路由、接口映射、状态矩阵、设计 token、可访问性、已知限制
- [验收报告](docs/acceptance-report.md) — E5-E6 测试结果与截图
- [版本与回滚](docs/version-and-rollback.md) — 版本规则、无 git 时的快照回滚、干净目录复现
- [适配器兼容报告](docs/adapter-compatibility.md) — Mock 与 Core 适配器契约一致性
- [ADR-0001](docs/adr/0001-elder-terminal-scaffold-and-contract-freeze.md) — 工程与契约冻结决策

## 内容红线

所有演示数据 `source.type === 'SIMULATOR'`；禁止把合成数据说成真实健康记录；禁止诊断、
剂量建议、改药、声称“已吞服”；禁止关闭/取消 SOS/烟雾/燃气告警；禁止把无来源数据显示为
事实；日志不落消息正文/身份字段/Token/健康数据，不写 `localStorage/sessionStorage/IndexedDB`。
