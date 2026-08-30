import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import HomePage from '@/pages/HomePage.vue';
import TaskDetailPage from '@/pages/TaskDetailPage.vue';
import AlertDetailPage from '@/pages/AlertDetailPage.vue';
import SafetyPage from '@/pages/SafetyPage.vue';
import AgentPage from '@/pages/AgentPage.vue';
import TimelinePage from '@/pages/TimelinePage.vue';
import RemindersPage from '@/pages/RemindersPage.vue';
import SettingsPage from '@/pages/SettingsPage.vue';
import SystemPage from '@/pages/SystemPage.vue';
import NotFoundPage from '@/pages/NotFoundPage.vue';

export const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/home' },
  { path: '/home', name: 'home', component: HomePage, meta: { title: '今日' } },
  { path: '/task/:id', name: 'task', component: TaskDetailPage, meta: { title: '任务详情' } },
  { path: '/alert/:id', name: 'alert', component: AlertDetailPage, meta: { title: '告警详情' } },
  { path: '/safety', name: 'safety', component: SafetyPage, meta: { title: '安全提示' } },
  { path: '/agent', name: 'agent', component: AgentPage, meta: { title: '小护' } },
  { path: '/reminders', name: 'reminders', component: RemindersPage, meta: { title: '提醒' } },
  { path: '/timeline', name: 'timeline', component: TimelinePage, meta: { title: '时间线' } },
  { path: '/settings', name: 'settings', component: SettingsPage, meta: { title: '设置' } },
  { path: '/system', name: 'system', component: SystemPage, meta: { title: '系统状态' } },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: NotFoundPage },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});
