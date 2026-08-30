<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import PageShell from '@/components/PageShell.vue';
import StateView from '@/components/StateView.vue';
import QualityBadge from '@/components/QualityBadge.vue';
import { useCareStore } from '@/stores/care';
import { CARE_EVENT_LABEL, loadStateFor } from '@/contracts/displayMapping';
import type { CareEventV1 } from '@carehub/shared-contracts/elder';

const care = useCareStore();
const route = useRoute();
const errorState = computed(() => (care.loadError ? loadStateFor(care.loadError) : null));

function timeLabel(e: CareEventV1): string {
  return new Date(e.occurred_at).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

onMounted(() => {
  if (care.timeline.length === 0) {
    care.refresh();
  }
});
</script>

<template>
  <PageShell :title="route.path === '/reminders' ? '提醒' : '时间线'">
    <StateView
      v-if="care.loading && care.timeline.length === 0"
      variant="loading"
      title="正在加载"
    />
    <StateView
      v-else-if="errorState"
      :variant="errorState.variant"
      :title="errorState.title"
      :description="errorState.description"
    />
    <StateView
      v-else-if="care.timeline.length === 0"
      variant="empty"
      title="暂无时间线记录"
      description="今天还没有新的记录。"
    />
    <ol v-else class="timeline">
      <li v-for="e in care.timeline" :key="e.event_id" class="timeline__item">
        <div class="timeline__head">
          <span class="timeline__time">{{ timeLabel(e) }}</span>
          <span class="timeline__label">{{ CARE_EVENT_LABEL[e.event_type] }}</span>
          <QualityBadge :quality="e.quality.status" :reason="e.quality.reason" />
        </div>
        <p class="timeline__source">来源：CareHub 提醒记录</p>
      </li>
    </ol>
  </PageShell>
</template>

<style scoped>
.timeline {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.timeline__item {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  padding: var(--space-sm) var(--space-md);
  border: 2px solid var(--color-brand);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.timeline__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-sm);
}

.timeline__time {
  font-size: var(--font-size-time);
  font-weight: 700;
}

.timeline__label {
  font-size: var(--font-size-body);
  font-weight: 700;
}

.timeline__source {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--color-info);
}
</style>
