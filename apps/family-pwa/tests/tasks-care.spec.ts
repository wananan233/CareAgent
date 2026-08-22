import { describe, expect, it } from 'vitest'
import { MockCoreAdapter } from '../src/services/MockCoreAdapter'
describe('F2 tasks and care', () => {
  it('keeps medication evidence unknown', async () => { const [task] = await new MockCoreAdapter().getTasks('subject-demo-parent-01'); expect(task.evidence_state).toBe('UNKNOWN') })
  it('deduplicates a preset care request', async () => { const api = new MockCoreAdapter(); const [a, b] = await Promise.all([api.createCareRequest('subject-demo-parent-01', 'SEND_CARE_NOTE', 'care-1'), api.createCareRequest('subject-demo-parent-01', 'SEND_CARE_NOTE', 'care-1')]); expect(a.request_id).toBe(b.request_id) })
  it('denies requests for another subject', async () => { await expect(new MockCoreAdapter().getTasks('other-subject')).rejects.toThrow('FORBIDDEN') })
})
