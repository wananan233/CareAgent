<script setup lang="ts">
import { computed, onMounted } from 'vue';
import PageShell from '@/components/PageShell.vue';
import MainTaskCard from '@/components/MainTaskCard.vue';
import StateView from '@/components/StateView.vue';
import { useCareStore } from '@/stores/care';
import {
  EVIDENCE_LABEL,
  loadStateFor,
  TASK_KIND_LABEL,
  TASK_STATUS_LABEL,
} from '@/contracts/displayMapping';

const care = useCareStore();

const errorState = computed(() =>
  care.loadError ? loadStateFor(care.loadError) : null,
);
const primaryTask = computed(() => care.dashboard?.primaryTask ?? null);
const updateTime = computed(() =>
  care.dashboard
    ? new Date(care.dashboard.server_time).toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
      })
    : '--',
);

onMounted(() => {
  if (care.dashboard === null && care.tasks.length === 0) {
    care.refresh();
  }
});
</script>

<template>
  <PageShell title="今日">
    <StateView v-if="care.loading && !care.dashboard" variant="loading" title="正在加载" />
    <StateView
      v-else-if="errorState"
      :variant="errorState.variant"
      :title="errorState.title"
      :description="errorState.description"
    />
    <template v-else>
      <p class="home__welcome">{{ care.dashboard?.welcome }}</p>
      <MainTaskCard v-if="primaryTask" :task="primaryTask" />

      <section class="home__tasks" aria-labelledby="tasks-title">
        <h2 id="tasks-title" class="home__section-title">今日任务</h2>
        <ul class="home__task-list">
          <li v-for="task in care.tasks" :key="task.task_id" class="home__task-item">
            <RouterLink :to="`/task/${task.task_id}`" class="home__task-link">
              <span class="home__task-kind">{{ TASK_KIND_LABEL[task.kind] }}</span>
              <span class="home__task-status">
                {{ TASK_STATUS_LABEL[task.status] }} · {{ EVIDENCE_LABEL[task.evidence_state] }}
              </span>
            </RouterLink>
          </li>
        </ul>
      </section>

      <p class="home__next">{{ care.dashboard?.nextAction }}</p>
      <p class="home__meta">数据更新于 {{ updateTime }}</p>
    </template>
  </PageShell>
</template>

<style scoped>
.home__welcome {
  margin: 0;
  font-size: var(--font-size-body);
}

.home__section-title {
  margin: 0;
  font-size: var(--font-size-body);
  font-weight: 700;
}

.home__tasks {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.home__task-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.home__task-item {
  margin: 0;
}

.home__task-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
  min-height: var(--touch-min-target);
  padding: var(--space-sm) var(--space-md);
  border: 2px solid var(--color-brand);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  text-decoration: none;
  font-size: var(--font-size-body);
}

.home__task-kind {
  font-weight: 700;
}

.home__task-status {
  color: var(--color-info);
}

.home__next {
  margin: 0;
  font-size: var(--font-size-body);
  color: var(--color-info);
}

.home__meta {
  margin: 0;
  font-size: var(--font-size-caption);
}
</style>
