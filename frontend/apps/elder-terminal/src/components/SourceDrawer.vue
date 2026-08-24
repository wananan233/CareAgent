<script setup lang="ts">
import { ref } from 'vue';
import type { SourceRef } from '@carehub/shared-contracts';

const props = defineProps<{ sources: SourceRef[] }>();

const open = ref(false);

function timeLabel(s: SourceRef): string {
  return new Date(s.occurred_at).toLocaleString('zh-CN', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
</script>

<template>
  <div class="source-drawer">
    <button
      type="button"
      class="source-drawer__toggle"
      :aria-expanded="open ? 'true' : 'false'"
      @click="open = !open"
    >
      {{ open ? '收起来源' : '查看来源' }}（{{ props.sources.length }}）
    </button>
    <ul v-if="open" class="source-drawer__list">
      <li v-for="s in props.sources" :key="s.ref_id" class="source-drawer__item">
        <span class="source-drawer__label">{{ s.label }}</span>
        <span class="source-drawer__meta">{{ s.kind }} · {{ timeLabel(s) }}</span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.source-drawer {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.source-drawer__toggle {
  align-self: flex-start;
  min-height: var(--touch-min-target);
  padding: 0 var(--space-md);
  border: 2px solid var(--color-info);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-info);
  font-size: var(--font-size-body);
  font-weight: 700;
  cursor: pointer;
}

.source-drawer__toggle:hover {
  background: rgba(0, 0, 0, 0.04);
}

.source-drawer__list {
  list-style: none;
  margin: 0;
  padding: var(--space-sm) var(--space-md);
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  border: 2px solid var(--color-info);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.source-drawer__item {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-xs);
}

.source-drawer__label {
  font-size: var(--font-size-body);
  font-weight: 700;
}

.source-drawer__meta {
  font-size: var(--font-size-caption);
  color: var(--color-text-primary);
}
</style>
