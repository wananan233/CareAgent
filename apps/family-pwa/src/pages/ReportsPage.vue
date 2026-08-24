<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { AgentResponseV1 } from '@carehub/shared-contracts'
import AppIcon from '@/components/AppIcon.vue'
import { coreAdapter } from '@/services/adapter'
const report = ref<AgentResponseV1 | null>(null)
const period = ref<'day' | 'week'>('day')
const fallback = ref(false)
async function load() { report.value = await coreAdapter.getReport('subject-demo-parent-01', fallback.value ? 'fallback' : 'normal') }
onMounted(load)
</script>
<template>
  <main class="app-shell">
    <header class="top-bar"><div><p class="overline">更新于 09:50</p><h1>报告</h1></div><button class="round-button" aria-label="报告说明"><AppIcon name="info" /></button></header>
    <div class="segmented"><button :class="{active:period==='day'}" @click="period='day'">今日</button><button :class="{active:period==='week'}" @click="period='week'">本周</button></div>
    <section v-if="report && report.fallback === 'NONE'" class="report-lead"><span class="header-symbol blue"><AppIcon name="chart" :size="24" /></span><p>{{ period === 'day' ? '今日摘要' : '本周摘要' }}</p><h2>{{ report.message }}</h2><small>这是带来源的受控摘要，不构成诊断或医疗建议。</small></section>
    <section v-if="report && report.fallback === 'NONE'" class="ios-list report-facts">
      <div v-for="(fact, index) in report.facts" :key="fact.text" class="list-row"><span class="row-icon" :class="index === 0 ? 'red' : 'amber'"><AppIcon :name="index === 0 ? 'shield' : 'pill'" /></span><span class="row-main"><b>{{ index === 0 ? '安全提醒' : '任务证据' }}</b><small>{{ fact.text }}</small></span><span class="status" :class="index === 0 ? 'danger' : 'pending'">{{ index === 0 ? '需关注' : '待确认' }}</span></div>
    </section>
    <section v-if="report && report.fallback === 'NONE'" class="source-card"><div><AppIcon name="shield" /><b>来源与质量</b></div><p>来源事件：{{ report.facts.flatMap(x => x.source_refs).join('、') }}</p><p>数据类型：SIMULATOR · 仅用于本地演示</p></section>
    <section v-if="report && report.fallback !== 'NONE'" class="empty-state warning"><span><AppIcon name="info" :size="28" /></span><h2>摘要暂不可用</h2><p>{{ report.message }}</p><small>原因：{{ report.fallback }}</small></section>
    <button class="text-action" @click="fallback=!fallback; load()">{{ fallback ? '恢复正常模拟摘要' : '演示降级状态' }}</button>
  </main>
</template>
