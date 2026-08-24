<script setup lang="ts">
import { computed } from 'vue';
import { useAppStore } from '@/stores/app';

const app = useAppStore();

const status = computed(() =>
  app.offline
    ? { label: '离线', color: 'var(--color-warning)', dot: 'var(--color-warning)' }
    : { label: '在线', color: 'var(--color-success)', dot: 'var(--color-success)' },
);

const syncText = computed(() => {
  if (!app.lastSyncAt) return app.offline ? '离线中 · 无缓存数据' : '尚未同步';
  const time = new Date(app.lastSyncAt).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  });
  return app.offline ? `陈旧数据 · 最后可信更新 ${time}` : `最近更新 ${time}`;
});
</script>

<template>
  <div class="status-bar" role="status" aria-live="polite">
    <span class="status-bar__item">
      <span class="status-bar__dot" aria-hidden="true" :style="{ background: status.dot }"></span>
      <span class="status-bar__text" :style="{ color: status.color }">{{ status.label }}</span>
    </span>
    <span class="status-bar__item status-bar__sync" :class="{ 'status-bar__sync--stale': app.offline }">
      {{ syncText }}
    </span>
    <span v-if="app.offline && app.lastSyncAt" class="status-bar__item status-bar__stale">陈旧数据</span>
    <span v-if="app.updateReady" class="status-bar__item status-bar__update">
      新版本已就绪，刷新后生效
    </span>
    <span v-if="app.errorCode" class="status-bar__item status-bar__error">
      提示：{{ app.errorCode }}
    </span>
    <button
      v-if="app.offline || app.errorCode"
      type="button"
      class="status-bar__retry"
      @click="app.retry()"
    >
      重试
    </button>
  </div>
</template>

<style scoped>
.status-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-xs) var(--space-md);
  background: var(--color-surface);
  border-bottom: 1px solid rgba(0, 0, 0, 0.12);
}

.status-bar__item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  font-size: var(--font-size-caption);
}

.status-bar__dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
}

.status-bar__text {
  font-weight: 700;
}

.status-bar__sync {
  color: var(--color-text-primary);
}

.status-bar__error {
  color: var(--color-danger);
  font-weight: 700;
}

.status-bar__sync--stale {
  color: var(--color-warning);
}

.status-bar__stale {
  color: var(--color-warning);
  border: 2px solid var(--color-warning);
  border-radius: var(--radius-md);
  padding: 2px var(--space-xs);
  font-weight: 700;
}

.status-bar__update {
  color: var(--color-brand);
  border: 2px solid var(--color-brand);
  border-radius: var(--radius-md);
  padding: 2px var(--space-xs);
  font-weight: 700;
}

.status-bar__retry {
  min-height: var(--touch-min-target);
  min-width: var(--touch-min-target);
  padding: 0 var(--space-sm);
  border: 2px solid var(--color-brand);
  border-radius: var(--radius-md);
  background: var(--color-brand);
  color: var(--color-text-on-dark);
  font-size: var(--font-size-caption);
  font-weight: 700;
  cursor: pointer;
}

.status-bar__retry:hover {
  filter: brightness(1.1);
}
</style>
