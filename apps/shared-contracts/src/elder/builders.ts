import type {
  AgentResponseV1,
  AlertViewV1,
  CareEventV1,
  CareRequestV1,
  CareTaskV1,
  ConsentViewV1,
  ContextSnapshotV1,
  DashboardViewV1,
  EventSource,
  Fact,
  Quality,
  RequestReceiptV1,
  SourceRef,
  UnknownItem,
} from './types'
import type { ErrorCode, ErrorEnvelope, ReasonCode } from './errors'
import { API_VERSION } from './types'

let counter = 0
export const makeId = (prefix: string): string => `${prefix}-${++counter}`

export const makeSourceRef = (overrides: Partial<SourceRef> = {}): SourceRef => ({
  type: 'SIMULATOR',
  ref_id: makeId('ref'),
  kind: 'simulator_event',
  label: '合成事件',
  occurred_at: new Date().toISOString(),
  ...overrides,
})

export const makeEventSource = (overrides: Partial<EventSource> = {}): EventSource => ({
  type: 'SIMULATOR',
  simulator_id: 'care-dose',
  ...overrides,
})

export const makeQuality = (overrides: Partial<Quality> = {}): Quality => ({
  status: 'VALID',
  ...overrides,
})

export const makeCareEvent = (overrides: Partial<CareEventV1> = {}): CareEventV1 => ({
  event_id: makeId('evt'),
  event_type: 'MEDICATION_DUE',
  occurred_at: new Date().toISOString(),
  source: makeEventSource(),
  quality: makeQuality(),
  source_refs: [makeSourceRef()],
  ...overrides,
})

export const makeCareTask = (overrides: Partial<CareTaskV1> = {}): CareTaskV1 => ({
  task_id: makeId('task'),
  kind: 'MEDICATION_DUE',
  status: 'DUE',
  scheduled_at: new Date().toISOString(),
  evidence_state: 'UNKNOWN',
  version: 1,
  source_refs: [{ type: 'SIMULATOR', label: 'CareDose 合成事件' }],
  ...overrides,
})

export const makeAlert = (overrides: Partial<AlertViewV1> = {}): AlertViewV1 => ({
  alert_id: makeId('alert'),
  kind: 'SMOKE_GAS',
  safety_level: 'S0',
  status: 'OPEN',
  occurred_at: new Date().toISOString(),
  version: 1,
  source_refs: [{ type: 'SIMULATOR', label: 'CareSafe 合成事件' }],
  quality: 'VALID',
  ...overrides,
})

export const makeAgentResponse = (
  overrides: Partial<AgentResponseV1> = {},
): AgentResponseV1 => ({
  schema_version: 'AgentResponseV1',
  response_id: makeId('response'),
  agent_run_id: makeId('run'),
  channel: 'TERMINAL',
  message: '今日提醒已整理完毕。',
  facts: [],
  fallback: 'NONE',
  generator_version: API_VERSION,
  ...overrides,
})

export const makeConsent = (overrides: Partial<ConsentViewV1> = {}): ConsentViewV1 => ({
  scope: 'timeline',
  status: 'ACTIVE',
  expires_at: new Date(Date.now() + 86_400_000).toISOString(),
  version: 1,
  ...overrides,
})

export const makeFact = (overrides: Partial<Fact> = {}): Fact => ({
  key: 'key', value: 'value', confidence: 'VALID', ...overrides,
})

export const makeUnknownItem = (overrides: Partial<UnknownItem> = {}): UnknownItem => ({
  key: 'key', note: '暂未确认', ...overrides,
})

export const makeContextSnapshot = (
  overrides: Partial<ContextSnapshotV1> = {},
): ContextSnapshotV1 => ({
  snapshot_id: makeId('snap'),
  purpose: 'dashboard',
  as_of: new Date().toISOString(),
  facts: [],
  unknowns: [],
  freshness: 'FRESH',
  ...overrides,
})

export const makeDashboard = (
  overrides: Partial<DashboardViewV1> = {},
): DashboardViewV1 => ({
  snapshot_id: makeId('snap'),
  server_time: new Date().toISOString(),
  source_refs: [{ type: 'SIMULATOR', label: 'CareHub 合成聚合' }],
  quality: 'VALID',
  last_updated_at: new Date().toISOString(),
  family_member: {
    subject_id: 'subject-sim-001',
    household_id: 'household-sim-001',
    display_name: '合成用户',
    relationship: 'SELF',
  },
  consent: makeConsent(),
  welcome: '您好，今天最重要的一件事如下。',
  primaryTask: makeCareTask(),
  nextAction: '点击查看任务详情',
  safetyStatus: 'NONE',
  ...overrides,
})

export const makeCareRequest = (
  overrides: Partial<CareRequestV1> = {},
): CareRequestV1 => ({
  command_id: makeId('cmd'),
  idempotency_key: makeId('idem'),
  expected_version: 1,
  reason_code: 'ACKNOWLEDGE_VIEWED',
  kind: 'ACKNOWLEDGE_TASK',
  target_id: makeId('target'),
  ...overrides,
})

export const makeReceipt = (
  overrides: Partial<RequestReceiptV1> = {},
): RequestReceiptV1 => ({
  request_id: makeId('request'),
  audit_time: new Date().toISOString(),
  alert_id: makeId('target'),
  status: 'RECORDED',
  ...overrides,
})

export const makeError = (
  code: ErrorCode,
  reasonCode: ReasonCode,
  message: string,
  retryable = false,
  correlationId = makeId('corr'),
): ErrorEnvelope => ({
  code,
  reason_code: reasonCode,
  message,
  correlation_id: correlationId,
  retryable,
})
