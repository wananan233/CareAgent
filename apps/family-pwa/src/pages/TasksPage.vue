<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { CareTaskV1 } from '@carehub/shared-contracts'
import AppIcon from '@/components/AppIcon.vue'
import { coreAdapter, currentSubjectId } from '@/services/adapter'
const tasks = ref<CareTaskV1[]>([])
const filter = ref<'all' | 'pending' | 'history'>('all')
onMounted(async () => { tasks.value = await coreAdapter.getTasks(currentSubjectId) })
const visible = computed(() => filter.value === 'history' ? [] : tasks.value)
const formatTime = (value: string) => new Intl.DateTimeFormat('zh-CN', { month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(value))
</script>
<template>
  <main class="app-shell">
    <header class="top-bar"><div><p class="overline">今天 · {{ tasks.length }} 项</p><h1>提醒</h1></div><button class="round-button" aria-label="通知中心"><AppIcon name="bell" /></button></header>
    <div class="segmented"><button :class="{ active: filter === 'all' }" @click="filter='all'">全部</button><button :class="{ active: filter === 'pending' }" @click="filter='pending'">待关注</button><button :class="{ active: filter === 'history' }" @click="filter='history'">历史</button></div>
    <div class="section-heading"><h2>优先处理</h2></div>
    <div class="section-heading"><h2>{{ filter === 'history' ? '最近记录' : '接下来' }}</h2></div>
    <section v-if="visible.length" class="ios-list">
      <article v-for="task in visible" :key="task.task_id" class="task-detail-row"><span class="row-icon amber"><AppIcon name="pill" /></span><div class="row-main"><b>用药提醒</b><small>今天 {{ formatTime(task.scheduled_at) }}</small><div class="evidence-line"><span>状态</span><strong>是否完成仍待确认</strong></div><p>系统只确认提醒记录，不代表已经完成服药。</p></div></article>
    </section>
    <section v-if="visible.length" class="explanation-card"><h2>为什么还是待确认？</h2><p>CareHub 目前只有提醒记录，没有足够证据确认是否完成。</p><RouterLink to="/reports">查看依据 <AppIcon name="chevron" /></RouterLink></section>
    <section v-else class="empty-state"><span><AppIcon name="check" :size="28" /></span><h2>暂无历史记录</h2><p>完成或已记录的操作会显示在这里。</p></section>
  </main>
</template>
