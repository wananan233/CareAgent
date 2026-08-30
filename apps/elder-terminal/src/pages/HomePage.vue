<script setup lang="ts">
import { computed, onMounted } from 'vue';
import PageShell from '@/components/PageShell.vue';
import StateView from '@/components/StateView.vue';
import { useCareStore } from '@/stores/care';
import { EVIDENCE_LABEL, loadStateFor, TASK_KIND_LABEL, TASK_STATUS_LABEL, CARE_EVENT_LABEL } from '@/contracts/displayMapping';
const care = useCareStore();
const errorState = computed(() => care.loadError ? loadStateFor(care.loadError) : null);
const latestEvents = computed(() => care.timeline.slice(0, 3));
function timeLabel(value: string) { return new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(value)); }
onMounted(() => { if (care.dashboard === null && care.tasks.length === 0) care.refresh(); });
</script>
<template>
  <PageShell title="今天">
    <StateView v-if="care.loading && !care.dashboard" variant="loading" title="正在加载" />
    <StateView v-else-if="errorState" :variant="errorState.variant" :title="errorState.title" :description="errorState.description" :correlation-id="care.loadCorrelationId" />
    <div v-else class="home__grid">
      <section class="home__overview"><p class="home__eyebrow">今天怎么样</p><h2>今天整体平稳，有 {{ care.tasks.length ? '1 件事还需要确认' : '没有待确认的事' }}</h2><p>{{ care.dashboard?.welcome }}</p></section>
      <section class="home__agent"><p class="home__eyebrow">✦ CareAgent 今日助手</p><h2>{{ care.agent?.message || '查看今天已有的照护记录' }}</h2><p>{{ care.agent ? `基于 ${care.agent.facts.reduce((count, fact) => count + fact.source_refs.length, 0)} 条来源记录。` : '打开后会从 CareHub BFF 获取今日状态。' }}</p><RouterLink to="/agent">看看今天</RouterLink></section>
      <section class="home__section"><p class="home__eyebrow">今天要做</p><h2>按时看看提醒</h2><ul class="home__task-list"><li v-for="task in care.tasks" :key="task.task_id"><RouterLink :to="`/task/${task.task_id}`" class="home__task-link"><span><b>{{ TASK_KIND_LABEL[task.kind] }}</b><small>{{ TASK_STATUS_LABEL[task.status] }} · {{ EVIDENCE_LABEL[task.evidence_state] }}</small></span><span aria-hidden="true">›</span></RouterLink></li></ul></section>
      <section class="home__section"><p class="home__eyebrow">今天发生了什么</p><h2>最近记录</h2><ul class="home__event-list"><li v-for="event in latestEvents" :key="event.event_id"><b>{{ timeLabel(event.occurred_at) }} {{ CARE_EVENT_LABEL[event.event_type] }}</b><span>信息可信 · CareHub 提醒记录</span></li></ul><RouterLink to="/timeline" class="home__text-link">查看全部记录</RouterLink></section>
      <section class="home__help"><p class="home__eyebrow">需要帮助</p><h2>有事就联系家人</h2><button type="button">联系家人</button></section>
    </div>
  </PageShell>
</template>
<style scoped>
.home__grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:var(--space-md)}.home__overview,.home__section,.home__help,.home__agent{display:flex;flex-direction:column;gap:var(--space-sm);padding:var(--space-md);border-radius:var(--radius-lg);background:var(--color-surface);box-shadow:0 1px 4px rgba(41,38,34,.08)}.home__overview{grid-column:1/-1;background:#e7f0ed}.home__agent{grid-column:1/-1;background:linear-gradient(135deg,#e1eeea,#f9fcfb);border:1px solid #c4ded6}.home__agent h2{margin:0;font-size:var(--font-size-main);line-height:1.25}.home__agent p:not(.home__eyebrow){margin:0}.home__agent a{display:inline-flex;align-items:center;justify-content:center;align-self:flex-start;min-height:var(--touch-min-target);padding:0 var(--space-md);border-radius:var(--radius-md);background:var(--color-brand);color:#fff;font-weight:700;text-decoration:none}.home__eyebrow{margin:0;color:var(--color-text-secondary);font-size:var(--font-size-caption);font-weight:700}.home__overview h2,.home__section h2,.home__help h2{margin:0;font-size:var(--font-size-main);line-height:1.25}.home__overview p:not(.home__eyebrow){margin:0}.home__task-list,.home__event-list{display:flex;flex-direction:column;gap:var(--space-xs);list-style:none;margin:0;padding:0}.home__task-link{display:flex;align-items:center;justify-content:space-between;gap:var(--space-sm);min-height:var(--touch-min-target);padding:var(--space-sm);border-radius:var(--radius-md);background:var(--color-surface-muted);color:var(--color-text-primary);text-decoration:none}.home__task-link small,.home__event-list span{display:block;color:var(--color-text-secondary);font-size:var(--font-size-caption)}.home__event-list li{padding:0 0 var(--space-sm);border-bottom:1px solid #e5e0d8}.home__text-link{color:var(--color-brand);font-weight:700}.home__help{background:#f1ece5}.home__help button{min-height:64px;border:0;border-radius:var(--radius-md);background:var(--color-brand);color:#fff;font:inherit;font-weight:700;cursor:pointer}@media(max-width:720px){.home__grid{grid-template-columns:1fr}.home__overview,.home__agent{grid-column:auto}}
</style>
