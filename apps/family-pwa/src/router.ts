import { createRouter, createWebHistory } from 'vue-router'
import FamilyShell from './pages/FamilyShell.vue'
import ErrorPage from './pages/ErrorPage.vue'
import AlertDetail from './pages/AlertDetail.vue'
import TasksPage from './pages/TasksPage.vue'
import CarePage from './pages/CarePage.vue'
import ReportsPage from './pages/ReportsPage.vue'
import SettingsPage from './pages/SettingsPage.vue'

export default createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0, behavior: 'auto' }),
  routes: [
    { path: '/', component: FamilyShell, meta: { primary: true, order: 0, depth: 0 } },
    { path: '/alerts/:id', component: AlertDetail, props: true, meta: { order: 1, depth: 1 } },
    { path: '/tasks', component: TasksPage, meta: { primary: true, order: 1, depth: 0 } },
    { path: '/care', component: CarePage, meta: { primary: true, order: 2, depth: 0 } },
    { path: '/reports', component: ReportsPage, meta: { primary: true, order: 3, depth: 0 } },
    { path: '/settings', component: SettingsPage, meta: { primary: true, order: 4, depth: 0 } },
    { path: '/error/:code', component: ErrorPage, props: true, meta: { order: 5, depth: 1 } },
    { path: '/:pathMatch(.*)*', redirect: '/error/UNAVAILABLE' }
  ]
})
