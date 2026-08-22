import type { ReasonCode } from '@carehub/shared-contracts';

/** 原因码 → 低认知负担中文提示（不泄漏内部细节、不含身份/正文）。 */
export const ERROR_MESSAGES: Record<ReasonCode, string> = {
  NETWORK_OFFLINE: '当前离线，正在显示最后可信数据。',
  CONSENT_REVOKED: '暂无权限查看，请联系家属确认授权。',
  CONSENT_EXPIRED: '授权已过期，请重新授权。',
  SUBJECT_MISMATCH: '无权访问该账号的数据。',
  VERSION_CONFLICT: '数据已更新，请刷新后重试。',
  UPSTREAM_TIMEOUT: '服务响应超时，请稍后重试。',
  UPSTREAM_FAILED: '服务暂时不可用，请稍后重试。',
  SCHEMA_INVALID: '数据格式异常，已按“暂未确认”显示。',
  NOT_IMPLEMENTED: '该功能尚未接入，敬请期待。',
  AGENT_FALLBACK: '助手暂时无法解释，已显示固定提示。',
};

export function messageFor(reasonCode: ReasonCode): string {
  return ERROR_MESSAGES[reasonCode];
}
