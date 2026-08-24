# CareAgent

[![CI](https://github.com/wananan233/CareAgent/actions/workflows/ci.yml/badge.svg)](https://github.com/wananan233/CareAgent/actions/workflows/ci.yml)

CareHub 2.0 的本地优先照护建议编排器。它不是设备控制器、医疗诊断系统或自治急救决策器。

## PWA 工作区

家庭端与老人端现已统一到根 pnpm 工作区，并共享家庭端 Core DTO：

```text
apps/family-pwa/         家庭端 PWA
apps/elder-terminal/     老人端 PWA
apps/shared-contracts/   跨端契约；src/family.ts 为 Core 规范来源
```

```bash
pnpm install --frozen-lockfile
pnpm --filter @carehub/family-pwa dev
pnpm --filter @carehub/elder-terminal dev
```

完整老人端验收结果见 [docs/elder-terminal/acceptance-report.md](docs/elder-terminal/acceptance-report.md)。

## 当前 Gate：G5（可观测性、重放与故障注入）

G1 已实现 SQLite WAL 事件库、Transactional Outbox、确定性规则、状态投影与合成设备模拟器。G2 在其上实现不依赖模型的 CareAgent MVP。G3 新增结构化与工作记忆、同意账本、RBAC+ABAC、数据删除与敏感日志扫描。G4 增加默认离线 FakeProvider、目的最小化、固定 Schema、安全扫描与模板降级，仅开放今日状态和日报。G5 增加最小化 Trace/Metrics、确定性重放报告与故障注入证据。G4 另提供可选的 DeepSeek Provider，密钥只从独立进程环境变量读取。

## 能力概览

- **G1 事件闭环**：模拟器事件经过 Event Store、确定性 Rule Engine、Projection 与 Transactional Outbox，可完整重放。
- **G2 安全聊天**：模型只能接收经过授权、最小化且带来源引用的上下文快照，不能访问数据库、设备或 Skill。
- **G2.1 状态问答**：G1 的活动告警、服药任务和未知状态可转换为可追溯的聊天事实。
- **G2.2 本地 API**：`POST /v1/users/{id}/chat` 使用 Bearer Token 绑定用户，服务只监听 `127.0.0.1`。
- **G2.3 网页界面**：浏览器端最多保留三轮历史；令牌和历史不写入数据库或磁盘。
- **G2.4 可追溯回答**：DeepSeek 只能输出授权事实索引；服务端将其映射为 `AgentResponseV1.facts`，拒绝越界引用。
- **G2.5 运行保护**：本地 HTTP API 按已认证用户限制为每分钟最多 10 次请求，限流状态仅保存在内存。
- **G2.6 持续验证**：GitHub Actions 会在每次推送和 Pull Request 中执行全量测试。
- **G2 验收收口**：HTTP 请求结果记录为不含消息正文的审计哈希链；完整范围见 [G2 验收文档](docs/G2_ACCEPTANCE.md)。

### 已冻结的边界

- S-1/S0 安全链路不经过 LLM 或 Planner；模型不能直连 SQLite、MQTT、BLE、GPIO、Shell、任意 HTTP 或 Skill。
- 所有有副作用的动作先表示为 `ActionIntentV1`；它不是执行结果。
- `CareEventV1` 是事实记录；所有时间必须是带时区的 RFC3339 字符串。
- 健康观察必须同时带 `source`、`quality`、`measured_at`；不确定信息使用 `UNKNOWN` 与原因，不用猜测或零值代替。
- G0 默认使用合成 fixture 与 FakeLLM；不保存原始音视频或真实健康数据。

## 目录

```text
contracts/schemas/     JSON Schema 唯一契约源
openapi/               API 边界
policies/              RBAC + ABAC + Consent 能力矩阵
skills/                白名单 Skill Manifest
fixtures/golden/       固定时钟、纯合成测试数据
carehub/core/          Event Store、Rule Engine、Projection、Replay
carehub/g2/            只读聊天服务、上下文快照与 FakeLLM
carehub/simulators/    Dose/Safe/Radar/Vision 等合成事件适配器
docs/adr/              已决架构决策
docs/threat-model/     安全与隐私威胁模型
scripts/               契约校验脚本
tests/                 G0 自动校验
```

## 验证

```bash
cd /home/ziyi/Desktop/Careagent
env -u PYTHONPATH conda run -n carehub-research python -m pytest -q
env -u PYTHONPATH conda run -n carehub-research python -m scripts.run_g1_demo
env -u PYTHONPATH conda run -n carehub-research python -m scripts.run_g2_demo
```

当前测试套件覆盖契约、事件幂等、死信隔离、规则安全分支、投影回放、G1→G2 授权快照、DeepSeek 适配器与本地 HTTP API。

## 快速开始：本地网页聊天

需要 Python 3.11、Conda 环境 `carehub-research` 与可选的 DeepSeek API 密钥。仅使用 FakeLLM 运行测试不需要网络或模型密钥。

```bash
cd /home/ziyi/Desktop/Careagent
export DEEPSEEK_API_KEY='新生成的密钥'
export CAREHUB_API_TOKEN='自行生成的本地随机令牌'
env -u PYTHONPATH conda run --no-capture-output -n carehub-research python -m scripts.run_g2_simulator_api
```

随后访问 [http://127.0.0.1:8080/](http://127.0.0.1:8080/)，输入用户 ID `synthetic-01` 和同一 `CAREHUB_API_TOKEN`。该服务只使用合成模拟器数据，按 `Ctrl+C` 可停止。

### DeepSeek（可选）

先在 DeepSeek 控制台撤销任何已泄露的密钥，并在当前终端设置新密钥（不要写进仓库）：

```bash
export DEEPSEEK_API_KEY='新生成的密钥'
```

创建聊天服务时注入 `ChatService(DeepSeekGenerator())` 即使用 `deepseek-v4-flash`。适配器只调用无工具的 Chat Completions 接口，且最终回复仍会经过本地契约与来源校验。
DeepSeek 输出采用 JSON 模式，回复引用只能指向 `ContextSnapshotV1.facts` 中的授权事实。

配置后可运行一次只读连通性演示：

```bash
env -u PYTHONPATH conda run -n carehub-research python -m scripts.run_g2_deepseek_demo
```

启动本地交互式聊天（最近 3 轮只存在内存，输入 `/exit` 结束）：

```bash
env -u PYTHONPATH conda run --no-capture-output -n carehub-research python -m scripts.run_g2_chat_cli
```

启动带 G1 模拟器状态的聊天（内置一条合成服药任务）：

```bash
env -u PYTHONPATH conda run --no-capture-output -n carehub-research python -m scripts.run_g2_simulator_chat_cli
```

### G2.2 本地 HTTP API（模拟器）

服务仅监听 `127.0.0.1`。在两个终端分别执行：

```bash
export CAREHUB_API_TOKEN='自行生成的本地随机令牌'
env -u PYTHONPATH conda run --no-capture-output -n carehub-research python -m scripts.run_g2_simulator_api
```

```bash
curl -sS -X POST 'http://127.0.0.1:8080/v1/users/synthetic-01/chat' \
  -H "Authorization: Bearer $CAREHUB_API_TOKEN" \
  -H 'Content-Type: application/json' \
  --data '{"message":"我现在有什么提醒？"}'
```

令牌绑定 `user:synthetic-01`，不能访问其他用户；请求内容和对话历史不会写入事件库或磁盘。

服务启动后，在浏览器打开 [http://127.0.0.1:8080/](http://127.0.0.1:8080/)，填写相同的 `CAREHUB_API_TOKEN` 即可使用网页聊天。网页中的令牌和最近三轮历史只存于当前页面内存。

## G0 未决项

见 [docs/G0_DECISIONS.md](docs/G0_DECISIONS.md)。已按你的批准以纯合成数据进入 G1；服药暂缓窗口、长时间静止阈值、服药证据矩阵及产品化合规适用性尚未制度性签字，因此不接入真实用药、告警或硬件服务。
