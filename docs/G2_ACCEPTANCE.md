# G2 确定性 CareAgent MVP 验收

本 Gate 依据《CareHub 2.0_CareAgent详细架构与研发任务书_V1.0_正式版》执行。G2 不接真实 LLM、真实硬件、真实通知服务或真实健康数据。

## 已验收能力

- `AgentRunV1` 持久化状态机：接收、上下文、规划、策略检查、执行、完成/拒绝，并使用乐观版本控制。
- `CareTaskV1` 以主体、来源事件、状态、安全等级和版本持久化。
- `ContextSnapshotV1` 按 purpose 构造、最小化、哈希冻结并持久化；任务事实均有来源事件。
- Deterministic Planner 固定实现 Medication Reminder、Inactivity Check、Fall Follow-up、Daily Summary、Family Escalation。
- Policy Gateway 对调用者、主体、能力、同意和幂等键默认拒绝。
- Mock Skill Executor 以幂等键去重；UI/TTS/Family Mock 接收固定 Response 模板。
- Response Engine 要求 `source_refs`，并对医疗、剂量、已服药等越界文本模板降级。
- 重启后可恢复 AgentRun、CareTask、ContextSnapshot、Plan 与已执行 Intent。

## 证据

```bash
env -u PYTHONPATH conda run -n carehub-research python -m pytest -q
env -u PYTHONPATH conda run -n carehub-research python -m scripts.run_g2_demo
```

全套测试覆盖五工作流（其中五条演示覆盖任务书要求的至少四条闭环）、跨主体/缺少同意拒绝、Intent 幂等、AgentRun 版本冲突与数据库重启恢复。

## 明确排除

- 真实模型接入及可信模型回复属于 G4。
- 长期记忆、生产 Consent/RBAC、隐私生命周期属于 G3。
- 真实硬件、医疗判断、剂量调整、服药确认、自治告警和真实家属通知不在本 Gate。
