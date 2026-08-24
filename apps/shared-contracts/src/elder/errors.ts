import type { ErrorEnvelope as CoreErrorEnvelope } from '../family'

export type ErrorCode = CoreErrorEnvelope['code']
export type ReasonCode =
  | ErrorCode
  | 'NETWORK_OFFLINE'
  | 'CONSENT_REVOKED'
  | 'CONSENT_EXPIRED'
  | 'SUBJECT_MISMATCH'
  | 'UPSTREAM_TIMEOUT'
  | 'UPSTREAM_FAILED'
  | 'NOT_IMPLEMENTED'
  | 'AGENT_FALLBACK'

/** 家庭端扁平 ErrorEnvelope；reason_code/retryable 是老人端安全反馈扩展。 */
export interface ErrorEnvelope extends CoreErrorEnvelope {
  reason_code?: ReasonCode
  retryable?: boolean
}
