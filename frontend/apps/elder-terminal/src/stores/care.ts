import { defineStore } from 'pinia';
import {
  isAgentResponseV1,
  makeCareRequest,
  makeError,
  safeParse,
} from '@carehub/shared-contracts';
import type {
  AgentResponseV1,
  AlertViewV1,
  CareEventV1,
  CareTaskV1,
  DashboardViewV1,
  ReasonCode,
  RequestKind,
  RequestReceiptV1,
  SubjectId,
} from '@carehub/shared-contracts';
import type { AdapterResult } from '@/services/adapter';
import { MockCoreAdapter } from '@/services/MockCoreAdapter';
import { DEMO_SUBJECT_ID } from '@/scenarios/fixtures';
import { useAppStore } from '@/stores/app';
import {
  OFFLINE_BLOCKED_LABEL,
  PENDING_RESUBMIT_LABEL,
  riskForRequest,
  type PendingResubmit,
} from '@/contracts/offlinePolicy';

/**
 * 老人端数据视图模型（非业务事实源）：事实仍来自 MockCoreAdapter，Pinia 仅缓存
 * 最近一次成功的投影用于渲染。业务状态必须带 snapshot/version/source/quality。
 */
export const useCareStore = defineStore('care', {
  state: () => ({
    subjectId: DEMO_SUBJECT_ID as SubjectId,
    api: new MockCoreAdapter(),
    dashboard: null as DashboardViewV1 | null,
    tasks: [] as CareTaskV1[],
    timeline: [] as CareEventV1[],
    alerts: [] as AlertViewV1[],
    agent: null as AgentResponseV1 | null,
    loading: false,
    submitting: false,
    agentLoading: false,
    loadError: null as ReasonCode | null,
    agentError: null as ReasonCode | null,
    receipt: null as RequestReceiptV1 | null,
    lastTrustedAt: null as string | null,
    pendingResubmit: null as PendingResubmit | null,
    blockedAction: null as string | null,
  }),
  getters: {
    /** 离线判定：应用网络标记，或最近一次加载返回 NETWORK_OFFLINE。 */
    isOffline(): boolean {
      return useAppStore().offline || this.loadError === 'NETWORK_OFFLINE';
    },
    /** 陈旧快照：离线且仍持有最后一次可信数据。 */
    stale(): boolean {
      return this.isOffline && this.lastTrustedAt !== null;
    },
  },
  actions: {
    async loadDashboard() {
      const r = await this.api.getDashboard(this.subjectId);
      if (r.ok) {
        this.dashboard = r.data;
        this.markTrusted();
      } else {
        this.loadError = r.error.error.reasonCode;
      }
    },
    async loadTasks() {
      const r = await this.api.getTasks(this.subjectId);
      if (r.ok) {
        this.tasks = r.data;
        this.markTrusted();
      } else {
        this.loadError = r.error.error.reasonCode;
      }
    },
    async loadTimeline() {
      const r = await this.api.getTimeline(this.subjectId);
      if (r.ok) {
        this.timeline = r.data;
        this.markTrusted();
      } else {
        this.loadError = r.error.error.reasonCode;
      }
    },
    async loadAlerts() {
      const r = await this.api.getAlerts(this.subjectId);
      if (r.ok) {
        this.alerts = r.data;
        this.markTrusted();
      } else {
        this.loadError = r.error.error.reasonCode;
      }
    },
    /** 刷新恢复：重新拉取首页/任务/时间线/告警（网络恢复后重试）。 */
    async refresh() {
      this.loading = true;
      this.loadError = null;
      try {
        await Promise.all([
          this.loadDashboard(),
          this.loadTasks(),
          this.loadTimeline(),
          this.loadAlerts(),
        ]);
      } finally {
        this.loading = false;
      }
    },
    /** 记录最后一次可信同步时间（成功加载后调用），并同步给系统状态条。 */
    markTrusted() {
      this.lastTrustedAt = new Date().toISOString();
      useAppStore().setLastSyncAt(this.lastTrustedAt);
      this.loadError = null;
    },
    /** 网络恢复：重新拉取全部数据。低风险待提交请求不在此自动执行。 */
    async recover() {
      await this.refresh();
    },
    /**
     * 离线写门控：高风险动作仅记录阻断文案（不排队）；低风险请求记录“待重新提交”占位。
     * 返回 true 表示请求被离线拦截，调用方不得继续提交。
     */
    gateOfflineRequest(kind: RequestKind, targetId: string): boolean {
      if (!this.isOffline) return false;
      if (riskForRequest(kind) === 'HIGH') {
        this.blockedAction = OFFLINE_BLOCKED_LABEL;
      } else {
        this.pendingResubmit = {
          kind,
          targetId,
          label: PENDING_RESUBMIT_LABEL,
          createdAt: new Date().toISOString(),
        };
      }
      return true;
    },
    /** 确认“已看到提醒”：携带 command_id / idempotency_key / expected_version。 */
    async acknowledgeTask(task_id: string): Promise<AdapterResult<RequestReceiptV1>> {
      const task = this.tasks.find((t) => t.task_id === task_id);
      if (!task) {
        return {
          ok: false,
          error: makeError('FAILED', 'SCHEMA_INVALID', '任务不存在', false),
        };
      }
      if (this.gateOfflineRequest('ACKNOWLEDGE_TASK', task_id)) {
        return {
          ok: false,
          error: makeError('OFFLINE', 'NETWORK_OFFLINE', PENDING_RESUBMIT_LABEL, false),
        };
      }
      this.submitting = true;
      try {
        const request = makeCareRequest({
          kind: 'ACKNOWLEDGE_TASK',
          targetId: task_id,
          expected_version: task.version,
        });
        const result = await this.api.submitRequest(this.subjectId, request);
        if (result.ok) {
          this.receipt = result.data;
          await this.loadTasks();
        } else {
          this.loadError = result.error.error.reasonCode;
        }
        return result;
      } finally {
        this.submitting = false;
      }
    },
    /** 记录“查看告警”（服务端允许的只读请求），无状态变更。 */
    async viewAlert(alert_id: string): Promise<void> {
      const alert = this.alerts.find((a) => a.alert_id === alert_id);
      if (!alert) return;
      if (this.gateOfflineRequest('VIEW_ALERT', alert_id)) return;
      const request = makeCareRequest({
        kind: 'VIEW_ALERT',
        targetId: alert_id,
        expected_version: alert.version,
      });
      await this.api.submitRequest(this.subjectId, request);
    },
    /** 确认“已看到告警”：携带 command_id / idempotency_key / expected_version。 */
    async acknowledgeAlert(alert_id: string): Promise<AdapterResult<RequestReceiptV1>> {
      const alert = this.alerts.find((a) => a.alert_id === alert_id);
      if (!alert) {
        return {
          ok: false,
          error: makeError('FAILED', 'SCHEMA_INVALID', '告警不存在', false),
        };
      }
      if (this.gateOfflineRequest('ACKNOWLEDGE_ALERT', alert_id)) {
        return {
          ok: false,
          error: makeError('OFFLINE', 'NETWORK_OFFLINE', OFFLINE_BLOCKED_LABEL, false),
        };
      }
      this.submitting = true;
      try {
        const request = makeCareRequest({
          kind: 'ACKNOWLEDGE_ALERT',
          targetId: alert_id,
          expected_version: alert.version,
        });
        const result = await this.api.submitRequest(this.subjectId, request);
        if (result.ok) {
          this.receipt = result.data;
          await this.loadAlerts();
        } else {
          this.loadError = result.error.error.reasonCode;
        }
        return result;
      } finally {
        this.submitting = false;
      }
    },
    /** 询问 Agent：回复必须通过 guard 校验；无来源事实/越界回复一律不渲染原始文本。 */
    async askAgent(text: string): Promise<void> {
      this.agentLoading = true;
      this.agent = null;
      this.agentError = null;
      try {
        const result = await this.api.chat(this.subjectId, text);
        if (!result.ok) {
          this.agentError = result.error.error.reasonCode;
          return;
        }
        const parsed = safeParse(isAgentResponseV1, result.data);
        if (!parsed.ok) {
          // 无来源事实 / 结构异常 → 模板失败态，绝不渲染原始模型文本。
          this.agentError = 'SCHEMA_INVALID';
          return;
        }
        this.agent = parsed.value;
        if (parsed.value.fallback) {
          this.agentError = 'AGENT_FALLBACK';
        }
      } finally {
        this.agentLoading = false;
      }
    },
  },
});
