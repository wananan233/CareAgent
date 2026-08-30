import type { AgentResponseV1, AlertViewV1, CareRequestV1, CareTaskV1, ConsentRevokeReceiptV1, DashboardV1, ErrorEnvelope, RequestCommandV1, RequestReceiptV1, TimelineEventV1 } from '@carehub/shared-contracts'

/** All A0 read-only capabilities exposed by the CareHub BFF. */
export type AgentCapability = 'TODAY_STATUS' | 'DAILY_SUMMARY' | 'WEEKLY_TREND' | 'CHANGE_EXPLANATION' | 'READ_ONLY_QA'
export class CoreApiError extends Error { constructor(public readonly code: string, public readonly correlationId?: string) { super(code) } }

export interface CoreAdapter {
  getDashboard(subjectId: string): Promise<DashboardV1>
  getAlerts(subjectId: string): Promise<AlertViewV1[]>
  acknowledgeAlert(subjectId: string, alertId: string, command: RequestCommandV1): Promise<RequestReceiptV1>
  getTasks(subjectId: string): Promise<CareTaskV1[]>
  getTimeline(subjectId: string): Promise<TimelineEventV1[]>
  createCareRequest(subjectId: string, template: 'SEND_CARE_NOTE' | 'REMINDER_PREFERENCE', idempotencyKey: string): Promise<CareRequestV1>
  getAgent(subjectId: string, capability: AgentCapability): Promise<AgentResponseV1>
  askReadOnly(subjectId: string, question: string): Promise<AgentResponseV1>
  revokeConsent(subjectId: string, scope: string, expectedVersion: number): Promise<ConsentRevokeReceiptV1>
  relinquishConsent(subjectId: string, scope: string, expectedVersion: number): Promise<ConsentRevokeReceiptV1>
}

export class CoreApiAdapter implements CoreAdapter {
  constructor(private readonly options: { baseUrl: string; token: string; householdId: string; fetcher?: typeof fetch; timeoutMs?: number }) {}
  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), this.options.timeoutMs ?? 3_000)
    let response: Response
    try { response = await (this.options.fetcher ?? fetch)(`${this.options.baseUrl.replace(/\/$/, '')}${path}`, { ...init, signal: controller.signal, headers: { Accept: 'application/json', Authorization: `Bearer ${this.options.token}`, ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...init.headers } }) }
    catch (error) { throw new CoreApiError(controller.signal.aborted ? 'TIMEOUT' : 'OFFLINE') }
    finally { clearTimeout(timeout) }
    const raw = await response.text()
    let payload: unknown
    try { payload = raw ? JSON.parse(raw) : {} } catch { throw new CoreApiError('NON_JSON_RESPONSE', response.headers.get('X-Correlation-Id') ?? undefined) }
    if (!response.ok) {
      const error = payload as Partial<ErrorEnvelope>
      throw new CoreApiError(error.code ?? 'INTERNAL_ERROR', error.correlation_id ?? response.headers.get('X-Correlation-Id') ?? undefined)
    }
    if (payload === null || typeof payload !== 'object') throw new CoreApiError('SCHEMA_INVALID', response.headers.get('X-Correlation-Id') ?? undefined)
    return payload as T
  }
  async getDashboard(subjectId: string): Promise<DashboardV1> { return this.request(`/v1/households/${encodeURIComponent(this.options.householdId)}/subjects/${encodeURIComponent(subjectId)}/dashboard`) }
  async getAlerts(subjectId: string): Promise<AlertViewV1[]> {
    const view = await this.request<{ items: AlertViewV1[] }>(`/v1/households/${encodeURIComponent(this.options.householdId)}/subjects/${encodeURIComponent(subjectId)}/alerts`)
    return view.items
  }
  private path(subjectId: string, suffix: string): string { return `/v1/households/${encodeURIComponent(this.options.householdId)}/subjects/${encodeURIComponent(subjectId)}/${suffix}` }
  async acknowledgeAlert(subjectId: string, alertId: string, command: RequestCommandV1): Promise<RequestReceiptV1> { return this.request(this.path(subjectId, 'requests'), { method: 'POST', body: JSON.stringify({ ...command, action: 'ACKNOWLEDGE_ALERT', resource_id: alertId }) }) }
  async getTasks(subjectId: string): Promise<CareTaskV1[]> {
    const view = await this.request<{ items: CareTaskV1[] }>(`/v1/households/${encodeURIComponent(this.options.householdId)}/subjects/${encodeURIComponent(subjectId)}/tasks`)
    return view.items
  }
  async getTimeline(subjectId: string): Promise<TimelineEventV1[]> { return (await this.request<{ items: TimelineEventV1[] }>(this.path(subjectId, 'timeline'))).items }
  async createCareRequest(subjectId: string, template: 'SEND_CARE_NOTE' | 'REMINDER_PREFERENCE', idempotencyKey: string): Promise<CareRequestV1> { return this.request(this.path(subjectId, 'requests'), { method: 'POST', body: JSON.stringify({ command_id: crypto.randomUUID(), idempotency_key: idempotencyKey, expected_version: 1, action: 'CREATE_CARE_REQUEST', template }) }) }
  async getAgent(subjectId: string, capability: AgentCapability): Promise<AgentResponseV1> {
    if (capability === 'READ_ONLY_QA') throw new CoreApiError('READ_ONLY_QA_REQUIRES_QUESTION')
    const suffix: Record<Exclude<AgentCapability, 'READ_ONLY_QA'>, string> = { TODAY_STATUS: 'today-status', DAILY_SUMMARY: 'report', WEEKLY_TREND: 'weekly-trend', CHANGE_EXPLANATION: 'change-explanation' }
    return this.request(this.path(subjectId, suffix[capability]))
  }
  async askReadOnly(subjectId: string, question: string): Promise<AgentResponseV1> {
    return this.request(this.path(subjectId, 'qa'), { method: 'POST', body: JSON.stringify({ question }) })
  }
  async revokeConsent(subjectId: string, scope: string, expectedVersion: number): Promise<ConsentRevokeReceiptV1> {
    const body = await this.request<{ consent: { scope: string; status: 'REVOKED'; revoked_at: string; version: number } }>(this.path(subjectId, `consents/${encodeURIComponent(scope)}:revoke`), { method: 'POST', body: JSON.stringify({ command_id: crypto.randomUUID(), idempotency_key: crypto.randomUUID(), expected_version: expectedVersion }) })
    return body.consent
  }
  async relinquishConsent(subjectId: string, scope: string, expectedVersion: number): Promise<ConsentRevokeReceiptV1> {
    const body = await this.request<{ consent: { scope: string; status: 'REVOKED'; revoked_at: string; version: number } }>(this.path(subjectId, `consents/${encodeURIComponent(scope)}:relinquish`), { method: 'POST', body: JSON.stringify({ command_id: crypto.randomUUID(), idempotency_key: crypto.randomUUID(), expected_version: expectedVersion }) })
    return body.consent
  }
}
