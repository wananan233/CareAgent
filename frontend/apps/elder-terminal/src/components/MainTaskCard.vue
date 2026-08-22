<script setup lang="ts">
import { computed } from 'vue';
import type { CareTaskV1 } from '@carehub/shared-contracts';
import {
  EVIDENCE_LABEL,
  TASK_KIND_LABEL,
  TASK_STATUS_LABEL,
} from '@/contracts/displayMapping';

const props = defineProps<{ task: CareTaskV1 }>();

const kindLabel = computed(() => TASK_KIND_LABEL[props.task.kind]);
const timeLabel = computed(() =>
  new Date(props.task.scheduledAt).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  }),
);
</script>

<template>
  <section class="main-task" aria-labelledby="main-task-title">
    <h2 id="main-task-title" class="main-task__kind">{{ kindLabel }}</h2>
    <p class="main-task__time">
      <svg class="main-task__clock" aria-hidden="true" viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 3" />
      </svg>
      {{ timeLabel }}
    </p>
    <p class="main-task__status">状态：{{ TASK_STATUS_LABEL[task.status] }}</p>
    <p class="main-task__evidence">证据：{{ EVIDENCE_LABEL[task.evidenceState] }}</p>
    <RouterLink :to="`/task/${task.taskId}`" class="main-task__action">
      查看任务详情
    </RouterLink>
  </section>
</template>

<style scoped>
.main-task {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  padding: var(--space-md);
  border: 2px solid var(--color-brand);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.main-task__kind {
  margin: 0;
  font-size: var(--font-size-main);
  line-height: 1.2;
}

.main-task__time {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  margin: 0;
  font-size: var(--font-size-time);
  font-weight: 700;
}

.main-task__clock {
  flex-shrink: 0;
}

.main-task__status,
.main-task__evidence {
  margin: 0;
  font-size: var(--font-size-body);
}

.main-task__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  align-self: flex-start;
  min-height: var(--touch-min-target);
  min-width: 180px;
  padding: 0 var(--space-md);
  border: 2px solid var(--color-brand);
  border-radius: var(--radius-md);
  background: var(--color-brand);
  color: var(--color-text-on-dark);
  font-size: var(--font-size-body);
  font-weight: 700;
  text-decoration: none;
}

.main-task__action:hover {
  filter: brightness(1.1);
}
</style>
