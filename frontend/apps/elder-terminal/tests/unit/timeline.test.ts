import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import TimelinePage from '@/pages/TimelinePage.vue';
import { useCareStore } from '@/stores/care';

describe('时间线页', () => {
  it('展示事件、质量标识与来源（LOW/CONFLICT 原因可见）', async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const care = useCareStore();
    await care.loadTimeline();

    const wrapper = mount(TimelinePage, { global: { plugins: [pinia] } });

    expect(wrapper.text()).toContain('服药提醒');
    expect(wrapper.text()).toContain('活动数据待确认');
    expect(wrapper.text()).toContain('信息待确认'); // LOW
    expect(wrapper.text()).toContain('信息冲突'); // CONFLICT
    expect(wrapper.text()).toContain('SIMULATOR');
  });
});
