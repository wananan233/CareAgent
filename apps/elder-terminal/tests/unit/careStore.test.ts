import { describe, expect, it } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { useCareStore } from '@/stores/care';

describe('care store（数据视图模型，非事实源）', () => {
  it('refresh 加载首页/任务/时间线', async () => {
    setActivePinia(createPinia());
    const store = useCareStore();
    await store.refresh();
    expect(store.dashboard).toBeTruthy();
    expect(store.tasks.length).toBeGreaterThan(0);
    expect(store.timeline.length).toBeGreaterThan(0);
  });

  it('确认后任务状态 ACKNOWLEDGED、证据仍 UNKNOWN、版本 +1', async () => {
    setActivePinia(createPinia());
    const store = useCareStore();
    await store.refresh();

    const task = store.tasks[0];
    const result = await store.acknowledgeTask(task.task_id);
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.data.status).toBe('RECORDED');

    const updated = store.tasks.find((t) => t.task_id === task.task_id);
    expect(updated?.status).toBe('ACKNOWLEDGED');
    expect(updated?.evidence_state).toBe('UNKNOWN');
    expect(updated?.version).toBe(task.version + 1);
  });

  it('refresh 恢复：offline 故障清除后重取成功', async () => {
    setActivePinia(createPinia());
    const store = useCareStore();
    await store.refresh();

    store.api.setFault('offline');
    await store.refresh();
    expect(store.loadError).toBe('NETWORK_OFFLINE');

    store.api.setFault('none');
    await store.refresh();
    expect(store.loadError).toBeNull();
  });
});
