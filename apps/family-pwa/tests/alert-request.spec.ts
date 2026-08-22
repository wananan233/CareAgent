import { describe, expect, it } from 'vitest'
import { MockCoreAdapter } from '../src/services/MockCoreAdapter'
describe('F1 alert acknowledgement', () => {
  it('deduplicates the viewed request by idempotency key', async () => { const api = new MockCoreAdapter(); const c = { command_id: 'c1', idempotency_key: 'same', expected_version: 3, reason_code: 'ACKNOWLEDGE_VIEWED' as const }; const [a, b] = await Promise.all([api.acknowledgeAlert('subject-demo-parent-01', 'alert-smoke-gas-001', c), api.acknowledgeAlert('subject-demo-parent-01', 'alert-smoke-gas-001', c)]); expect(a.request_id).toBe(b.request_id) })
  it('rejects a stale alert version', async () => { await expect(new MockCoreAdapter().acknowledgeAlert('subject-demo-parent-01', 'alert-smoke-gas-001', { command_id: 'c2', idempotency_key: 'stale', expected_version: 2, reason_code: 'ACKNOWLEDGE_VIEWED' })).rejects.toThrow('VERSION_CONFLICT') })
})
