import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { CoreApiAdapter } from '../src/services/CoreApiAdapter'
import { i0Tokens, startI0Bff } from '../../test-support/i0Bff'

let stop: (() => Promise<void>) | undefined; let api: CoreApiAdapter; let baseUrl: string
beforeAll(async () => { const bff = await startI0Bff(); stop = bff.stop; baseUrl = bff.baseUrl; api = new CoreApiAdapter({ baseUrl, token: i0Tokens.familyA, householdId: 'household:i0-a' }) }, 15_000)
afterAll(async () => { await stop?.() })

describe.sequential('Family CoreApiAdapter real HTTP contract', () => {
  it('gets dashboard through the scoped BFF route', async () => {
    expect((await api.getDashboard('user:elder-a')).family_member.household_id).toBe('household:i0-a')
  })
  it('gets tasks through the scoped BFF route', async () => {
    expect((await api.getTasks('user:elder-a')).length).toBeGreaterThan(0)
  })
  it('gets timeline through the scoped BFF route', async () => {
    expect((await api.getTimeline('user:elder-a')).length).toBeGreaterThan(0)
  })
  it('rejects another household', async () => {
    await expect(api.getTasks('user:elder-b')).rejects.toThrow('POLICY_DENIED')
  })
  it('returns authenticated error envelopes and restricted CORS preflight', async () => {
    const unauthorized = await fetch(`${baseUrl}/v1/households`); const denied = await fetch(`${baseUrl}/v1/households`, { method: 'OPTIONS', headers: { Origin: 'https://denied.example' } }); const allowed = await fetch(`${baseUrl}/v1/households`, { method: 'OPTIONS', headers: { Origin: 'http://127.0.0.1:5173' } });
    expect(unauthorized.status).toBe(401); expect((await unauthorized.json()).correlation_id).toBeTruthy(); expect(denied.status).toBe(403); expect(allowed.status).toBe(204); expect(allowed.headers.get('access-control-allow-origin')).toBe('http://127.0.0.1:5173');
  })
  it('returns correlation-bearing 409 and 422 envelopes without changing authorization', async () => {
    const path = `${baseUrl}/v1/households/household%3Ai0-a/subjects/user%3Aelder-a/consents/view:relinquish`
    const conflict = await fetch(path, { method: 'POST', headers: { Authorization: `Bearer ${i0Tokens.familyA}`, 'Content-Type': 'application/json' }, body: JSON.stringify({ command_id: 'family-http-conflict', idempotency_key: 'family-http-conflict-key', expected_version: 99 }) })
    const invalid = await fetch(`${baseUrl}/v1/households/household%3Ai0-a/subjects/user%3Aelder-a/requests`, { method: 'POST', headers: { Authorization: `Bearer ${i0Tokens.familyA}`, 'Content-Type': 'application/json' }, body: JSON.stringify({}) })
    const conflictBody = await conflict.json() as { code?: string; correlation_id?: string }
    const invalidBody = await invalid.json() as { code?: string; correlation_id?: string }
    expect(conflict.status).toBe(409); expect(conflictBody.code).toBe('VERSION_CONFLICT'); expect(conflictBody.correlation_id).toBeTruthy()
    expect(invalid.status).toBe(422); expect(invalidBody.code).toBe('INVALID_COMMAND'); expect(invalidBody.correlation_id).toBeTruthy()
  })
  it('posts a controlled command and unwraps the scoped consent revoke envelope', async () => {
    const receipt = await api.acknowledgeAlert('user:elder-a', 'alert:i0-a', { command_id: 'family-http-command', idempotency_key: 'family-http-key', expected_version: 1, reason_code: 'ACKNOWLEDGE_VIEWED' })
    expect(receipt.status).toBe('RECORDED')
    const dashboard = await api.getDashboard('user:elder-a')
    const revoked = await api.relinquishConsent('user:elder-a', dashboard.consent.scope, dashboard.consent.version)
    expect(revoked.status).toBe('REVOKED')
    await expect(api.getTimeline('user:elder-a')).rejects.toThrow('POLICY_DENIED')
  })
})
