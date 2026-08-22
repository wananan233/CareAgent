# CareHub 2.0 老人端

面向老年人的大屏 PWA 演示端。**纯软件、纯合成数据、无真实硬件**：所有数据来自
`MockCoreAdapter`，界面全局携带“模拟数据”标识，绝不把合成数据渲染成真实健康记录。

技术栈：Vue 3 + TypeScript + Vite 6 + Pinia + Vue Router 4 + 手写 Service Worker（离线壳）。

> 状态：E0–E6 全部完成。真实 Core/BFF 接口（C0–C4）尚未接入，当前唯一数据源为
> `MockCoreAdapter`（`CoreApiAdapter` 全部返回 `NOT_IMPLEMENTED` 占位）。

## 快速开始

```bash
# 在仓库根目录（npm workspaces monorepo）
npm install              # 首次安装
npm run dev              # 启动 dev server（默认 http://localhost:5173）
npm run build            # vue-tsc --noEmit + vite build（产出 dist/）
npm run test             # Vitest 单元/组件测试
npm run test:e2e         # Playwright 端到端测试（自动拉起 dev server）
npm run typecheck        # 仅 vue-tsc 类型检查
```

也可进入本目录单独执行：`npm run dev` / `npm run build` / `npm run test`。

## 目录结构

```
apps/elder-terminal/
├── public/
│   ├── manifest.webmanifest   # PWA 清单（standalone、主题色、中文）
│   └── sw.js                  # 手写离线壳 Service Worker
├── src/
│   ├── components/            # AppShell、NavBar、卡片、状态条、徽标、来源抽屉等
│   ├── composables/           # useNetworkStatus（online/offline 事件）
│   ├── contracts/             # 状态矩阵、显示/错误映射、离线策略
│   ├── pages/                 # 9 个路由页面
│   ├── pwa/register.ts        # SW 注册与更新检测
│   ├── router/index.ts        # 路由表
│   ├── scenarios/fixtures.ts  # 合成演示 fixtures
│   ├── services/              # ElderTerminalApi + Mock/Core 适配器
│   ├── stores/                # app（连接/更新）、care（数据/离线门控）
│   ├── styles/tokens.css      # 设计 token CSS 变量
│   ├── tokens/index.ts        # 设计 token 常量（测试断言用）
│   └── main.ts
└── tests/
    ├── unit/                  # Vitest（20 个文件）
    └── e2e/                   # Playwright（6 个文件）
```

## 路由表

| 路径 | 名称 | 标题 | 说明 |
| --- | --- | --- | --- |
| `/` | — | — | 重定向到 `/home` |
| `/home` | home | 今日 | 主任务、活动回顾、安全状态 |
| `/task/:id` | task | 任务详情 | 证据状态、确认请求 |
| `/alert/:id` | alert | 告警详情 | 发生时间、来源、确认 |
| `/safety` | safety | 安全提示 | S-1/S0 告警卡（不可关闭） |
| `/agent` | agent | 小护 | 每日摘要问答、来源抽屉 |
| `/timeline` | timeline | 时间线 | 合成事件流、质量原因 |
| `/settings` | settings | 设置 | 授权范围展示 |
| `/system` | system | 系统状态 | 在线/离线模拟、更新提示 |

## 接口映射（ElderTerminalApi 契约）

统一数据访问接口，`MockCoreAdapter` 与 `CoreApiAdapter` 共享同一契约（`src/services/adapter.ts`）：

| 方法 | 对应版本化端点 | Mock 行为 |
| --- | --- | --- |
| `getDashboard` | `GET /v1/dashboard` | 返回合成今日视图 + 主任务 |
| `getTasks` | `GET /v1/tasks` | 返回合成任务列表 |
| `getTimeline` | `GET /v1/timeline` | 返回合成事件流 |
| `getAlerts` | `GET /v1/alerts` | 返回合成告警列表 |
| `submitRequest` | `POST /v1/requests` | 幂等确认/查看；过期版本 → `VERSION_CONFLICT` |
| `chat` | `POST /v1/agent/chat` | 返回合成摘要；故障注入可模拟超时/越界/无来源 |
| `revokeConsent` | `POST /v1/consent` | 返回 `REVOKED` 授权视图 |

**写请求约束**：每个 `CareRequestV1` 必须携带 `commandId`、`idempotencyKey`、
`expectedVersion`；服务端按 `idempotencyKey` 幂等，按 `expectedVersion` 做乐观并发校验。

## 状态矩阵

见 `src/contracts/stateMatrix.ts`。页面可展示状态为 `READY / ONLINE / OFFLINE / STALE /
DENIED / FAILED / UNKNOWN / CONFLICT / FALLBACK / ACTIVE / ACKNOWLEDGED / RESOLVED`。
各页面的合法状态与“禁止项”已契约冻结（如任务详情禁止把 UNKNOWN 显示为已完成，
安全页禁止关闭 S-1/S0 告警）。

证据状态仅三值：`UNKNOWN / SEEN / PENDING`——**不存在“已吞服”等推断状态**。

## 设计 token（适老 P0）

见 `src/tokens/index.ts`：正文 ≥ 20px（body 24）、主要任务 ≥ 30px（main 32）、
数字时间 ≥ 28px（time 28）、辅助说明 ≥ 20px（caption 20）、可点击目标 ≥ 56×56px
（minTarget 56）。颜色含 brand `#0b3d2e`、danger `#b3261e`、focusRing `#f0a500` 等。

## 离线壳与陈旧数据

- `public/sw.js`：手写 Service Worker，导航请求网络优先、失败回退缓存 `index.html`；
  同源 GET 网络优先并回写缓存。**仅缓存壳与静态资源，绝不缓存敏感正文/令牌。**
- `useNetworkStatus`：监听 `online/offline`，联网时触发 `care.recover()` 刷新。
- 离线门控（`src/contracts/offlinePolicy.ts`）：安全告警确认（`ACKNOWLEDGE_ALERT`）为
  高风险，离线时直接阻断（“离线时无法执行此操作，请联网后再试。”）；普通低风险请求
  （`ACKNOWLEDGE_TASK` / `VIEW_ALERT`）仅提示“待网络恢复后重新提交”，**绝不自动执行**。
- 陈旧数据：离线时保留“最后可信快照”时间，状态条显示“陈旧数据 · 最后可信更新 …”。

## 可访问性

- 每页单一 `h1`，导航 `nav[aria-label="主导航"]`，跳转链接 `a.app-shell__skip`。
- 所有按钮有可访问名称；表单输入有 `<label>` 关联。
- 状态不以颜色为唯一表达（在线/离线均有可见文本）。
- 无障碍基线 e2e：`tests/e2e/accessibility.spec.ts`。

## 内容红线与日志脱敏

- 全局“模拟数据”标识、`source.type === 'SIMULATOR'`。
- 禁止把合成数据说成真实健康记录；禁止诊断、剂量建议、改药；禁止声称“已吞服”；
  禁止关闭/取消 SOS/烟雾/燃气告警；禁止把无来源数据展示为事实。
- **日志脱敏红线**：日志只允许 `correlationId / route / reasonCode / duration`，
  禁止写入消息正文、身份字段、Token 或健康数据；禁止写 `localStorage /
  sessionStorage / IndexedDB`。静态扫描测试：`tests/unit/logRedaction.test.ts`。

## 测试

- 单元/组件：`npm run test`（Vitest，20 个文件，覆盖 store、适配器、页面、状态矩阵、
  显示/错误映射、PWA 注册、离线门控、日志脱敏等）。
- 端到端：`npm run test:e2e`（Playwright，6 个文件：五条演示场景、无障碍、键盘、
  排版、设置、壳）。
- 五条演示场景见 `tests/e2e/scenarios.spec.ts`：① CareDose 服药提醒闭环；
  ② CareSafe 烟雾/燃气告警；③ CareRadar 低质量活动数据；④ CareAgent 每日摘要；
  ⑤ 网络断开与离线壳。

## 环境变量

见 `.env.example`。当前全部使用 `MockCoreAdapter`，以下变量为未来 C2 BFF 接入预留，
**尚未接入业务逻辑**：

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `/v1` | Core API 基础路径（预留） |
| `VITE_DEMO_MODE` | `mock` | 演示模式（当前唯一支持值） |

## 已知限制

- 真实 HTTP 接入需等 C2 BFF（C0–C4 就绪前），`CoreApiAdapter` 为 `NOT_IMPLEMENTED` 占位。
- 未引入 `vite-plugin-pwa`，PWA 用 `public/sw.js` + `src/pwa/register.ts` 手写实现。
- 无 git 仓库：版本回滚依赖源码快照/备份（见 `../../docs/version-and-rollback.md`）。
