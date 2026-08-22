import { describe, expect, it } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { createMemoryHistory, createRouter } from 'vue-router';
import { routes } from '@/router';
import HomePage from '@/pages/HomePage.vue';
import { useCareStore } from '@/stores/care';

const router = createRouter({ history: createMemoryHistory(), routes });

async function setup() {
  const pinia = createPinia();
  setActivePinia(pinia);
  const care = useCareStore();
  await care.refresh();
  const wrapper = mount(HomePage, { global: { plugins: [pinia, router] } });
  return { care, wrapper };
}

describe('今日首页', () => {
  it('展示欢迎语、主任务与今日任务列表', async () => {
    const { wrapper } = await setup();
    expect(wrapper.text()).toContain('您好');
    expect(wrapper.text()).toContain('今日任务');
    expect(wrapper.text()).toContain('按时服药');
  });

  it('离线时展示离线状态视图', async () => {
    const { care, wrapper } = await setup();
    care.api.setFault('offline');
    await care.refresh();
    await flushPromises();
    expect(wrapper.text()).toContain('当前离线');
  });
});
