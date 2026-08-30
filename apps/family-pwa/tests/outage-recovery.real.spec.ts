import { afterAll, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import router from '../src/router'
import { CoreApiAdapter } from '../src/services/CoreApiAdapter'
import { i0Tokens, startI0Bff } from '../../test-support/i0Bff'

const waitFor = async (check: () => boolean) => { const end = Date.now() + 6_000; while (Date.now() < end) { if (check()) return; await new Promise(resolve => setTimeout(resolve, 25)) } throw new Error('恢复超时') }
let first: Awaited<ReturnType<typeof startI0Bff>>; let second: Awaited<ReturnType<typeof startI0Bff>> | undefined
afterAll(async () => { await second?.stop(); await first?.stop() })
describe.sequential('FamilyShell 真实 BFF outage 自动恢复', () => {
  it('保留 dashboard 快照并在 same-port restart 后自动恢复，无命令副作用', async () => {
    first = await startI0Bff()
    const api = new CoreApiAdapter({ baseUrl: first.baseUrl, token: i0Tokens.familyA, householdId: 'household:i0-a' })
    expect((await api.getDashboard('user:elder-a')).family_member.household_id).toBe('household:i0-a')
    vi.resetModules()
    vi.doMock('@/services/adapter', () => ({ coreAdapter: api, currentSubjectId: 'user:elder-a' }))
    const { default: FamilyShell } = await import('../src/pages/FamilyShell.vue')
    await router.push('/')
    await router.isReady()
    const wrapper = mount(FamilyShell, { global: { plugins: [createPinia(), router], stubs: { AppIcon: true } } })
    await waitFor(() => !wrapper.find('[aria-busy=\"true\"]').exists())
    expect(wrapper.html()).not.toContain('aria-busy')
    expect(wrapper.text()).toContain('我的家庭')
    await waitFor(() => wrapper.text().includes('CareHub 智能照护'))
    await first.stop()
    await waitFor(() => wrapper.text().includes('当前离线'))
    expect(wrapper.text()).toContain('CareHub 智能照护')
    second = await startI0Bff({ port: Number(new URL(first.baseUrl).port) })
    await waitFor(() => !wrapper.text().includes('当前离线'))
    expect(wrapper.text()).toContain('CareHub 智能照护')
    wrapper.unmount()
  }, 20_000)
})
