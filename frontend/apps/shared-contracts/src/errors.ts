export type ErrorCode =
  | 'OFFLINE'
  | 'DENIED'
  | 'FAILED'
  | 'VALIDATION_ERROR'
  | 'NOT_IMPLEMENTED';

export type ReasonCode =
  | 'NETWORK_OFFLINE'
  | 'CONSENT_REVOKED'
  | 'CONSENT_EXPIRED'
  | 'SUBJECT_MISMATCH'
  | 'VERSION_CONFLICT'
  | 'UPSTREAM_TIMEOUT'
  | 'UPSTREAM_FAILED'
  | 'SCHEMA_INVALID'
  | 'NOT_IMPLEMENTED'
  | 'AGENT_FALLBACK';

/**
 * 固定错误信封。日志只允许携带 correlationId / route / reasonCode / duration，
 * 禁止写入消息正文、身份字段或 Token。
 */
export interface ErrorEnvelope {
  error: {
    code: ErrorCode;
    reasonCode: ReasonCode;
    message: string;
    correlationId: string;
    route?: string;
    retryable: boolean;
  };
  version: string;
}
