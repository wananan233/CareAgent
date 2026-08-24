import type { AgentResponseV1, AlertViewV1, CareRequestV1, CareTaskV1, ConsentRevokeReceiptV1, DashboardV1, RequestCommandV1, RequestReceiptV1 } from '@carehub/shared-contracts'
import { isDashboardV1 } from '@/contracts/guard'
import { dailyReportFixture, fallbackReportFixture, familyDashboardFixture, medicationTaskFixture, smokeGasAlertFixture } from '@/scenarios/fixtures'
import type { CoreAdapter } from './CoreApiAdapter'

export class MockCoreAdapter implements CoreAdapter {
  private readonly receipts = new Map<string, RequestReceiptV1>()
  private readonly careRequests = new Map<string, CareRequestV1>()
  private revoked = false
  async getDashboard(subjectId: string): Promise<DashboardV1> {
    if (subjectId !== familyDashboardFixture.family_member.subject_id) throw new Error('FORBIDDEN')
    if (this.revoked) throw new Error('FORBIDDEN'); const payload = structuredClone(familyDashboardFixture)
    if (!isDashboardV1(payload)) throw new Error('SCHEMA_INVALID')
    return payload
  }
  async getAlerts(subjectId: string): Promise<AlertViewV1[]> { if (subjectId !== familyDashboardFixture.family_member.subject_id) throw new Error('FORBIDDEN'); return [structuredClone(smokeGasAlertFixture)] }
  async acknowledgeAlert(subjectId: string, alertId: string, command: RequestCommandV1): Promise<RequestReceiptV1> {
    if (subjectId !== familyDashboardFixture.family_member.subject_id) throw new Error('FORBIDDEN')
    if (alertId !== smokeGasAlertFixture.alert_id || command.reason_code !== 'ACKNOWLEDGE_VIEWED') throw new Error('UNAVAILABLE')
    if (command.expected_version !== smokeGasAlertFixture.version) throw new Error('VERSION_CONFLICT')
    const old = this.receipts.get(command.idempotency_key); if (old) return old
    const receipt = { request_id: `req-${command.command_id}`, audit_time: '2026-08-14T10:26:00+08:00', alert_id: alertId, status: 'RECORDED' as const }; this.receipts.set(command.idempotency_key, receipt); return receipt
  }
  async getTasks(subjectId: string): Promise<CareTaskV1[]> { if (subjectId !== familyDashboardFixture.family_member.subject_id) throw new Error('FORBIDDEN'); return [structuredClone(medicationTaskFixture)] }
  async createCareRequest(subjectId: string, template: 'SEND_CARE_NOTE' | 'REMINDER_PREFERENCE', idempotencyKey: string): Promise<CareRequestV1> { if (subjectId !== familyDashboardFixture.family_member.subject_id) throw new Error('FORBIDDEN'); const old = this.careRequests.get(idempotencyKey); if (old) return old; const value = { request_id: `care-${idempotencyKey}`, template, status: 'RECORDED' as const, audit_time: '2026-08-14T11:00:00+08:00' }; this.careRequests.set(idempotencyKey, value); return value }
  async getReport(subjectId: string, mode: 'normal' | 'fallback'): Promise<AgentResponseV1> { if (subjectId !== familyDashboardFixture.family_member.subject_id) throw new Error('FORBIDDEN'); return structuredClone(mode === 'fallback' ? fallbackReportFixture : dailyReportFixture) }
  async revokeConsent(subjectId: string, scope: string, expectedVersion: number): Promise<ConsentRevokeReceiptV1> { if (subjectId !== familyDashboardFixture.family_member.subject_id || scope !== familyDashboardFixture.consent.scope) throw new Error('FORBIDDEN'); if (expectedVersion !== familyDashboardFixture.consent.version) throw new Error('VERSION_CONFLICT'); this.revoked = true; return { scope, status: 'REVOKED', revoked_at: '2026-08-14T11:30:00+08:00', version: expectedVersion + 1 } }
}
