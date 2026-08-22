import { describe, expect, it } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { createMemoryHistory, createRouter } from 'vue-router';
import { routes } from '@/router';
import TaskDetailPage from '@/pages/TaskDetailPage.vue';
import { useCareStore } from '@/stores/care';
import { ACKNOWLEDGE_ACTION_LABEL } from '@/contracts/displayMapping';

async function setup() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const care = useCareStore();
  await care.refresh();

  const taskId = care.tasks[0].taskId;
  const router = createRouter({ history: createMemoryHistory(), routes });
  await router.push(`/task/${taskId}`);
  await router.isReady();

  const wrapper = mount(TaskDetailPage, { global: { plugins: [pinia, router] } });
  return { care, wrapper, taskId };
}

describe('任务详情页', () => {
  it('渲染任务字段、来源与“我已看到提醒”按钮', async () => {
    const { wrapper } = await setup();
    expect(wrapper.text()).toContain('按时服药');
    expect(wrapper.text()).toContain('暂未确认');
    expect(wrapper.text()).toContain('模拟数据');
    expect(wrapper.text()).toContain(ACKNOWLEDGE_ACTION_LABEL);
  });

  it('点击确认后状态变为“已看到提醒”、证据仍“暂未确认”', async () => {
    const { care, wrapper, taskId } = await setup();
    await wrapper.find('button.detail__action').trigger('click');
    await flushPromises();

    const task = care.tasks.find((t) => t.taskId === taskId);
    expect(task?.status).toBe('ACKNOWLEDGED');
    expect(task?.evidenceState).toBe('UNKNOWN');
    expect(wrapper.text()).toContain('确认请求已接收');
  });
});
