<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { AgentResponseV1 } from '@carehub/shared-contracts'
import AppIcon from '@/components/AppIcon.vue'
import CareAgentSheet from '@/components/CareAgentSheet.vue'
import { coreAdapter, currentSubjectId } from '@/services/adapter'
import type { AgentCapability } from '@/services/CoreApiAdapter'

const period = ref<'day' | 'week'>('day')
const report = ref<AgentResponseV1 | null>(null)
const loading = ref(true)
const error = ref<{ code: string; correlation?: string } | null>(null)
const sourcesOpen = ref(false)
const feedback = ref('')
const careAgentOpen = ref(false)
const changeExplanation = ref<AgentResponseV1 | null>(null)
const capability = computed<AgentCapability>(() => period.value === 'day' ? 'DAILY_SUMMARY' : 'WEEKLY_TREND')
const sourceRefs = computed(() => [...new Set(report.value?.facts.flatMap(f => f.source_refs) ?? [])])
const unknownLabel = (field: string) => field.toLowerCase().includes('medication') ? '是否已经实际完成服药' : '该事项的完整状态'
async function load() { loading.value = true; error.value = null; try { report.value = await coreAdapter.getAgent(currentSubjectId, capability.value) } catch (e) { const x = e as { message?: string; correlationId?: string }; error.value = { code: x.message ?? 'UNAVAILABLE', correlation: x.correlationId } } finally { loading.value = false } }
async function changePeriod(value: 'day' | 'week') { period.value = value; await load() }
async function loadExplanation() { changeExplanation.value = await coreAdapter.getAgent(currentSubjectId, 'CHANGE_EXPLANATION') }
onMounted(load)
</script>
<template>
  <main class="app-shell">
    <header class="top-bar"><div><p class="overline">CareHub AI · 仅基于已授权记录</p><h1>智能报告</h1></div><button class="round-button" aria-label="查看 AI 说明"><AppIcon name="info" /></button></header>
    <div class="segmented"><button :class="{active:period==='day'}" @click="changePeriod('day')">今日简报</button><button :class="{active:period==='week'}" @click="changePeriod('week')">周趋势</button></div>
    <section v-if="loading" class="skeleton-card" aria-busy="true"><i/><i/><i/></section>
    <section v-else-if="error" class="empty-state warning"><span><AppIcon name="info" :size="28"/></span><h2>AI 服务暂不可用</h2><p>基础照护功能仍正常。请稍后重试。</p><button class="text-action" @click="load">重试</button></section>
    <template v-else-if="report">
      <section class="report-lead"><span class="header-symbol blue"><AppIcon name="chart" :size="24"/></span><p>{{ period === 'day' ? 'AI 今日照护简报' : 'AI 周趋势' }}</p><h2>{{ period === 'day' ? '今天整体平稳' : '最近一周照护记录变化' }}</h2><p class="report-summary">{{ report.message }}</p><small>AI 辅助分析 · {{ report.fallback === 'NONE' ? '当前可用' : '基础摘要降级' }}</small></section>
      <section v-if="period==='week'" class="trend-strip"><div><small>最近 7 天</small><b>{{ report.message }}</b></div><button class="inline-link" @click="loadExplanation">为什么值得关注？</button></section>
      <section v-if="changeExplanation" class="ai-detail-card"><h2>AI 解读</h2><p>{{ changeExplanation.message }}</p><button class="inline-link" @click="sourcesOpen=true">查看依据</button></section>
      <div class="section-heading"><h2>{{ period === 'day' ? '今日变化与关注' : '变化依据' }}</h2><button class="inline-link" @click="sourcesOpen=true">查看依据</button></div>
      <section class="ios-list report-facts"><div v-for="fact in report.facts" :key="fact.text" class="list-row"><span class="row-icon amber"><AppIcon name="chart"/></span><span class="row-main"><b>已授权记录</b><small>{{ fact.text }}</small></span></div><div v-if="!report.facts.length" class="list-row"><span class="row-main"><small>没有足够的已授权记录可展示。</small></span></div></section>
      <section class="ai-detail-card"><h2>AI 还不知道什么</h2><p v-if="!report.unknowns?.length">当前没有额外未知项；数据不足时 CareHub 不会自行推断。</p><ul v-else><li v-for="item in report.unknowns" :key="item.field">{{ unknownLabel(item.field) }}：{{ item.reason }}</li></ul></section>
      <section v-if="report.why_it_matters?.length" class="ai-detail-card"><h2>为什么值得关注</h2><p v-for="line in report.why_it_matters" :key="line">{{ line }}</p></section>
      <section v-if="report.suggested_safe_actions?.length" class="ai-detail-card"><h2>建议下一步</h2><p v-for="action in report.suggested_safe_actions" :key="action">{{ action }}</p></section>
      <section class="feedback-row" aria-label="AI 反馈"><span>这份分析有帮助吗？</span><button v-for="label in ['有帮助','不准确','已过时']" :key="label" :class="{selected: feedback===label}" @click="feedback=label">{{ label }}</button><small v-if="feedback">已记录，将用于改进 CareHub AI 体验。</small></section>
      <div class="section-heading"><h2>问 CareAgent</h2><button class="inline-link" @click="careAgentOpen=true">打开 CareAgent</button></div>
      <section class="qa-card careagent-entry"><span class="header-symbol blue"><AppIcon name="sparkles" :size="22" /></span><div><b>有问题想确认？</b><p>CareAgent 会基于已授权记录回答，并说明依据和未知项。</p></div><button class="primary-action" @click="careAgentOpen=true">✦ 问 CareAgent</button></section>
    </template>
  </main>
  <CareAgentSheet v-model:open="careAgentOpen" />
  <Transition name="sheet"><div v-if="sourcesOpen" class="sheet-backdrop" @click.self="sourcesOpen=false"><section class="bottom-sheet" role="dialog" aria-modal="true" aria-label="AI 分析依据"><div class="sheet-handle"/><h2>本次 AI 分析依据</h2><p>使用 {{ sourceRefs.length }} 条已授权来源记录，不显示内部编号或原始事件内容。</p><section class="ios-list"><div v-for="fact in report?.facts" :key="fact.text" class="list-row"><span class="row-main"><b>{{ fact.text }}</b><small>{{ fact.source_refs.length }} 条来源记录</small></span></div></section><button class="sheet-cancel" @click="sourcesOpen=false">完成</button></section></div></Transition>
</template>
