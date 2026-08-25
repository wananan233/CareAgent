<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import type { DashboardV1 } from '@carehub/shared-contracts'
import AppIcon from '@/components/AppIcon.vue'
import { coreAdapter, currentSubjectId } from '@/services/adapter'
import { useUiStore } from '@/stores/ui'

const dashboard = ref<DashboardV1 | null>(null)
const loading = ref(true)
const ui = useUiStore()
onMounted(async () => { dashboard.value = await coreAdapter.getDashboard(currentSubjectId); ui.markTrusted(dashboard.value.last_updated_at); loading.value = false })
const online = () => ui.setNetwork(false)
const offline = () => ui.setNetwork(true)
onMounted(() => { addEventListener('online', online); addEventListener('offline', offline) })
onUnmounted(() => { removeEventListener('online', online); removeEventListener('offline', offline) })
</script>

<template>
  <main class="app-shell home-page">
    <header class="top-bar">
      <div><p class="overline">我的家庭</p><h1>概览</h1></div>
      <button class="avatar-button" type="button" aria-label="当前家庭成员">妈</button>
    </header>

    <div class="demo-chip"><span></span>模拟数据 · 本地演示</div>
    <div v-if="ui.isOffline" class="offline-banner">当前离线，显示本次会话的最后可信快照</div>

    <section v-if="loading" class="skeleton-card" aria-busy="true"><i></i><i></i><i></i></section>
    <template v-else-if="dashboard">
      <RouterLink class="critical-card" to="/alerts/alert-smoke-gas-001">
        <div class="critical-icon"><AppIcon name="shield" :size="24" /></div>
        <div class="critical-content"><p><b>安全提醒</b><span>10:24</span></p><h2>烟雾/燃气模拟告警</h2><small>请查看事件来源和后续安排</small></div>
        <AppIcon name="chevron" class="chevron" />
      </RouterLink>

      <div class="metric-grid">
        <RouterLink to="/tasks" class="metric-card"><span class="metric-icon blue"><AppIcon name="clock" /></span><b>2</b><small>今日待关注</small></RouterLink>
        <RouterLink to="/reports" class="metric-card"><span class="metric-icon green"><AppIcon name="chart" /></span><b>09:50</b><small>最近更新</small></RouterLink>
      </div>

      <div class="section-heading"><h2>今天</h2><RouterLink to="/tasks">查看全部</RouterLink></div>
      <section class="ios-list">
        <RouterLink to="/tasks" class="list-row"><span class="row-icon amber"><AppIcon name="pill" /></span><span class="row-main"><b>午间用药提醒</b><small>12:00 · 证据待确认</small></span><span class="status pending">待关注</span><AppIcon name="chevron" class="chevron" /></RouterLink>
        <RouterLink to="/care" class="list-row"><span class="row-icon purple"><AppIcon name="heart" /></span><span class="row-main"><b>关怀问候</b><small>可发送一条预设关怀请求</small></span><AppIcon name="chevron" class="chevron" /></RouterLink>
      </section>

      <div class="section-heading"><h2>今日关怀摘要</h2><RouterLink to="/reports">详情</RouterLink></div>
      <RouterLink class="summary-card" to="/reports"><span class="summary-icon"><AppIcon name="chart" :size="26" /></span><div><b>状态存在待确认信息</b><p>1 条安全提醒 · 1 项任务证据未知</p><small>来源 {{ dashboard.source_refs[0].type }} · 质量 {{ dashboard.quality }}</small></div><AppIcon name="chevron" class="chevron" /></RouterLink>
    </template>
  </main>
</template>
