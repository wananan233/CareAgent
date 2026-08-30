<script setup lang="ts">
import { computed, onMounted } from 'vue';
import PageShell from '@/components/PageShell.vue';
import StateView from '@/components/StateView.vue';
import { useCareStore } from '@/stores/care';
import { EVIDENCE_LABEL, TASK_KIND_LABEL, loadStateFor } from '@/contracts/displayMapping';

const care = useCareStore();
const errorState = computed(() => care.loadError ? loadStateFor(care.loadError) : null);
function timeLabel(value: string) { return new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(value)); }
onMounted(() => { if (!care.tasks.length) care.refresh(); });
</script>

<template>
  <PageShell title="提醒">
    <StateView v-if="care.loading && !care.tasks.length" variant="loading" title="正在加载" />
    <StateView v-else-if="errorState" :variant="errorState.variant" :title="errorState.title" :description="errorState.description" />
    <section v-else class="reminders">
      <RouterLink v-for="task in care.tasks" :key="task.task_id" :to="`/task/${task.task_id}`" class="reminders__card">
        <p class="reminders__eyebrow">{{ timeLabel(task.scheduled_at) }}</p>
        <h2>{{ TASK_KIND_LABEL[task.kind] }}</h2>
        <strong>● {{ EVIDENCE_LABEL[task.evidence_state] }}</strong>
        <p>系统只知道提醒已经送达，不能确认是否已经完成。</p>
        <span>✦ CareAgent：为什么还是待确认？　查看依据 ›</span>
      </RouterLink>
    </section>
  </PageShell>
</template>

<style scoped>
.reminders{display:flex;flex-direction:column;gap:var(--space-md)}.reminders__card{display:flex;flex-direction:column;gap:var(--space-xs);padding:var(--space-md);border-radius:var(--radius-lg);background:var(--color-surface);box-shadow:0 1px 4px rgba(41,38,34,.08);color:var(--color-text-primary);text-decoration:none}.reminders__card h2,.reminders__card p{margin:0}.reminders__card h2{font-size:var(--font-size-main)}.reminders__eyebrow{color:var(--color-text-secondary);font-size:var(--font-size-caption);font-weight:700}.reminders__card strong{color:var(--color-warning)}.reminders__card span{margin-top:var(--space-xs);color:var(--color-brand);font-weight:700}
</style>
