<script setup lang="ts">
import { computed, onMounted } from 'vue';
import type { SafetyLevel } from '@carehub/shared-contracts/elder';
import { useCareStore } from '@/stores/care';
import { ALERT_KIND_LABEL } from '@/contracts/displayMapping';

const care = useCareStore();

const RANK: Record<SafetyLevel, number> = {
  'S-1': 0,
  S0: 1,
};

/** 全局不可忽略的安全卡：仅展示 S-1/S0 且仍在进行中的最高级告警。 */
const critical = computed(() => {
  const actives = care.alerts.filter(
    (a) => a.status === 'OPEN' && (a.safety_level === 'S-1' || a.safety_level === 'S0'),
  );
  if (actives.length === 0) return null;
  return actives.sort((a, b) => RANK[a.safety_level] - RANK[b.safety_level])[0];
});

onMounted(() => {
  if (care.alerts.length === 0) {
    care.loadAlerts();
  }
});
</script>

<template>
  <aside v-if="critical" class="global-safety" aria-label="紧急安全提示">
    <span class="global-safety__icon" aria-hidden="true">!</span>
    <div class="global-safety__body">
      <strong class="global-safety__kind">紧急安全提醒</strong>
      <span class="global-safety__note">检测到{{ ALERT_KIND_LABEL[critical.kind] }}信息，请立即关注</span>
    </div>
    <RouterLink :to="`/alert/${critical.alert_id}`" class="global-safety__action">
      查看详情
    </RouterLink>
  </aside>
</template>

<style scoped>
.global-safety {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md);
  margin-bottom: var(--space-md);
  border: 0;
  border-radius: var(--radius-lg);
  background: #fce9e7;
  box-shadow: 0 4px 12px rgba(179, 38, 30, .12);
}

.global-safety__icon {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 64px;
  min-height: 64px;
  border-radius: var(--radius-md);
  background: #d44a40;
  color: white;
  font-size: var(--font-size-main);
  font-weight: 900;
}

.global-safety__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.global-safety__kind {
  font-size: var(--font-size-main);
}

.global-safety__note {
  font-size: var(--font-size-body);
  color: #9d241e;
  font-weight: 700;
}

.global-safety__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: var(--touch-min-target);
  padding: 0 var(--space-md);
  border: 0;
  border-radius: var(--radius-md);
  background: var(--color-danger);
  color: var(--color-text-on-dark);
  font-size: var(--font-size-body);
  font-weight: 700;
  text-decoration: none;
}
</style>
