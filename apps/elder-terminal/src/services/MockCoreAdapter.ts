import {
  makeConsent,
  makeError,
  makeReceipt,
} from '@carehub/shared-contracts/elder';
import type {
  AgentResponseV1,
  AlertViewV1,
  CareEventV1,
  CareRequestV1,
  CareTaskV1,
  ConsentScope,
  ConsentViewV1,
  DashboardViewV1,
  RequestReceiptV1,
  SubjectId,
} from '@carehub/shared-contracts/elder';
import type { AdapterErr, AdapterResult, DevelopmentFaultInjection, ElderTerminalApi } from './adapter';
import {
  DEMO_SUBJECT_ID,
  fixtureAgentFallback,
  fixtureAgentNoSource,
  fixtureAgentResponse,
  fixtureAlerts,
  fixtureDashboard,
  fixtureTasks,
  fixtureTimeline,
} from '@/scenarios/fixtures';

export type MockFault = 'none' | 'offline' | 'denied' | 'failed' | 'timeout';

/** Agent 故障注入：模拟模型超时、越界回复与无来源事实。 */
export type AgentFault = 'none' | 'timeout' | 'out_of_bounds' | 'no_source';

export interface MockCoreAdapterOptions {
  fault?: MockFault;
  agentFault?: AgentFault;
  subjectId?: SubjectId;
}

/** 纯合成数据的适配器实现，用于在 C0-C4 就绪前完成所有页面与验收。 */
export class MockCoreAdapter implements ElderTerminalApi, DevelopmentFaultInjection {
  private fault: MockFault;
  private agentFault: AgentFault;
  private readonly subjectId: SubjectId;
  private readonly tasks: CareTaskV1[];
  private readonly timeline: CareEventV1[];
  private readonly alerts: AlertViewV1[];
  private readonly receipts = new Map<string, RequestReceiptV1>();

  constructor(options: MockCoreAdapterOptions = {}) {
    this.fault = options.fault ?? 'none';
    this.agentFault = options.agentFault ?? 'none';
    this.subjectId = options.subjectId ?? DEMO_SUBJECT_ID;
    this.tasks = fixtureTasks();
    this.timeline = fixtureTimeline();
    this.alerts = fixtureAlerts();
  }

  /** 故障注入开关（用于“刷新恢复”：offline → none 后重取即恢复）。 */
  setFault(fault: MockFault): void {
    this.fault = fault;
  }

  /** Agent 故障注入开关。 */
  setAgentFault(fault: AgentFault): void {
    this.agentFault = fault;
  }

  private faultError(): AdapterErr | null {
    switch (this.fault) {
      case 'offline':
        return { ok: false, error: makeError('OFFLINE', 'NETWORK_OFFLINE', '网络不可用', false) };
      case 'denied':
        return { ok: false, error: makeError('FORBIDDEN', 'SUBJECT_MISMATCH', '无权访问', false) };
      case 'failed':
        return { ok: false, error: makeError('UNAVAILABLE', 'UPSTREAM_FAILED', '服务不可用', true) };
      case 'timeout':
        return { ok: false, error: makeError('UNAVAILABLE', 'UPSTREAM_TIMEOUT', '服务响应超时', true) };
      default:
        return null;
    }
  }

  private check(subjectId: SubjectId): AdapterErr | null {
    if (subjectId !== this.subjectId) {
      return {
        ok: false,
        error: makeError('FORBIDDEN', 'SUBJECT_MISMATCH', '无权访问该账号', false),
      };
    }
    return this.faultError();
  }

  async getDashboard(subjectId: SubjectId): Promise<AdapterResult<DashboardViewV1>> {
    const denied = this.check(subjectId);
    if (denied) return denied;
    // 主任务必须与 getTasks 同源（同一 task_id/version），保证详情跳转与确认后状态一致。
    const dash = fixtureDashboard();
    return { ok: true, data: { ...dash, primaryTask: this.tasks[0] ?? null } };
  }

  async getTasks(subjectId: SubjectId): Promise<AdapterResult<CareTaskV1[]>> {
    return this.check(subjectId) ?? { ok: true, data: this.tasks.map((t) => ({ ...t })) };
  }

  async getTimeline(subjectId: SubjectId): Promise<AdapterResult<CareEventV1[]>> {
    return (
      this.check(subjectId) ??
      { ok: true, data: this.timeline.map((e) => ({ ...e, source_refs: [...e.source_refs] })) }
    );
  }

  async getAlerts(subjectId: SubjectId): Promise<AdapterResult<AlertViewV1[]>> {
    return (
      this.check(subjectId) ?? { ok: true, data: this.alerts.map((a) => ({ ...a })) }
    );
  }

  async submitRequest(
    subjectId: SubjectId,
    request: CareRequestV1,
  ): Promise<AdapterResult<RequestReceiptV1>> {
    const denied = this.check(subjectId);
    if (denied) return denied;

    // 幂等：同一 idempotency_key 只处理一次，重复提交返回同一回执。
    const cached = this.receipts.get(request.idempotency_key);
    if (cached) return { ok: true, data: { ...cached } };

    if (request.kind === 'ACKNOWLEDGE_TASK') {
      const task = this.tasks.find((t) => t.task_id === request.target_id);
      if (!task) {
        return {
          ok: false,
          error: makeError('SCHEMA_INVALID', 'SCHEMA_INVALID', '任务不存在', false),
        };
      }
      // 过期版本：expected_version 与当前不一致 → VERSION_CONFLICT（不缓存，需刷新后重试）。
      if (task.version !== request.expected_version) {
        return {
          ok: false,
          error: makeError('VERSION_CONFLICT', 'VERSION_CONFLICT', '任务版本已更新', false),
        };
      }
      // 应用确认：仅表达“已看到提醒”；证据状态保持 UNKNOWN（绝不推断“已吞服”）。
      task.status = 'ACKNOWLEDGED';
      task.version += 1;
    } else if (request.kind === 'VIEW_ALERT') {
      // 查看：服务端允许的只读动作，不改变告警状态。
      if (!this.alerts.some((a) => a.alert_id === request.target_id)) {
        return {
          ok: false,
          error: makeError('SCHEMA_INVALID', 'SCHEMA_INVALID', '告警不存在', false),
        };
      }
    } else if (request.kind === 'ACKNOWLEDGE_ALERT') {
      const alert = this.alerts.find((a) => a.alert_id === request.target_id);
      if (!alert) {
        return {
          ok: false,
          error: makeError('SCHEMA_INVALID', 'SCHEMA_INVALID', '告警不存在', false),
        };
      }
      if (alert.version !== request.expected_version) {
        return {
          ok: false,
          error: makeError('VERSION_CONFLICT', 'VERSION_CONFLICT', '告警版本已更新', false),
        };
      }
      // 确认仅表达“已看到告警”，绝不代表“关闭/取消”安全事件。
      alert.status = 'VIEWED';
      alert.version += 1;
    }

    const receipt = makeReceipt({ request_id: request.command_id, alert_id: request.target_id });
    this.receipts.set(request.idempotency_key, receipt);
    return { ok: true, data: receipt };
  }

  async chat(subjectId: SubjectId, text: string): Promise<AdapterResult<AgentResponseV1>> {
    const denied = this.check(subjectId);
    if (denied) return denied;

    // 模型超时：返回可重试的失败信封。
    if (this.agentFault === 'timeout') {
      return {
        ok: false,
        error: makeError('UNAVAILABLE', 'UPSTREAM_TIMEOUT', '模型响应超时', true),
      };
    }
    // 越界回复：模型产出超范围内容，替换为安全回退模板（不渲染原始文本）。
    if (this.agentFault === 'out_of_bounds') {
      return { ok: true, data: fixtureAgentFallback() };
    }
    // 无来源事实：返回结构上通过 TS 类型、但 guard 会拒绝的回复（事实无 source_refs）。
    if (this.agentFault === 'no_source') {
      return { ok: true, data: fixtureAgentNoSource() };
    }

    return {
      ok: true,
      data: text.trim() === '' ? fixtureAgentFallback() : fixtureAgentResponse(),
    };
  }

  async revokeConsent(
    subjectId: SubjectId,
    scope: ConsentScope,
  ): Promise<AdapterResult<ConsentViewV1>> {
    const denied = this.check(subjectId);
    if (denied) return denied;
    return {
      ok: true,
      data: makeConsent({ scope, status: 'REVOKED', expires_at: new Date().toISOString() }),
    };
  }
}
