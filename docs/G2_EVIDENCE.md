# G2 确定性 MVP 证据

G2 仅使用固定模板、确定性 Planner 和 Mock Executor；运行中不调用 DeepSeek 或任何真实硬件/通知服务。

## 验收命令

```bash
env -u PYTHONPATH conda run -n carehub-research python -m pytest -q
env -u PYTHONPATH conda run -n carehub-research python -m scripts.run_g2_demo
```

`run_g2_demo` 覆盖 Medication Reminder、Inactivity Check、Fall Follow-up、Daily Summary、Family Escalation，分别分发到 TTS、UI 和 Family Mock。

## 安全证据

- Policy Gateway 对缺少同意、跨主体、未知能力、无幂等键默认拒绝。
- Mock Skill Executor 以 `idempotency_key` 去重；重放不会重复副作用。
- AgentRun 使用乐观版本迁移；重启后可读取 CareTask、ContextSnapshot 和 Plan。
- Response Engine 要求每项事实都带 `source_refs`，并阻止医疗/剂量/已服药等越界文本。
