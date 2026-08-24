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
  Quality,
  RequestReceiptV1,
  SourceRef,
} from './types';
import type { ErrorCode, ErrorEnvelope, ReasonCode } from './errors';
import { API_VERSION } from './types';

let counter = 0;
export const makeId = (prefix: string): string => `${prefix}-${++counter}`;

export const makeSourceRef = (overrides: Partial<SourceRef> = {}): SourceRef => ({
  ref_id: makeId('ref'),
  kind: 'simulator_event',
  label: '合成事件',
  occurred_at: new Date().toISOString(),
  ...overrides,
});

export const makeEventSource = (overrides: Partial<EventSource> = {}): EventSource => ({
  type: 'SIMULATOR',
  simulator_id: 'care-dose',
  ...overrides,
});

export const makeQuality = (overrides: Partial<Quality> = {}): Quality => ({
  status: 'VALID',
  ...overrides,
});

export const makeCareEvent = (overrides: Partial<CareEventV1> = {}): CareEventV1 => ({
  event_id: makeId('evt'),
  event_type: 'MEDICATION_DUE',
  occurred_at: new Date().toISOString(),
  source: makeEventSource(),
  quality: makeQuality(),
  source_refs: [makeSourceRef()],
  ...overrides,
});

export const makeCareTask = (overrides: Partial<CareTaskV1> = {}): CareTaskV1 => ({
  task_id: makeId('task'),
  kind: 'MEDICATION',
  status: 'DUE',
  scheduled_at: new Date().toISOString(),
  evidence_state: 'UNKNOWN',
  version: 1,
  ...overrides,
});

export const makeAlert = (overrides: Partial<AlertViewV1> = {}): AlertViewV1 => ({
  alert_id: makeId('alert'),
  kind: 'SMOKE_GAS',
  safety_level: 'S0',
  status: 'ACTIVE',
  occurred_at: new Date().toISOString(),
  version: 1,
  ...overrides,
});

export const makeAgentResponse = (overrides: Partial<AgentResponseV1> = {}): AgentResponseV1 => ({
  message: '今日提醒已整理完毕。',
  facts: [],
  source_refs: [makeSourceRef()],
  fallback: false,
  ...overrides,
});

export const makeConsent = (overrides: Partial<ConsentViewV1> = {}): ConsentViewV1 => ({
  scope: 'timeline',
  status: 'GRANTED',
  expires_at: new Date(Date.now() + 86_400_000).toISOString(),
  version: 1,
  ...overrides,
});

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
});

export const makeDashboard = (overrides: Partial<DashboardViewV1> = {}): DashboardViewV1 => ({
  server_time: new Date().toISOString(),
  snapshot_id: makeId('snap'),
  welcome: '您好，今天最重要的一件事如下。',
  primaryTask: makeCareTask(),
  nextAction: '点击查看任务详情',
  safetyStatus: 'NONE',
  source_refs: [makeSourceRef()],
  ...overrides,
});

export const makeCareRequest = (overrides: Partial<CareRequestV1> = {}): CareRequestV1 => ({
  commandId: makeId('cmd'),
  idempotency_key: makeId('idem'),
  expected_version: 1,
  kind: 'ACKNOWLEDGE_TASK',
  targetId: makeId('task'),
  ...overrides,
});

export const makeReceipt = (overrides: Partial<RequestReceiptV1> = {}): RequestReceiptV1 => ({
  commandId: makeId('cmd'),
  status: 'RECEIVED',
  receivedAt: new Date().toISOString(),
  ...overrides,
});

export const makeError = (
  code: ErrorCode,
  reasonCode: ReasonCode,
  message: string,
  retryable = false,
): ErrorEnvelope => ({
  error: { code, reasonCode, message, correlationId: makeId('corr'), retryable },
  version: API_VERSION,
});
