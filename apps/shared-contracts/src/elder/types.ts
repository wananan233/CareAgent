/**
 * 老人端展示投影。
 *
 * 服务端事实 DTO 始终来自 ../family.ts；本模块只补充老人端页面所需的
 * 时间线、主任务组合视图和本地请求元数据，不再声明第二套 Core DTO。
 */
import type {
  AgentResponseV1 as CoreAgentResponseV1,
  AlertViewV1 as CoreAlertViewV1,
  CareTaskV1 as CoreCareTaskV1,
  ConsentViewV1 as CoreConsentViewV1,
  DashboardV1 as CoreDashboardV1,
  QualityStatus as CoreQualityStatus,
  RequestReceiptV1 as CoreRequestReceiptV1,
  SourceRefV1,
} from '../family'

export const API_VERSION = 'v1'
export const SIMULATED_DATA_LABEL = '模拟数据'

export type SubjectId = string
export type HouseholdId = string
export type QualityStatus = CoreQualityStatus
export type TaskKind = CoreCareTaskV1['kind']
export type TaskStatus = CoreCareTaskV1['status'] | 'ACKNOWLEDGED'
export type EvidenceState = CoreCareTaskV1['evidence_state']
export type SafetyLevel = CoreAlertViewV1['safety_level']
export type AlertKind = CoreAlertViewV1['kind']
export type AlertStatus = CoreAlertViewV1['status']
export type ConsentStatus = CoreConsentViewV1['status']
export type ConsentScope = 'timeline' | 'alerts' | 'tasks' | 'summary'

export interface EventSource {
  type: 'SIMULATOR'
  simulator_id: string
}

export interface Quality {
  status: QualityStatus
  reason?: string
}

/** Core SourceRef 的老人端可追溯展示扩展。 */
export interface SourceRef extends SourceRefV1 {
  ref_id: string
  kind: string
  occurred_at: string
}

export type CareEventType =
  | 'MEDICATION_DUE'
  | 'SMOKE_GAS'
  | 'LOW_QUALITY_ACTIVITY'

export interface CareEventV1 {
  event_id: string
  event_type: CareEventType
  occurred_at: string
  source: EventSource
  quality: Quality
  source_refs: SourceRef[]
}

/** Core 任务在老人端的展示投影；ACKNOWLEDGED 只表示“已看到提醒”。 */
export type CareTaskV1 = Omit<CoreCareTaskV1, 'status'> & {
  status: TaskStatus
}

export type AlertViewV1 = CoreAlertViewV1
export type AgentResponseV1 = CoreAgentResponseV1
export type ConsentViewV1 = CoreConsentViewV1
export type RequestReceiptV1 = CoreRequestReceiptV1

export interface Fact {
  key: string
  value: string
  confidence: QualityStatus
}

export interface UnknownItem {
  key: string
  note: string
}

export type Freshness = 'FRESH' | 'STALE'

export interface ContextSnapshotV1 {
  snapshot_id: string
  purpose: string
  as_of: string
  facts: Fact[]
  unknowns: UnknownItem[]
  freshness: Freshness
}

/** 家庭端 DashboardV1 加老人端单主任务展示字段。 */
export interface DashboardViewV1 extends CoreDashboardV1 {
  welcome: string
  primaryTask: CareTaskV1 | null
  nextAction: string
  safetyStatus: AlertStatus | 'NONE'
}

export type RequestKind = 'ACKNOWLEDGE_TASK' | 'VIEW_ALERT' | 'ACKNOWLEDGE_ALERT'

/** 包含家庭端 RequestCommandV1 的全部受控字段。 */
export interface CareRequestV1 {
  command_id: string
  idempotency_key: string
  expected_version: number
  reason_code: 'ACKNOWLEDGE_VIEWED'
  kind: RequestKind
  target_id: string
}
