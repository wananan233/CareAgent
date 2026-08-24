<script setup lang="ts">
import { computed } from 'vue';
import type { AlertViewV1 } from '@carehub/shared-contracts';
import { ALERT_KIND_LABEL, ALERT_STATUS_LABEL } from '@/contracts/displayMapping';

const props = defineProps<{ alert: AlertViewV1 }>();
const emit = defineEmits<{ acknowledge: [] }>();

const isCritical = computed(
  () => props.alert.safety_level === 'S-1' || props.alert.safety_level === 'S0',
);

const timeLabel = computed(() =>
  new Date(props.alert.occurred_at).toLocaleString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }),
);
</script>

<template>
  <article class="alert-card" :class="{ 'alert-card--critical': isCritical }">
    <div class="alert-card__head">
      <span class="alert-card__level">{{ alert.safety_level }}</span>
      <h2 class="alert-card__kind">{{ ALERT_KIND_LABEL[alert.kind] }}</h2>
      <span class="alert-card__status">{{ ALERT_STATUS_LABEL[alert.status] }}</span>
    </div>
    <p class="alert-card__time">发生时间：{{ timeLabel }}</p>
    <div class="alert-card__actions">
      <RouterLink :to="`/alert/${alert.alert_id}`" class="alert-card__view">
        查看详情
      </RouterLink>
      <button
        v-if="alert.status === 'ACTIVE'"
        type="button"
        class="alert-card__confirm"
        @click="emit('acknowledge')"
      >
        我已看到提醒
      </button>
    </div>
  </article>
</template>

<style scoped>
.alert-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  padding: var(--space-md);
  border: 2px solid var(--color-brand);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.alert-card--critical {
  border-color: var(--color-danger);
  border-width: 3px;
}

.alert-card__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-sm);
}

.alert-card__level {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 48px;
  min-height: 48px;
  padding: 0 var(--space-sm);
  border-radius: var(--radius-md);
  background: var(--color-danger);
  color: var(--color-text-on-dark);
  font-size: var(--font-size-body);
  font-weight: 900;
}

.alert-card__kind {
  margin: 0;
  font-size: var(--font-size-main);
}

.alert-card__status {
  font-size: var(--font-size-caption);
  color: var(--color-info);
  font-weight: 700;
}

.alert-card__time {
  margin: 0;
  font-size: var(--font-size-body);
}

.alert-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.alert-card__view,
.alert-card__confirm {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: var(--touch-min-target);
  padding: 0 var(--space-md);
  border: 2px solid var(--color-brand);
  border-radius: var(--radius-md);
  font-size: var(--font-size-body);
  font-weight: 700;
  text-decoration: none;
  cursor: pointer;
}

.alert-card__view {
  background: var(--color-surface);
  color: var(--color-brand);
}

.alert-card__confirm {
  background: var(--color-brand);
  color: var(--color-text-on-dark);
}
</style>
