import type {
  AlertKind,
  AlertStatus,
  CareEventType,
  EvidenceState,
  QualityStatus,
  ReasonCode,
  TaskKind,
  TaskStatus,
} from '@carehub/shared-contracts/elder';
import type { StateVariant } from '@/components/StateView.vue';

/** 质量 → 文案。LOW/CONFLICT/UNKNOWN 一律不得显示为“正常/已完成”。 */
export const QUALITY_LABEL: Record<QualityStatus, string> = {
  VALID: '信息可信',
  LOW: '信息待确认',
  CONFLICT: '信息冲突',
  UNKNOWN: '暂未确认',
};

/** 证据状态 → 文案。家庭端契约只允许 UNKNOWN，不推断服药事实。 */
export const EVIDENCE_LABEL: Record<EvidenceState, string> = {
  UNKNOWN: '暂未确认',
};

/** 任务状态 → 文案。ACKNOWLEDGED 只表达“已看到提醒”。 */
export const TASK_STATUS_LABEL: Record<TaskStatus, string> = {
  DUE: '待处理',
  REMINDING: '提醒中',
  ACKNOWLEDGED: '已看到提醒',
};

export const TASK_KIND_LABEL: Record<TaskKind, string> = {
  MEDICATION_DUE: '按时服药',
};

export const CARE_EVENT_LABEL: Record<CareEventType, string> = {
  MEDICATION_DUE: '服药提醒',
  SMOKE_GAS: '烟雾/燃气告警',
  LOW_QUALITY_ACTIVITY: '活动数据待确认',
};

/** 告警类型 → 文案。S-1/S0 为不可忽略安全事件。 */
export const ALERT_KIND_LABEL: Record<AlertKind, string> = {
  SMOKE_GAS: '烟雾/燃气',
};

/** 告警状态 → 文案。OPEN 表示仍须关注。 */
export const ALERT_STATUS_LABEL: Record<AlertStatus, string> = {
  OPEN: '待查看',
  VIEWED: '已查看',
};

/** 唯一允许的用户确认动作文案（红线：不得写“已吞服/已服药”）。 */
export const ACKNOWLEDGE_ACTION_LABEL = '我已看到提醒';

/** Agent 模板失败态：无来源事实/越界回复时渲染的固定文案（绝不渲染原始模型文本）。 */
export const AGENT_FAILURE_LABEL = '助手暂时无法给出解释，请稍后再试或联系家属。';

/** 加载失败原因 → 页面状态视图（离线/拒绝/失败）。 */
export interface LoadStateView {
  variant: StateVariant;
  title: string;
  description: string;
}

export function loadStateFor(reasonCode: ReasonCode | null): LoadStateView {
  switch (reasonCode) {
    case 'NETWORK_OFFLINE':
      return {
        variant: 'offline',
        title: '当前离线',
        description: '网络恢复后将自动更新，目前显示的是最后可信数据。',
      };
    case 'SUBJECT_MISMATCH':
    case 'FORBIDDEN':
    case 'CONSENT_REVOKED':
    case 'CONSENT_EXPIRED':
      return {
        variant: 'denied',
        title: '暂无权限',
        description: '无权访问该账号的数据，请联系家属确认授权。',
      };
    case 'UPSTREAM_TIMEOUT':
    case 'UPSTREAM_FAILED':
    case 'SCHEMA_INVALID':
    case 'NOT_IMPLEMENTED':
      return {
        variant: 'failed',
        title: '暂时无法加载',
        description: '服务暂时不可用，请稍后重试。',
      };
    default:
      return {
        variant: 'failed',
        title: '暂时无法加载',
        description: '发生未知错误，请稍后重试。',
      };
  }
}
