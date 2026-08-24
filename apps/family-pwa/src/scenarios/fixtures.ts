import type { AgentResponseV1, AlertViewV1, CareTaskV1, DashboardV1 } from '@carehub/shared-contracts'

export const familyDashboardFixture: DashboardV1 = {
  snapshot_id: 'snap-family-demo-001',
  server_time: '2026-08-14T09:50:00+08:00',
  last_updated_at: '2026-08-14T09:50:00+08:00',
  quality: 'VALID',
  source_refs: [{ type: 'SIMULATOR', label: 'CareHub 合成模拟器' }],
  family_member: { subject_id: 'subject-demo-parent-01', household_id: 'household-demo-01', display_name: '演示家庭成员', relationship: '家人' },
  consent: { scope: 'family.dashboard.read', status: 'ACTIVE', expires_at: '2026-12-31T23:59:59+08:00', version: 1 }
}
export const smokeGasAlertFixture: AlertViewV1 = { alert_id: 'alert-smoke-gas-001', kind: 'SMOKE_GAS', safety_level: 'S-1', status: 'OPEN', occurred_at: '2026-08-14T10:24:00+08:00', version: 3, quality: 'VALID', source_refs: [{ type: 'SIMULATOR', label: 'CareSafe 合成模拟器' }] }
export const medicationTaskFixture: CareTaskV1 = { task_id: 'task-medication-001', kind: 'MEDICATION_DUE', status: 'DUE', scheduled_at: '2026-08-14T12:00:00+08:00', evidence_state: 'UNKNOWN', version: 2, source_refs: [{ type: 'SIMULATOR', label: 'CareDose 合成模拟器' }] }
export const dailyReportFixture: AgentResponseV1 = { schema_version: 'AgentResponseV1', response_id: 'response-demo-report-001', agent_run_id: 'run-demo-report-001', channel: 'FAMILY', message: '今日状态存在待确认信息，请以来源记录为准。', facts: [{ text: '安全提醒：1 条 S-1 模拟告警。', source_refs: ['evt-smoke-gas-001'] }, { text: '任务证据：UNKNOWN，待确认。', source_refs: ['evt-medication-001'] }], fallback: 'NONE', generator_version: 'fixture.g4.v1' }
export const fallbackReportFixture: AgentResponseV1 = { schema_version: 'AgentResponseV1', response_id: 'response-demo-fallback-001', agent_run_id: 'run-demo-fallback-001', channel: 'FAMILY', message: '受控摘要暂不可用，已显示固定说明。', facts: [], fallback: 'TEMPLATE_FALLBACK', generator_version: 'response-template-g4.v1' }
