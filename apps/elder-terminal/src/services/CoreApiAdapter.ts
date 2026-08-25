import { makeError } from '@carehub/shared-contracts/elder';
import type { AgentResponseV1, AlertViewV1, CareEventV1, CareRequestV1, CareTaskV1, ConsentScope, ConsentViewV1, DashboardViewV1, ErrorEnvelope, RequestReceiptV1, SubjectId } from '@carehub/shared-contracts/elder';
import type { AdapterResult, ElderTerminalApi } from './adapter';

export interface CoreApiAdapterOptions { baseUrl: string; token: string; householdId: string; fetcher?: typeof fetch }
type BffView = { items: unknown[] };
const quality = (v: unknown): 'VALID' | 'LOW' | 'CONFLICT' | 'UNKNOWN' => v === 'LOW' ? 'LOW' : v === 'CONFLICT' ? 'CONFLICT' : v === 'UNKNOWN' ? 'UNKNOWN' : 'VALID';
const sourceRefs = (v: unknown, at: string) => (Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string') : []).map((id) => ({ type: 'SIMULATOR' as const, label: 'CareHub 合成事件', ref_id: id, kind: 'care_event', occurred_at: at }));

/** 真实 BFF 适配器：只访问版本化的家庭/主体路由，绝不直接读取 Core 数据库。 */
export class CoreApiAdapter implements ElderTerminalApi {
  constructor(private readonly options: CoreApiAdapterOptions) {}
  private path(subjectId: SubjectId, suffix: string): string { return `/v1/households/${encodeURIComponent(this.options.householdId)}/subjects/${encodeURIComponent(subjectId)}/${suffix}`; }
  private async request<T>(path: string, init: RequestInit = {}): Promise<AdapterResult<T>> {
    try {
      const response = await (this.options.fetcher ?? fetch)(`${this.options.baseUrl.replace(/\/$/, '')}${path}`, { ...init, headers: { Accept: 'application/json', Authorization: `Bearer ${this.options.token}`, ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...init.headers } });
      const body: unknown = await response.json();
      if (!response.ok) {
        const error = body as Partial<ErrorEnvelope>;
        const code = error.code === 'FORBIDDEN' ? 'FORBIDDEN' : error.code === 'UNAUTHORIZED' ? 'UNAUTHORIZED' : 'UNAVAILABLE';
        return { ok: false, error: makeError(code, error.reason_code ?? error.code ?? 'UPSTREAM_FAILED', error.message ?? '服务请求失败', Boolean(error.retryable)) };
      }
      return { ok: true, data: body as T };
    } catch { return { ok: false, error: makeError('OFFLINE', 'NETWORK_OFFLINE', '无法连接照护服务', true) }; }
  }
  async getTasks(subjectId: SubjectId): Promise<AdapterResult<CareTaskV1[]>> {
    const result = await this.request<BffView>(this.path(subjectId, 'tasks')); if (!result.ok) return result;
    const tasks = result.data.items.map((item): CareTaskV1 | null => {
      const raw = item && typeof item === 'object' ? item as Record<string, unknown> : null;
      const at = raw && typeof raw.scheduled_at === 'string' ? raw.scheduled_at : null; const id = raw && typeof raw.task_ref === 'string' ? raw.task_ref : null; const version = raw && typeof raw.version === 'number' ? raw.version : null;
      return !raw || !at || !id || version === null ? null : { task_id: id, kind: 'MEDICATION_DUE', status: raw.status === 'REMINDING' ? 'REMINDING' : 'DUE', evidence_state: 'UNKNOWN', scheduled_at: at, version, source_refs: sourceRefs(raw.source_refs, at).map(({ type, label }) => ({ type, label })) };
    });
    return tasks.some((item) => item === null) ? { ok: false, error: makeError('SCHEMA_INVALID', 'SCHEMA_INVALID', '任务响应不符合契约', false) } : { ok: true, data: tasks as CareTaskV1[] };
  }
  async getAlerts(subjectId: SubjectId): Promise<AdapterResult<AlertViewV1[]>> {
    const result = await this.request<BffView>(this.path(subjectId, 'alerts')); if (!result.ok) return result;
    const alerts = result.data.items.map((item): AlertViewV1 | null => {
      const raw = item && typeof item === 'object' ? item as Record<string, unknown> : null;
      if (!raw || typeof raw.alert_id !== 'string' || typeof raw.occurred_at !== 'string' || typeof raw.version !== 'number' || (raw.safety_level !== 'S-1' && raw.safety_level !== 'S0')) return null;
      return { alert_id: raw.alert_id, kind: 'SMOKE_GAS', safety_level: raw.safety_level, status: raw.status === 'VIEWED' ? 'VIEWED' : 'OPEN', occurred_at: raw.occurred_at, version: raw.version, source_refs: sourceRefs(raw.source_refs, raw.occurred_at).map(({ type, label }) => ({ type, label })), quality: quality(raw.quality) };
    });
    return alerts.some((item) => item === null) ? { ok: false, error: makeError('SCHEMA_INVALID', 'SCHEMA_INVALID', '告警响应不符合契约', false) } : { ok: true, data: alerts as AlertViewV1[] };
  }
  async getTimeline(subjectId: SubjectId): Promise<AdapterResult<CareEventV1[]>> {
    const result = await this.request<BffView>(this.path(subjectId, 'timeline')); if (!result.ok) return result;
    const events = result.data.items.map((item): CareEventV1 | null => {
      const raw = item && typeof item === 'object' ? item as Record<string, unknown> : null;
      if (!raw || typeof raw.event_id !== 'string' || typeof raw.occurred_at !== 'string') return null;
      const event_type = raw.event_type === 'ALERT_RAISED' ? 'SMOKE_GAS' : raw.event_type === 'MEDICATION_DUE' ? 'MEDICATION_DUE' : 'LOW_QUALITY_ACTIVITY';
      return { event_id: raw.event_id, event_type, occurred_at: raw.occurred_at, source: { type: 'SIMULATOR', simulator_id: 'carehub-bff' }, quality: { status: 'VALID' }, source_refs: [{ type: 'SIMULATOR', ref_id: raw.event_id, kind: 'care_event', label: 'CareHub 合成事件', occurred_at: raw.occurred_at }] };
    });
    return events.some((item) => item === null) ? { ok: false, error: makeError('SCHEMA_INVALID', 'SCHEMA_INVALID', '时间线响应不符合契约', false) } : { ok: true, data: events as CareEventV1[] };
  }
  async getDashboard(subjectId: SubjectId): Promise<AdapterResult<DashboardViewV1>> {
    const [dashboard, tasks, alerts] = await Promise.all([this.request<Record<string, unknown>>(this.path(subjectId, 'dashboard')), this.getTasks(subjectId), this.getAlerts(subjectId)]);
    if (!dashboard.ok) return dashboard; if (!tasks.ok) return tasks; if (!alerts.ok) return alerts;
    const now = typeof dashboard.data.server_time === 'string' ? dashboard.data.server_time : new Date().toISOString();
    return { ok: true, data: { snapshot_id: typeof dashboard.data.snapshot_id === 'string' ? dashboard.data.snapshot_id : 'bff-snapshot', server_time: now, last_updated_at: typeof dashboard.data.last_updated_at === 'string' ? dashboard.data.last_updated_at : now, quality: quality(dashboard.data.quality), source_refs: [{ type: 'SIMULATOR', label: 'CareHub BFF' }], family_member: { subject_id: subjectId, household_id: this.options.householdId, display_name: '当前用户', relationship: 'SELF' }, consent: { scope: 'view', status: 'ACTIVE', expires_at: '2099-01-01T00:00:00.000Z', version: 0 }, welcome: '您好，今天最重要的一件事如下。', primaryTask: tasks.data[0] ?? null, nextAction: tasks.data[0] ? '点击查看任务详情' : '查看今日状态', safetyStatus: alerts.data.some((alert) => alert.status === 'OPEN') ? 'OPEN' : 'NONE' } };
  }
  async submitRequest(subjectId: SubjectId, request: CareRequestV1): Promise<AdapterResult<RequestReceiptV1>> { return this.request<RequestReceiptV1>(this.path(subjectId, 'requests'), { method: 'POST', body: JSON.stringify({ command_id: request.command_id, idempotency_key: request.idempotency_key, expected_version: request.expected_version, action: request.kind, resource_id: request.target_id }) }); }
  async chat(subjectId: SubjectId, text: string): Promise<AdapterResult<AgentResponseV1>> { return text.trim() ? this.request<AgentResponseV1>(this.path(subjectId, 'report')) : { ok: false, error: makeError('INVALID_REQUEST', 'INVALID_REQUEST', '问题不能为空', false) }; }
  async revokeConsent(subjectId: SubjectId, scope: ConsentScope): Promise<AdapterResult<ConsentViewV1>> { return this.request<ConsentViewV1>(this.path(subjectId, `consents/${encodeURIComponent(scope)}:revoke`), { method: 'POST', body: JSON.stringify({ command_id: crypto.randomUUID(), idempotency_key: crypto.randomUUID(), expected_version: 1 }) }); }
  setFault(_fault: 'none' | 'offline' | 'denied' | 'failed' | 'timeout'): void { /* 真实 BFF 不接受客户端故障注入。 */ }
  setAgentFault(_fault: 'none' | 'timeout' | 'out_of_bounds' | 'no_source'): void { /* 真实 BFF 不接受客户端模型注入。 */ }
}
