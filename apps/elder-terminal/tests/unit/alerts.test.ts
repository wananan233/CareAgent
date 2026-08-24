import { describe, expect, it } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { createMemoryHistory, createRouter } from 'vue-router';
import { makeCareRequest } from '@carehub/shared-contracts/elder';
import { routes } from '@/router';
import SafetyPage from '@/pages/SafetyPage.vue';
import AlertCard from '@/components/AlertCard.vue';
import GlobalSafetyCard from '@/components/GlobalSafetyCard.vue';
import { useCareStore } from '@/stores/care';
import { MockCoreAdapter } from '@/services/MockCoreAdapter';
import { DEMO_SUBJECT_ID } from '@/scenarios/fixtures';

const router = createRouter({ history: createMemoryHistory(), routes });

async function setupSafety() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const care = useCareStore();
  await care.loadAlerts();
  const wrapper = mount(SafetyPage, { global: { plugins: [pinia, router] } });
  return { care, wrapper };
}

describe('安全页（SafetyPage）', () => {
  it('展示家庭端契约规定的 SMOKE_GAS 告警', async () => {
    const { wrapper } = await setupSafety();
    expect(wrapper.text()).toContain('烟雾/燃气');
  });

  it('S-1/S0 告警卡片不提供关闭/取消按钮', async () => {
    const { wrapper } = await setupSafety();
    const dismissButtons = wrapper
      .findAll('button')
      .filter((b) => /关闭|取消/.test(b.text()));
    expect(dismissButtons.length).toBe(0);
  });

  it('确认告警后状态变为 VIEWED', async () => {
    const { care, wrapper } = await setupSafety();
    const card = wrapper.findAllComponents(AlertCard)[0];
    await card.find('button.alert-card__confirm').trigger('click');
    await flushPromises();
    expect(care.alerts[0].status).toBe('VIEWED');
  });
});

describe('全局安全卡（GlobalSafetyCard）', () => {
  it('展示最高级 S-1/S0 告警，且无关闭/取消按钮', async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const care = useCareStore();
    await care.loadAlerts();
    const wrapper = mount(GlobalSafetyCard, { global: { plugins: [pinia, router] } });
    await flushPromises();
    expect(wrapper.text()).toContain('S-1');
    expect(wrapper.text()).toContain('烟雾/燃气');
    expect(wrapper.text()).toContain('查看详情');
    expect(wrapper.text()).not.toContain('关闭');
    expect(wrapper.text()).not.toContain('取消');
  });
});

describe('adapter 告警请求（VIEW_ALERT / ACKNOWLEDGE_ALERT）', () => {
  it('VIEW_ALERT 为只读动作，不改变状态', async () => {
    const api = new MockCoreAdapter();
    const alerts = await api.getAlerts(DEMO_SUBJECT_ID);
    const alert = alerts.ok ? alerts.data[0] : null;
    expect(alert).toBeTruthy();

    const r = await api.submitRequest(
      DEMO_SUBJECT_ID,
      makeCareRequest({
        kind: 'VIEW_ALERT',
        target_id: alert!.alert_id,
        expected_version: alert!.version,
      }),
    );
    expect(r.ok).toBe(true);
    const after = await api.getAlerts(DEMO_SUBJECT_ID);
    expect(after.ok && after.data[0].status).toBe('OPEN');
  });

  it('ACKNOWLEDGE_ALERT 确认后状态 VIEWED 且版本 +1', async () => {
    const api = new MockCoreAdapter();
    const alerts = await api.getAlerts(DEMO_SUBJECT_ID);
    const alert = alerts.ok ? alerts.data[0] : null;
    expect(alert).toBeTruthy();

    const r = await api.submitRequest(
      DEMO_SUBJECT_ID,
      makeCareRequest({
        kind: 'ACKNOWLEDGE_ALERT',
        target_id: alert!.alert_id,
        expected_version: alert!.version,
      }),
    );
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.data.status).toBe('RECORDED');

    const after = await api.getAlerts(DEMO_SUBJECT_ID);
    const updated = after.ok ? after.data.find((a) => a.alert_id === alert!.alert_id) : undefined;
    expect(updated?.status).toBe('VIEWED');
    expect(updated?.version).toBe(alert!.version + 1);
  });

  it('ACKNOWLEDGE_ALERT 过期版本返回 VERSION_CONFLICT', async () => {
    const api = new MockCoreAdapter();
    const alerts = await api.getAlerts(DEMO_SUBJECT_ID);
    const alert = alerts.ok ? alerts.data[0] : null;

    const r = await api.submitRequest(
      DEMO_SUBJECT_ID,
      makeCareRequest({
        kind: 'ACKNOWLEDGE_ALERT',
        target_id: alert!.alert_id,
        expected_version: alert!.version + 999,
      }),
    );
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.error.code).toBe('VERSION_CONFLICT');
  });
});
