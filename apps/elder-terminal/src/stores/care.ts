import { defineStore } from 'pinia';
import {
  isAgentResponseV1,
  makeCareRequest,
  makeError,
  safeParse,
} from '@carehub/shared-contracts/elder';
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
} from '@carehub/shared-contracts/elder';
import type { AdapterResult, DevelopmentFaultInjection, ElderTerminalApi } from '@/services/adapter';
import { createElderTerminalApi, runtimeSubjectId } from '@/services/runtime';
import { useAppStore } from '@/stores/app';
import {
  OFFLINE_BLOCKED_LABEL,
  PENDING_RESUBMIT_LABEL,
  riskForRequest,
  type PendingResubmit,
} from '@/contracts/offlinePolicy';

/**
 * 老人端数据视图模型（非业务事实源）：事实来自受控 BFF 或开发 Mock，Pinia 仅缓存
 * 最近一次成功的投影用于渲染。业务状态必须带 snapshot/version/source/quality。
 */
export const useCareStore = defineStore('care', {
  state: () => ({
    subjectId: runtimeSubjectId as SubjectId,
    // 故障注入仅由开发/测试 Mock 提供；正式运行时绝不会调用这些可选能力。
    api: createElderTerminalApi() as ElderTerminalApi & DevelopmentFaultInjection,
    dashboard: null as DashboardViewV1 | null,
    tasks: [] as CareTaskV1[],
    timeline: [] as CareEventV1[],
    alerts: [] as AlertViewV1[],
    agent: null as AgentResponseV1 | null,
    loading: false,
    submitting: false,
    agentLoading: false,
    loadError: null as ReasonCode | null,
    loadCorrelationId: null as string | null,
    agentError: null as ReasonCode | null,
    receipt: null as RequestReceiptV1 | null,
    lastTrustedAt: null as string | null,
    pendingResubmit: null as PendingResubmit | null,
    blockedAction: null as string | null,
    recoveryTimer: null as ReturnType<typeof setTimeout> | null,
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
        this.loadError = r.error.reason_code ?? r.error.code; this.loadCorrelationId = r.error.correlation_id;
      }
    },
    async loadTasks() {
      const r = await this.api.getTasks(this.subjectId);
      if (r.ok) {
        this.tasks = r.data;
        this.markTrusted();
      } else {
        this.loadError = r.error.reason_code ?? r.error.code; this.loadCorrelationId = r.error.correlation_id;
      }
    },
    async loadTimeline() {
      const r = await this.api.getTimeline(this.subjectId);
      if (r.ok) {
        this.timeline = r.data;
        this.markTrusted();
      } else {
        this.loadError = r.error.reason_code ?? r.error.code; this.loadCorrelationId = r.error.correlation_id;
      }
    },
    async loadAlerts() {
      const r = await this.api.getAlerts(this.subjectId);
      if (r.ok) {
        this.alerts = r.data;
        this.markTrusted();
      } else {
        this.loadError = r.error.reason_code ?? r.error.code; this.loadCorrelationId = r.error.correlation_id;
      }
    },
    /** 刷新恢复：重新拉取首页/任务/时间线/告警（网络恢复后重试）。 */
    async refresh() {
      this.loading = true;
      this.loadError = null;
      this.loadCorrelationId = null;
      try {
        await Promise.all([
          this.loadDashboard(),
          this.loadTasks(),
          this.loadTimeline(),
          this.loadAlerts(),
        ]);
      } finally {
        this.loading = false;
        if (this.loadError === 'NETWORK_OFFLINE') this.scheduleRecovery();
        else this.stopRecovery();
      }
    },
    /** BFF 不可达时仅重试只读同步；不重放任何受控命令。 */
    scheduleRecovery() {
      if (this.recoveryTimer) return;
      this.recoveryTimer = setTimeout(() => {
        this.recoveryTimer = null;
        void this.refresh();
      }, 1_000);
    },
    stopRecovery() {
      if (this.recoveryTimer) clearTimeout(this.recoveryTimer);
      this.recoveryTimer = null;
    },
    /** 记录最后一次可信同步时间（成功加载后调用），并同步给系统状态条。 */
    markTrusted() {
      this.lastTrustedAt = new Date().toISOString();
      useAppStore().setLastSyncAt(this.lastTrustedAt);
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
          error: makeError('SCHEMA_INVALID', 'SCHEMA_INVALID', '任务不存在', false),
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
          target_id: task_id,
          expected_version: task.version,
        });
        const result = await this.api.submitRequest(this.subjectId, request);
        if (result.ok) {
          this.receipt = result.data;
          await this.loadTasks();
        } else {
          this.loadError = result.error.reason_code ?? result.error.code;
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
        target_id: alert_id,
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
          error: makeError('SCHEMA_INVALID', 'SCHEMA_INVALID', '告警不存在', false),
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
          target_id: alert_id,
          expected_version: alert.version,
        });
        const result = await this.api.submitRequest(this.subjectId, request);
        if (result.ok) {
          this.receipt = result.data;
          await this.loadAlerts();
        } else {
          this.loadError = result.error.reason_code ?? result.error.code;
        }
        return result;
      } finally {
        this.submitting = false;
      }
    },
    /** 询问 Agent：回复必须通过 guard 校验；无来源事实/越界回复一律不渲染原始文本。 */
    async askAgent(capability: 'TODAY_STATUS' | 'DAILY_SUMMARY' | string = 'TODAY_STATUS'): Promise<void> {
      this.agentLoading = true;
      this.agent = null;
      this.agentError = null;
      try {
        // Legacy callers may pass explanatory button text; that never becomes a free-form
        // prompt. It deterministically maps to the BFF's TODAY_STATUS projection.
        const purpose = capability === 'DAILY_SUMMARY' ? 'DAILY_SUMMARY' : 'TODAY_STATUS';
        const result = await this.api.getAgent(this.subjectId, purpose);
        if (!result.ok) {
          this.agentError = result.error.reason_code ?? result.error.code;
          return;
        }
        const parsed = safeParse(isAgentResponseV1, result.data);
        if (!parsed.ok) {
          // 无来源事实 / 结构异常 → 模板失败态，绝不渲染原始模型文本。
          this.agentError = 'SCHEMA_INVALID';
          return;
        }
        this.agent = parsed.value;
        if (parsed.value.fallback !== 'NONE') {
          this.agentError = 'AGENT_FALLBACK';
        }
      } finally {
        this.agentLoading = false;
      }
    },
  },
});
