import { describe, expect, it } from 'vitest'
import { MockCoreAdapter } from '../src/services/MockCoreAdapter'

describe('MockCoreAdapter', () => {
  it('returns only the fixture subject', async () => {
    await expect(new MockCoreAdapter().getDashboard('other-subject')).rejects.toThrow('FORBIDDEN')
  })
  it('returns a fresh object for each read', async () => {
    const api = new MockCoreAdapter(); const first = await api.getDashboard('subject-demo-parent-01'); const second = await api.getDashboard('subject-demo-parent-01')
    expect(first).not.toBe(second)
  })
})
