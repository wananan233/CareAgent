export type QualityStatus = 'VALID' | 'LOW' | 'CONFLICT' | 'UNKNOWN'
export type ConsentStatus = 'ACTIVE' | 'EXPIRED' | 'REVOKED'

export interface SourceRefV1 {
  type: 'SIMULATOR'
  label: string
}

export interface FamilyMemberV1 {
  subject_id: string
  household_id: string
  display_name: string
  relationship: string
}

export interface ConsentViewV1 {
  scope: string
  status: ConsentStatus
  expires_at: string
  version: number
}

export interface DashboardV1 {
  snapshot_id: string
  server_time: string
  source_refs: SourceRefV1[]
  quality: QualityStatus
  last_updated_at: string
  family_member: FamilyMemberV1
  consent: ConsentViewV1
}

export interface AlertViewV1 { alert_id: string; kind: 'SMOKE_GAS'; safety_level: 'S-1' | 'S0'; status: 'OPEN' | 'VIEWED'; occurred_at: string; version: number; source_refs: SourceRefV1[]; quality: QualityStatus }
export interface RequestCommandV1 { command_id: string; idempotency_key: string; expected_version: number; reason_code: 'ACKNOWLEDGE_VIEWED' }
export interface RequestReceiptV1 { request_id: string; audit_time: string; alert_id: string; status: 'RECORDED' }
export interface CareTaskV1 { task_id: string; kind: 'MEDICATION_DUE'; status: 'DUE' | 'REMINDING'; scheduled_at: string; evidence_state: 'UNKNOWN'; version: number; source_refs: SourceRefV1[] }
/** BFF timeline 的最小化事实投影；不包含原始事件 payload。 */
export interface TimelineEventV1 { event_id: string; event_type: string; occurred_at: string }
export interface CareRequestV1 { request_id: string; template: 'SEND_CARE_NOTE' | 'REMINDER_PREFERENCE'; status: 'RECORDED'; audit_time: string }
export type AgentFallback = 'NONE' | 'TEMPLATE_FALLBACK' | 'DETERMINISTIC_FALLBACK'
export interface AgentFactV1 { text: string; source_refs: string[] }
/** 与 contracts/schemas/agent-response.v1.json 保持字段与枚举一致。 */
export interface AgentResponseV1 {
  schema_version: 'AgentResponseV1'
  response_id: string
  agent_run_id: string
  channel: 'TERMINAL' | 'TTS' | 'FAMILY'
  message: string
  facts: AgentFactV1[]
  fallback: AgentFallback
  generator_version: string
}
export interface ConsentRevokeReceiptV1 { scope: string; status: 'REVOKED'; revoked_at: string; version: number }

export interface ErrorEnvelope {
  code: 'UNAUTHORIZED' | 'FORBIDDEN' | 'OFFLINE' | 'SCHEMA_INVALID' | 'UNAVAILABLE' | 'VERSION_CONFLICT' | 'INVALID_REQUEST' | 'INTERNAL_ERROR'
  message: string
  correlation_id: string
}
