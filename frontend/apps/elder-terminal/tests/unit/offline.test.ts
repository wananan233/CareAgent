import { describe, expect, it } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { createMemoryHistory, createRouter } from 'vue-router';
import { routes } from '@/router';
import AppShell from '@/components/AppShell.vue';
import SystemStatusBar from '@/components/SystemStatusBar.vue';
import { useAppStore } from '@/stores/app';
import { useCareStore } from '@/stores/care';
import { MockCoreAdapter } from '@/services/MockCoreAdapter';
import { DEMO_SUBJECT_ID } from '@/scenarios/fixtures';
import {
  OFFLINE_BLOCKED_LABEL,
  PENDING_RESUBMIT_LABEL,
} from '@/contracts/offlinePolicy';

function setup() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const app = useAppStore();
  const care = useCareStore();
  return { app, care };
}

describe('首次离线（无可信快照）', () => {
  it('离线加载失败：不伪造数据、无可信快照、不标陈旧', async () => {
    const { care } = setup();
    care.api.setFault('offline');
    await care.refresh();

    expect(care.loadError).toBe('NETWORK_OFFLINE');
    expect(care.isOffline).toBe(true);
    expect(care.dashboard).toBeNull();
    expect(care.tasks).toHaveLength(0);
    expect(care.lastTrustedAt).toBeNull();
    expect(care.stale).toBe(false);
  });
});

describe('陈旧快照', () => {
  it('在线同步后离线：保留最后可信数据并标陈旧', async () => {
    const { care } = setup();
    await care.refresh();
    expect(care.lastTrustedAt).not.toBeNull();
    const taskCount = care.tasks.length;

    care.api.setFault('offline');
    await care.refresh();

    expect(care.loadError).toBe('NETWORK_OFFLINE');
    expect(care.tasks).toHaveLength(taskCount);
    expect(care.stale).toBe(true);
  });
});

describe('网络恢复', () => {
  it('recover 清除离线并刷新，陈旧标记消失', async () => {
    const { care } = setup();
    await care.refresh();
    care.api.setFault('offline');
    await care.refresh();
    expect(care.stale).toBe(true);

    care.api.setFault('none');
    await care.recover();

    expect(care.loadError).toBeNull();
    expect(care.isOffline).toBe(false);
    expect(care.stale).toBe(false);
  });
});

describe('API 超时', () => {
  it('timeout 故障返回可重试 UPSTREAM_TIMEOUT', async () => {
    const api = new MockCoreAdapter({ fault: 'timeout' });
    const r = await api.getDashboard(DEMO_SUBJECT_ID);
    expect(r.ok).toBe(false);
    if (!r.ok) {
      expect(r.error.error.code).toBe('FAILED');
      expect(r.error.error.reasonCode).toBe('UPSTREAM_TIMEOUT');
      expect(r.error.error.retryable).toBe(true);
    }
  });

  it('care store 在超时下 loadError 为 UPSTREAM_TIMEOUT', async () => {
    const { care } = setup();
    care.api.setFault('timeout');
    await care.refresh();
    expect(care.loadError).toBe('UPSTREAM_TIMEOUT');
  });
});

describe('离线写门控', () => {
  it('低风险 ACKNOWLEDGE_TASK：记录待重新提交且不真正提交', async () => {
    const { app, care } = setup();
    await care.refresh();
    const task = care.tasks[0];
    app.setOffline(true);

    const result = await care.acknowledgeTask(task.taskId);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.error.reasonCode).toBe('NETWORK_OFFLINE');
    expect(care.pendingResubmit?.kind).toBe('ACKNOWLEDGE_TASK');
    expect(care.pendingResubmit?.targetId).toBe(task.taskId);
    expect(care.pendingResubmit?.label).toBe(PENDING_RESUBMIT_LABEL);
    expect(care.blockedAction).toBeNull();

    const after = care.tasks.find((t) => t.taskId === task.taskId);
    expect(after?.status).toBe('DUE');
    expect(after?.version).toBe(task.version);
  });

  it('高风险 ACKNOWLEDGE_ALERT：阻断且不排队', async () => {
    const { app, care } = setup();
    await care.refresh();
    const alert = care.alerts[0];
    app.setOffline(true);

    const result = await care.acknowledgeAlert(alert.alertId);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.error.reasonCode).toBe('NETWORK_OFFLINE');
    expect(care.blockedAction).toBe(OFFLINE_BLOCKED_LABEL);
    expect(care.pendingResubmit).toBeNull();

    const after = care.alerts.find((a) => a.alertId === alert.alertId);
    expect(after?.status).toBe('ACTIVE');
    expect(after?.version).toBe(alert.version);
  });

  it('低风险 VIEW_ALERT：记录待重新提交且不提交', async () => {
    const { app, care } = setup();
    await care.refresh();
    const alert = care.alerts[0];
    app.setOffline(true);

    await care.viewAlert(alert.alertId);
    expect(care.pendingResubmit?.kind).toBe('VIEW_ALERT');
    expect(care.blockedAction).toBeNull();

    const after = care.alerts.find((a) => a.alertId === alert.alertId);
    expect(after?.status).toBe('ACTIVE');
  });

  it('网络恢复后待重新提交请求不被自动执行', async () => {
    const { app, care } = setup();
    await care.refresh();
    const task = care.tasks[0];
    app.setOffline(true);
    await care.acknowledgeTask(task.taskId);
    expect(care.pendingResubmit).not.toBeNull();

    app.setOffline(false);
    await care.recover();
    expect(care.loadError).toBeNull();
    expect(care.pendingResubmit).not.toBeNull();

    const after = care.tasks.find((t) => t.taskId === task.taskId);
    expect(after?.status).toBe('DUE');
  });
});

describe('网络事件驱动的恢复刷新', () => {
  it('offline 事件标记离线，online 事件恢复并刷新', async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const app = useAppStore();
    const care = useCareStore();
    await care.refresh();

    const router = createRouter({ history: createMemoryHistory(), routes });
    mount(AppShell, { global: { plugins: [pinia, router] } });

    window.dispatchEvent(new Event('offline'));
    expect(app.offline).toBe(true);

    window.dispatchEvent(new Event('online'));
    await flushPromises();
    expect(app.offline).toBe(false);
    expect(care.loadError).toBeNull();
    expect(care.lastTrustedAt).not.toBeNull();
  });
});

describe('SystemStatusBar 陈旧标识', () => {
  it('离线且持有快照时显示“陈旧数据”', () => {
    setActivePinia(createPinia());
    const app = useAppStore();
    app.setOffline(true);
    app.setLastSyncAt(new Date().toISOString());
    const wrapper = mount(SystemStatusBar);
    expect(wrapper.text()).toContain('陈旧数据');
  });

  it('离线但无快照时不显示“陈旧数据”', () => {
    setActivePinia(createPinia());
    const app = useAppStore();
    app.setOffline(true);
    const wrapper = mount(SystemStatusBar);
    expect(wrapper.text()).toContain('离线');
    expect(wrapper.text()).not.toContain('陈旧数据');
  });
});
