import type {
  AgentResponseV1, AlertViewV1, CareEventV1, CareRequestV1, CareTaskV1,
  ConsentViewV1, ContextSnapshotV1, DashboardViewV1, EventSource, Fact,
  Quality, RequestReceiptV1, SourceRef, UnknownItem,
} from './types'
import type { ErrorEnvelope } from './errors'

export type Guard<T> = (value: unknown) => value is T
const record = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v)
const string = (v: unknown): v is string => typeof v === 'string'
const nonempty = (v: unknown): v is string => string(v) && v.trim().length > 0
const number = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v)
const boolean = (v: unknown): v is boolean => typeof v === 'boolean'
const iso = (v: unknown): v is string => nonempty(v) && !Number.isNaN(Date.parse(v))
const oneOf = <T extends string>(xs: readonly T[]): Guard<T> => (v): v is T => string(v) && (xs as readonly string[]).includes(v)
const arrayOf = <T>(g: Guard<T>): Guard<T[]> => (v): v is T[] => Array.isArray(v) && v.every(g)

const QUALITY = ['VALID', 'LOW', 'CONFLICT', 'UNKNOWN'] as const
const EVENTS = ['MEDICATION_DUE', 'SMOKE_GAS', 'LOW_QUALITY_ACTIVITY'] as const
const TASK_STATUS = ['DUE', 'REMINDING', 'ACKNOWLEDGED'] as const
const ALERT_STATUS = ['OPEN', 'VIEWED'] as const
const CONSENT_STATUS = ['ACTIVE', 'EXPIRED', 'REVOKED'] as const
const FALLBACK = ['NONE', 'TEMPLATE_FALLBACK', 'DETERMINISTIC_FALLBACK'] as const
const ERROR_CODES = ['UNAUTHORIZED', 'FORBIDDEN', 'OFFLINE', 'SCHEMA_INVALID', 'UNAVAILABLE', 'VERSION_CONFLICT', 'INVALID_REQUEST', 'INTERNAL_ERROR'] as const
const REASON_CODES = [...ERROR_CODES, 'NETWORK_OFFLINE', 'CONSENT_REVOKED', 'CONSENT_EXPIRED', 'SUBJECT_MISMATCH', 'UPSTREAM_TIMEOUT', 'UPSTREAM_FAILED', 'NOT_IMPLEMENTED', 'AGENT_FALLBACK'] as const
const REQUEST_KINDS = ['ACKNOWLEDGE_TASK', 'VIEW_ALERT', 'ACKNOWLEDGE_ALERT'] as const

export const isSourceRef: Guard<SourceRef> = (v): v is SourceRef => record(v) && v.type === 'SIMULATOR' && nonempty(v.label) && nonempty(v.ref_id) && nonempty(v.kind) && iso(v.occurred_at)
export const isEventSource: Guard<EventSource> = (v): v is EventSource => record(v) && v.type === 'SIMULATOR' && nonempty(v.simulator_id)
export const isQuality: Guard<Quality> = (v): v is Quality => record(v) && oneOf(QUALITY)(v.status) && (v.reason === undefined || string(v.reason))
export const isCareEventV1: Guard<CareEventV1> = (v): v is CareEventV1 => record(v) && nonempty(v.event_id) && oneOf(EVENTS)(v.event_type) && iso(v.occurred_at) && isEventSource(v.source) && isQuality(v.quality) && arrayOf(isSourceRef)(v.source_refs)
export const isCareTaskV1: Guard<CareTaskV1> = (v): v is CareTaskV1 => record(v) && nonempty(v.task_id) && v.kind === 'MEDICATION_DUE' && oneOf(TASK_STATUS)(v.status) && iso(v.scheduled_at) && v.evidence_state === 'UNKNOWN' && number(v.version) && Array.isArray(v.source_refs) && v.source_refs.every((x) => record(x) && x.type === 'SIMULATOR' && nonempty(x.label))
export const isAlertViewV1: Guard<AlertViewV1> = (v): v is AlertViewV1 => record(v) && nonempty(v.alert_id) && v.kind === 'SMOKE_GAS' && (v.safety_level === 'S-1' || v.safety_level === 'S0') && oneOf(ALERT_STATUS)(v.status) && iso(v.occurred_at) && number(v.version) && oneOf(QUALITY)(v.quality) && Array.isArray(v.source_refs)
export const isAgentFact: Guard<AgentResponseV1['facts'][number]> = (v): v is AgentResponseV1['facts'][number] => record(v) && nonempty(v.text) && Array.isArray(v.source_refs) && v.source_refs.length > 0 && v.source_refs.every(nonempty)
export const isAgentResponseV1: Guard<AgentResponseV1> = (v): v is AgentResponseV1 => record(v) && v.schema_version === 'AgentResponseV1' && nonempty(v.response_id) && nonempty(v.agent_run_id) && (v.channel === 'TERMINAL' || v.channel === 'TTS' || v.channel === 'FAMILY') && string(v.message) && arrayOf(isAgentFact)(v.facts) && oneOf(FALLBACK)(v.fallback) && nonempty(v.generator_version)
export const isConsentViewV1: Guard<ConsentViewV1> = (v): v is ConsentViewV1 => record(v) && nonempty(v.scope) && oneOf(CONSENT_STATUS)(v.status) && iso(v.expires_at) && number(v.version)
export const isFact: Guard<Fact> = (v): v is Fact => record(v) && nonempty(v.key) && string(v.value) && oneOf(QUALITY)(v.confidence)
export const isUnknownItem: Guard<UnknownItem> = (v): v is UnknownItem => record(v) && nonempty(v.key) && string(v.note)
export const isContextSnapshotV1: Guard<ContextSnapshotV1> = (v): v is ContextSnapshotV1 => record(v) && nonempty(v.snapshot_id) && nonempty(v.purpose) && iso(v.as_of) && arrayOf(isFact)(v.facts) && arrayOf(isUnknownItem)(v.unknowns) && (v.freshness === 'FRESH' || v.freshness === 'STALE')
export const isDashboardViewV1: Guard<DashboardViewV1> = (v): v is DashboardViewV1 => record(v) && nonempty(v.snapshot_id) && iso(v.server_time) && iso(v.last_updated_at) && oneOf(QUALITY)(v.quality) && record(v.family_member) && nonempty(v.family_member.subject_id) && nonempty(v.family_member.household_id) && isConsentViewV1(v.consent) && nonempty(v.welcome) && (v.primaryTask === null || isCareTaskV1(v.primaryTask)) && nonempty(v.nextAction) && (v.safetyStatus === 'NONE' || oneOf(ALERT_STATUS)(v.safetyStatus)) && Array.isArray(v.source_refs)
export const isCareRequestV1: Guard<CareRequestV1> = (v): v is CareRequestV1 => record(v) && nonempty(v.command_id) && nonempty(v.idempotency_key) && number(v.expected_version) && v.reason_code === 'ACKNOWLEDGE_VIEWED' && oneOf(REQUEST_KINDS)(v.kind) && nonempty(v.target_id)
export const isRequestReceiptV1: Guard<RequestReceiptV1> = (v): v is RequestReceiptV1 => record(v) && nonempty(v.request_id) && iso(v.audit_time) && nonempty(v.alert_id) && v.status === 'RECORDED'
export const isErrorEnvelope: Guard<ErrorEnvelope> = (v): v is ErrorEnvelope => record(v) && oneOf(ERROR_CODES)(v.code) && nonempty(v.message) && nonempty(v.correlation_id) && (v.reason_code === undefined || oneOf(REASON_CODES)(v.reason_code)) && (v.retryable === undefined || boolean(v.retryable))

export type ParseResult<T> = { ok: true; value: T } | { ok: false; path: string }
export function safeParse<T>(guard: Guard<T>, value: unknown, path = 'value'): ParseResult<T> {
  return guard(value) ? { ok: true, value } : { ok: false, path }
}
