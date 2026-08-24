<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { CareTaskV1 } from '@carehub/shared-contracts'
import AppIcon from '@/components/AppIcon.vue'
import { coreAdapter } from '@/services/adapter'
const tasks = ref<CareTaskV1[]>([])
const filter = ref<'all' | 'pending' | 'history'>('all')
onMounted(async () => { tasks.value = await coreAdapter.getTasks('subject-demo-parent-01') })
const visible = computed(() => filter.value === 'history' ? [] : tasks.value)
</script>
<template>
  <main class="app-shell">
    <header class="top-bar"><div><p class="overline">今天 · 2 项</p><h1>提醒</h1></div><button class="round-button" aria-label="通知中心"><AppIcon name="bell" /></button></header>
    <div class="segmented"><button :class="{ active: filter === 'all' }" @click="filter='all'">全部</button><button :class="{ active: filter === 'pending' }" @click="filter='pending'">待关注</button><button :class="{ active: filter === 'history' }" @click="filter='history'">历史</button></div>
    <div class="section-heading"><h2>优先处理</h2></div>
    <RouterLink class="critical-card compact" to="/alerts/alert-smoke-gas-001"><div class="critical-icon"><AppIcon name="shield" /></div><div class="critical-content"><p><b>S-1 安全提醒</b><span>10:24</span></p><h2>烟雾/燃气模拟告警</h2><small>已查看不等于解除</small></div><AppIcon name="chevron" class="chevron" /></RouterLink>
    <div class="section-heading"><h2>{{ filter === 'history' ? '最近记录' : '接下来' }}</h2></div>
    <section v-if="visible.length" class="ios-list">
      <article v-for="task in visible" :key="task.task_id" class="task-detail-row"><span class="row-icon amber"><AppIcon name="pill" /></span><div class="row-main"><b>午间用药提醒</b><small>今天 12:00 · 来源 {{ task.source_refs[0].type }}</small><div class="evidence-line"><span>证据状态</span><strong>UNKNOWN · 待确认</strong></div><p>这不代表已经服药，家属端不能修改药名、剂量或频次。</p></div></article>
    </section>
    <section v-else class="empty-state"><span><AppIcon name="check" :size="28" /></span><h2>暂无历史记录</h2><p>完成或已记录的操作会显示在这里。</p></section>
  </main>
</template>
