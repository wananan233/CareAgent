import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import SystemStatusBar from '@/components/SystemStatusBar.vue';
import { useAppStore } from '@/stores/app';

describe('SystemStatusBar 系统状态条', () => {
  it('默认显示在线', () => {
    setActivePinia(createPinia());
    const wrapper = mount(SystemStatusBar);
    expect(wrapper.text()).toContain('在线');
    expect(wrapper.text()).not.toContain('重试');
  });

  it('离线时显示“离线”与重试按钮', () => {
    setActivePinia(createPinia());
    const app = useAppStore();
    app.setOffline(true);
    const wrapper = mount(SystemStatusBar);
    expect(wrapper.text()).toContain('离线');
    expect(wrapper.find('button').text()).toBe('重试');
  });

  it('点击重试清除离线状态', async () => {
    setActivePinia(createPinia());
    const app = useAppStore();
    app.setOffline(true);
    const wrapper = mount(SystemStatusBar);
    await wrapper.find('button').trigger('click');
    expect(app.offline).toBe(false);
  });
});
