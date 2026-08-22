/**
 * CareHub 2.0 — 双端共享版本化 DTO（老人端 + 家属端）。
 *
 * 这些 TypeScript 类型与 contracts/*.schema.json（声明式唯一事实源）对应，
 * 运行时由 guards.ts 严格校验。所有演示数据必须 source.type === 'SIMULATOR'，
 * 且绝不可被呈现为真实医疗记录。
 */

export const API_VERSION = 'v1';

/** 内容红线：所有演示数据必须携带的全局标识文案。 */
export const SIMULATED_DATA_LABEL = '模拟数据';

export type SubjectId = string;
export type HouseholdId = string;

/** 每一条演示数据都来自某个合成模拟器。 */
export type SourceType = 'SIMULATOR';

export interface EventSource {
  type: SourceType;
  simulatorId: string;
}

export type QualityStatus = 'VALID' | 'LOW' | 'CONFLICT' | 'UNKNOWN';

export interface Quality {
  status: QualityStatus;
  reason?: string;
}

export interface SourceRef {
  refId: string;
  kind: string;
  label: string;
  occurredAt: string;
}

export type CareEventType =
  | 'MEDICATION_DUE'
  | 'SMOKE_GAS'
  | 'SOS'
  | 'FALL'
  | 'LOW_QUALITY_ACTIVITY';

export interface CareEventV1 {
  eventId: string;
  eventType: CareEventType;
  occurredAt: string;
  source: EventSource;
  quality: Quality;
  sourceRefs: SourceRef[];
}

export type EvidenceState = 'UNKNOWN' | 'SEEN' | 'PENDING';

export type TaskKind = 'MEDICATION' | 'SAFETY_CHECK' | 'ACTIVITY_REVIEW';
export type TaskStatus = 'DUE' | 'REMINDING' | 'ACKNOWLEDGED' | 'UNKNOWN';

export interface CareTaskV1 {
  taskId: string;
  kind: TaskKind;
  status: TaskStatus;
  scheduledAt: string;
  evidenceState: EvidenceState;
  version: number;
}

export type SafetyLevel = 'S-1' | 'S0' | 'S1' | 'S2';
export type AlertKind = 'SMOKE_GAS' | 'SOS' | 'FALL' | 'GENERAL';
export type AlertStatus = 'ACTIVE' | 'ACKNOWLEDGED' | 'RESOLVED';

export interface AlertViewV1 {
  alertId: string;
  kind: AlertKind;
  safetyLevel: SafetyLevel;
  status: AlertStatus;
  occurredAt: string;
  version: number;
}

export interface AgentFact {
  statement: string;
  sourceRefs: SourceRef[];
  confidence: QualityStatus;
}

export interface AgentResponseV1 {
  message: string;
  facts: AgentFact[];
  sourceRefs: SourceRef[];
  fallback: boolean;
  reasonCode?: string;
}

export type ConsentScope = 'timeline' | 'alerts' | 'tasks' | 'summary';
export type ConsentStatus = 'GRANTED' | 'REVOKED' | 'EXPIRED' | 'PENDING';

export interface ConsentViewV1 {
  scope: ConsentScope;
  status: ConsentStatus;
  expiresAt: string;
  version: number;
}

export interface Fact {
  key: string;
  value: string;
  confidence: QualityStatus;
}

export interface UnknownItem {
  key: string;
  note: string;
}

export type Freshness = 'FRESH' | 'STALE';

export interface ContextSnapshotV1 {
  snapshotId: string;
  purpose: string;
  asOf: string;
  facts: Fact[];
  unknowns: UnknownItem[];
  freshness: Freshness;
}

export interface DashboardViewV1 {
  serverTime: string;
  snapshotId: string;
  welcome: string;
  primaryTask: CareTaskV1 | null;
  nextAction: string;
  safetyStatus: AlertStatus | 'NONE';
  sourceRefs: SourceRef[];
}

export type RequestKind = 'ACKNOWLEDGE_TASK' | 'VIEW_ALERT' | 'ACKNOWLEDGE_ALERT';

export interface CareRequestV1 {
  commandId: string;
  idempotencyKey: string;
  expectedVersion: number;
  kind: RequestKind;
  targetId: string;
}

export type ReceiptStatus = 'RECEIVED' | 'VERSION_CONFLICT';

export interface RequestReceiptV1 {
  commandId: string;
  status: ReceiptStatus;
  receivedAt: string;
}
