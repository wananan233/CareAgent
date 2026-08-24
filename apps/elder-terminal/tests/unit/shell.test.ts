import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia } from 'pinia';
import { createMemoryHistory, createRouter } from 'vue-router';
import { SIMULATED_DATA_LABEL } from '@carehub/shared-contracts/elder';
import { routes } from '@/router';
import AppShell from '@/components/AppShell.vue';

const router = createRouter({ history: createMemoryHistory(), routes });
const pinia = createPinia();

describe('AppShell 全局壳', () => {
  it('含品牌、全局“模拟数据”标识、主导航与主内容区', () => {
    const wrapper = mount(AppShell, {
      global: { plugins: [pinia, router] },
    });
    expect(wrapper.text()).toContain('CareHub 老人端');
    expect(wrapper.text()).toContain(SIMULATED_DATA_LABEL);
    expect(wrapper.find('nav').exists()).toBe(true);
    expect(wrapper.find('main#main-content').exists()).toBe(true);
  });

  it('提供键盘跳转链接', () => {
    const wrapper = mount(AppShell, {
      global: { plugins: [pinia, router] },
    });
    const skip = wrapper.find('a.app-shell__skip');
    expect(skip.exists()).toBe(true);
    expect(skip.attributes('href')).toBe('#main-content');
  });
});
