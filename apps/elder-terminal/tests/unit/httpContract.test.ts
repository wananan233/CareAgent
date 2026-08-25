import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { CoreApiAdapter } from '@/services/CoreApiAdapter';
import { makeCareRequest, type ConsentScope } from '@carehub/shared-contracts/elder';
import { i0Tokens, startI0Bff } from '../../../test-support/i0Bff';

let stop: (() => Promise<void>) | undefined;
let api: CoreApiAdapter;
beforeAll(async () => { const bff = await startI0Bff(); stop = bff.stop; api = new CoreApiAdapter({ baseUrl: bff.baseUrl, token: i0Tokens.elderA, householdId: 'household:i0-a' }); }, 15_000);
afterAll(async () => { await stop?.(); });

describe.sequential('Elder CoreApiAdapter real HTTP contract', () => {
  it('reads tasks through encoded scoped URLs', async () => {
    const tasks = await api.getTasks('user:elder-a');
    expect(tasks.ok && tasks.data.length).toBeGreaterThan(0);
  });
  it('reads alerts through encoded scoped URLs', async () => {
    const alerts = await api.getAlerts('user:elder-a');
    expect(alerts.ok).toBe(true);
  });
  it('reads timeline through encoded scoped URLs', async () => {
    const timeline = await api.getTimeline('user:elder-a');
    expect(timeline.ok && timeline.data.length).toBeGreaterThan(0);
  });
  it('reads report through encoded scoped URLs', async () => {
    const report = await api.chat('user:elder-a', '今日状态');
    expect(report.ok && report.data.facts.every(fact => fact.source_refs.length > 0)).toBe(true);
  });
  it('aggregates dashboard from protected reads', async () => { const dashboard = await api.getDashboard('user:elder-a'); expect(dashboard.ok && dashboard.data.family_member.household_id).toBe('household:i0-a'); });
  it('maps cross-household PDP denial to FORBIDDEN', async () => {
    const result = await api.getTasks('user:elder-b');
    expect(result.ok).toBe(false); if (!result.ok) expect(result.error.code).toBe('FORBIDDEN');
  });
  it('submits a controlled command through the scoped BFF route', async () => {
    const result = await api.submitRequest('user:elder-a', makeCareRequest({ command_id: 'elder-http-command', idempotency_key: 'elder-http-key', target_id: 'task:morning', expected_version: 1, kind: 'ACKNOWLEDGE_TASK', reason_code: 'ACKNOWLEDGE_VIEWED' }));
    expect(result.ok && result.data.status).toBe('RECORDED');
  });
  it('unwraps self-revoke consent and immediately denies the next protected read', async () => {
    const dashboard = await api.getDashboard('user:elder-a');
    expect(dashboard.ok).toBe(true);
    if (!dashboard.ok) return;
    const revoked = await api.revokeConsent('user:elder-a', dashboard.data.consent.scope as ConsentScope);
    expect(revoked.ok && revoked.data.status).toBe('REVOKED');
    const denied = await api.getTimeline('user:elder-a');
    expect(denied.ok).toBe(false);
    if (!denied.ok) expect(denied.error.code).toBe('FORBIDDEN');
  });
  it('maps an unavailable local endpoint to OFFLINE', async () => {
    const unavailable = new CoreApiAdapter({ baseUrl: 'http://127.0.0.1:1', token: i0Tokens.elderA, householdId: 'household:i0-a' });
    const result = await unavailable.getTasks('user:elder-a');
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe('OFFLINE');
  });
});
