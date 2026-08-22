import type {
  AgentFact,
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
} from './types';
import type { ErrorEnvelope } from './errors';

/** 手写严格运行时类型守卫（替代引入校验库，满足“严格 DTO guard”）。 */
export type Guard<T> = (value: unknown) => value is T;

const isRecord = (v: unknown): v is Record<string, unknown> =>
  typeof v === 'object' && v !== null && !Array.isArray(v);

const isString = (v: unknown): v is string => typeof v === 'string';

const isNonEmptyString = (v: unknown): v is string =>
  isString(v) && v.trim().length > 0;

const isNumber = (v: unknown): v is number =>
  typeof v === 'number' && Number.isFinite(v);

const isBoolean = (v: unknown): v is boolean => typeof v === 'boolean';

const isIsoDate = (v: unknown): v is string =>
  isNonEmptyString(v) && !Number.isNaN(Date.parse(v));

const oneOf = <T extends string>(allowed: readonly T[]): Guard<T> =>
  (v): v is T => isString(v) && (allowed as readonly string[]).includes(v);

const isArrayOf = <T>(guard: Guard<T>): Guard<T[]> =>
  (v): v is T[] => Array.isArray(v) && v.every(guard);

const SOURCE_TYPES = ['SIMULATOR'] as const;
const QUALITY_STATUSES = ['VALID', 'LOW', 'CONFLICT', 'UNKNOWN'] as const;
const CARE_EVENT_TYPES = [
  'MEDICATION_DUE',
  'SMOKE_GAS',
  'SOS',
  'FALL',
  'LOW_QUALITY_ACTIVITY',
] as const;
const EVIDENCE_STATES = ['UNKNOWN', 'SEEN', 'PENDING'] as const;
const TASK_KINDS = ['MEDICATION', 'SAFETY_CHECK', 'ACTIVITY_REVIEW'] as const;
const TASK_STATUSES = ['DUE', 'REMINDING', 'ACKNOWLEDGED', 'UNKNOWN'] as const;
const SAFETY_LEVELS = ['S-1', 'S0', 'S1', 'S2'] as const;
const ALERT_KINDS = ['SMOKE_GAS', 'SOS', 'FALL', 'GENERAL'] as const;
const ALERT_STATUSES = ['ACTIVE', 'ACKNOWLEDGED', 'RESOLVED'] as const;
const SAFETY_DISPLAY_STATUSES = ['ACTIVE', 'ACKNOWLEDGED', 'RESOLVED', 'NONE'] as const;
const CONSENT_SCOPES = ['timeline', 'alerts', 'tasks', 'summary'] as const;
const CONSENT_STATUSES = ['GRANTED', 'REVOKED', 'EXPIRED', 'PENDING'] as const;
const FRESHNESSES = ['FRESH', 'STALE'] as const;
const REQUEST_KINDS = ['ACKNOWLEDGE_TASK', 'VIEW_ALERT', 'ACKNOWLEDGE_ALERT'] as const;
const RECEIPT_STATUSES = ['RECEIVED', 'VERSION_CONFLICT'] as const;
const ERROR_CODES = ['OFFLINE', 'DENIED', 'FAILED', 'VALIDATION_ERROR', 'NOT_IMPLEMENTED'] as const;
const REASON_CODES = [
  'NETWORK_OFFLINE',
  'CONSENT_REVOKED',
  'CONSENT_EXPIRED',
  'SUBJECT_MISMATCH',
  'VERSION_CONFLICT',
  'UPSTREAM_TIMEOUT',
  'UPSTREAM_FAILED',
  'SCHEMA_INVALID',
  'NOT_IMPLEMENTED',
  'AGENT_FALLBACK',
] as const;

export const isEventSource: Guard<EventSource> = (v): v is EventSource =>
  isRecord(v) && oneOf(SOURCE_TYPES)(v.type) && isNonEmptyString(v.simulatorId);

export const isQuality: Guard<Quality> = (v): v is Quality =>
  isRecord(v) && oneOf(QUALITY_STATUSES)(v.status) &&
  (v.reason === undefined || isString(v.reason));

export const isSourceRef: Guard<SourceRef> = (v): v is SourceRef =>
  isRecord(v) && isNonEmptyString(v.refId) && isNonEmptyString(v.kind) &&
  isNonEmptyString(v.label) && isIsoDate(v.occurredAt);

export const isCareEventV1: Guard<CareEventV1> = (v): v is CareEventV1 =>
  isRecord(v) && isNonEmptyString(v.eventId) && oneOf(CARE_EVENT_TYPES)(v.eventType) &&
  isIsoDate(v.occurredAt) && isEventSource(v.source) && isQuality(v.quality) &&
  isArrayOf(isSourceRef)(v.sourceRefs);

export const isCareTaskV1: Guard<CareTaskV1> = (v): v is CareTaskV1 =>
  isRecord(v) && isNonEmptyString(v.taskId) && oneOf(TASK_KINDS)(v.kind) &&
  oneOf(TASK_STATUSES)(v.status) && isIsoDate(v.scheduledAt) &&
  oneOf(EVIDENCE_STATES)(v.evidenceState) && isNumber(v.version);

export const isAlertViewV1: Guard<AlertViewV1> = (v): v is AlertViewV1 =>
  isRecord(v) && isNonEmptyString(v.alertId) && oneOf(ALERT_KINDS)(v.kind) &&
  oneOf(SAFETY_LEVELS)(v.safetyLevel) && oneOf(ALERT_STATUSES)(v.status) &&
  isIsoDate(v.occurredAt) && isNumber(v.version);

export const isAgentFact: Guard<AgentFact> = (v): v is AgentFact =>
  isRecord(v) && isNonEmptyString(v.statement) &&
  isArrayOf(isSourceRef)(v.sourceRefs) && v.sourceRefs.length > 0 &&
  oneOf(QUALITY_STATUSES)(v.confidence);

export const isAgentResponseV1: Guard<AgentResponseV1> = (v): v is AgentResponseV1 =>
  isRecord(v) && isString(v.message) && isArrayOf(isAgentFact)(v.facts) &&
  isArrayOf(isSourceRef)(v.sourceRefs) && isBoolean(v.fallback) &&
  (v.fallback
    ? isNonEmptyString(v.reasonCode)
    : v.reasonCode === undefined || isString(v.reasonCode));

export const isConsentViewV1: Guard<ConsentViewV1> = (v): v is ConsentViewV1 =>
  isRecord(v) && oneOf(CONSENT_SCOPES)(v.scope) &&
  oneOf(CONSENT_STATUSES)(v.status) && isIsoDate(v.expiresAt) && isNumber(v.version);

export const isFact: Guard<Fact> = (v): v is Fact =>
  isRecord(v) && isNonEmptyString(v.key) && isString(v.value) &&
  oneOf(QUALITY_STATUSES)(v.confidence);

export const isUnknownItem: Guard<UnknownItem> = (v): v is UnknownItem =>
  isRecord(v) && isNonEmptyString(v.key) && isString(v.note);

export const isContextSnapshotV1: Guard<ContextSnapshotV1> = (v): v is ContextSnapshotV1 =>
  isRecord(v) && isNonEmptyString(v.snapshotId) && isNonEmptyString(v.purpose) &&
  isIsoDate(v.asOf) && isArrayOf(isFact)(v.facts) &&
  isArrayOf(isUnknownItem)(v.unknowns) && oneOf(FRESHNESSES)(v.freshness);

export const isDashboardViewV1: Guard<DashboardViewV1> = (v): v is DashboardViewV1 =>
  isRecord(v) && isIsoDate(v.serverTime) && isNonEmptyString(v.snapshotId) &&
  isNonEmptyString(v.welcome) && (v.primaryTask === null || isCareTaskV1(v.primaryTask)) &&
  isNonEmptyString(v.nextAction) && oneOf(SAFETY_DISPLAY_STATUSES)(v.safetyStatus) &&
  isArrayOf(isSourceRef)(v.sourceRefs);

export const isCareRequestV1: Guard<CareRequestV1> = (v): v is CareRequestV1 =>
  isRecord(v) && isNonEmptyString(v.commandId) && isNonEmptyString(v.idempotencyKey) &&
  isNumber(v.expectedVersion) && oneOf(REQUEST_KINDS)(v.kind) && isNonEmptyString(v.targetId);

export const isRequestReceiptV1: Guard<RequestReceiptV1> = (v): v is RequestReceiptV1 =>
  isRecord(v) && isNonEmptyString(v.commandId) && oneOf(RECEIPT_STATUSES)(v.status) &&
  isIsoDate(v.receivedAt);

export const isErrorEnvelope: Guard<ErrorEnvelope> = (v): v is ErrorEnvelope =>
  isRecord(v) && isRecord(v.error) &&
  oneOf(ERROR_CODES)(v.error.code) && oneOf(REASON_CODES)(v.error.reasonCode) &&
  isNonEmptyString(v.error.message) && isNonEmptyString(v.error.correlationId) &&
  isBoolean(v.error.retryable) && isString(v.version);

export interface ParseOk<T> {
  ok: true;
  value: T;
}
export interface ParseErr {
  ok: false;
  path: string;
}
export type ParseResult<T> = ParseOk<T> | ParseErr;

export function safeParse<T>(guard: Guard<T>, value: unknown, path = 'value'): ParseResult<T> {
  return guard(value) ? { ok: true, value } : { ok: false, path };
}
