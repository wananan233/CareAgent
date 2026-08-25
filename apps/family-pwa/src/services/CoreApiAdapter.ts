import type { AgentResponseV1, AlertViewV1, CareRequestV1, CareTaskV1, ConsentRevokeReceiptV1, DashboardV1, ErrorEnvelope, RequestCommandV1, RequestReceiptV1, TimelineEventV1 } from '@carehub/shared-contracts'

export interface CoreAdapter {
  getDashboard(subjectId: string): Promise<DashboardV1>
  getAlerts(subjectId: string): Promise<AlertViewV1[]>
  acknowledgeAlert(subjectId: string, alertId: string, command: RequestCommandV1): Promise<RequestReceiptV1>
  getTasks(subjectId: string): Promise<CareTaskV1[]>
  getTimeline(subjectId: string): Promise<TimelineEventV1[]>
  createCareRequest(subjectId: string, template: 'SEND_CARE_NOTE' | 'REMINDER_PREFERENCE', idempotencyKey: string): Promise<CareRequestV1>
  getReport(subjectId: string, mode: 'normal' | 'fallback'): Promise<AgentResponseV1>
  revokeConsent(subjectId: string, scope: string, expectedVersion: number): Promise<ConsentRevokeReceiptV1>
}

export class CoreApiAdapter implements CoreAdapter {
  constructor(private readonly options: { baseUrl: string; token: string; householdId: string; fetcher?: typeof fetch }) {}
  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await (this.options.fetcher ?? fetch)(`${this.options.baseUrl.replace(/\/$/, '')}${path}`, {
      ...init,
      headers: { Accept: 'application/json', Authorization: `Bearer ${this.options.token}`, ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...init.headers }
    })
    const payload: unknown = await response.json()
    if (!response.ok) {
      const error = payload as Partial<ErrorEnvelope>
      throw new Error(error.code ?? 'INTERNAL_ERROR')
    }
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
  async getReport(subjectId: string, mode: 'normal' | 'fallback'): Promise<AgentResponseV1> {
    if (mode === 'fallback') throw new Error('SIMULATED_FALLBACK_UNAVAILABLE')
    return this.request(`/v1/households/${encodeURIComponent(this.options.householdId)}/subjects/${encodeURIComponent(subjectId)}/report`)
  }
  async revokeConsent(subjectId: string, scope: string, expectedVersion: number): Promise<ConsentRevokeReceiptV1> {
    const body = await this.request<{ consent: { scope: string; status: 'REVOKED'; revoked_at: string; version: number } }>(this.path(subjectId, `consents/${encodeURIComponent(scope)}:revoke`), { method: 'POST', body: JSON.stringify({ command_id: crypto.randomUUID(), idempotency_key: crypto.randomUUID(), expected_version: expectedVersion }) })
    return body.consent
  }
}
