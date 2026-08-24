import type { RequestKind } from '@carehub/shared-contracts/elder';

/** 离线写请求的风险分级：高风险不排队，低风险仅提示“待网络恢复后重新提交”。 */
export type OfflineRisk = 'HIGH' | 'LOW';

/** 高风险动作在离线时的阻断文案（绝不进入队列）。 */
export const OFFLINE_BLOCKED_LABEL = '离线时无法执行此操作，请联网后再试。';

/** 低风险请求在离线时的提示文案（不自动执行）。 */
export const PENDING_RESUBMIT_LABEL = '待网络恢复后重新提交';

/** 低风险请求的本地占位：只记录意图，网络恢复后由用户重新发起，绝不自动执行。 */
export interface PendingResubmit {
  kind: RequestKind;
  targetId: string;
  label: string;
  createdAt: string;
}

/**
 * 风险分级：安全告警确认（ACKNOWLEDGE_ALERT）涉及 S-1/S0 事件，离线排队会失真，属高风险；
 * 其余（ACKNOWLEDGE_TASK、VIEW_ALERT）为普通低风险请求。
 */
export function riskForRequest(kind: RequestKind): OfflineRisk {
  return kind === 'ACKNOWLEDGE_ALERT' ? 'HIGH' : 'LOW';
}
