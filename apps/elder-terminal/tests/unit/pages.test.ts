import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia } from 'pinia';
import { createMemoryHistory, createRouter } from 'vue-router';
import type { Component } from 'vue';
import { routes } from '@/router';
import HomePage from '@/pages/HomePage.vue';
import TaskDetailPage from '@/pages/TaskDetailPage.vue';
import AlertDetailPage from '@/pages/AlertDetailPage.vue';
import SafetyPage from '@/pages/SafetyPage.vue';
import AgentPage from '@/pages/AgentPage.vue';
import TimelinePage from '@/pages/TimelinePage.vue';
import SettingsPage from '@/pages/SettingsPage.vue';
import SystemPage from '@/pages/SystemPage.vue';

const PAGES: Array<{ title: string; component: Component }> = [
  { title: '今日', component: HomePage },
  { title: '任务详情', component: TaskDetailPage },
  { title: '告警详情', component: AlertDetailPage },
  { title: '安全提示', component: SafetyPage },
  { title: '小护', component: AgentPage },
  { title: '时间线', component: TimelinePage },
  { title: '设置', component: SettingsPage },
  { title: '系统状态', component: SystemPage },
];

const router = createRouter({ history: createMemoryHistory(), routes });
const pinia = createPinia();

describe('页面渲染 h1 标题', () => {
  for (const { title, component } of PAGES) {
    it(`渲染「${title}」页的 h1 标题`, () => {
      const wrapper = mount(component, {
        global: { plugins: [pinia, router] },
      });
      expect(wrapper.find('h1').text()).toBe(title);
    });
  }
});
