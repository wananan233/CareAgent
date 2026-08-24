<script setup lang="ts">
import { computed } from 'vue';
import PageShell from '@/components/PageShell.vue';
import { useAppStore } from '@/stores/app';

const app = useAppStore();

const connection = computed(() =>
  app.offline
    ? { label: '离线', color: 'var(--color-warning)' }
    : { label: '在线', color: 'var(--color-success)' },
);

const freshness = computed(() =>
  app.offline ? { label: '数据可能过期', color: 'var(--color-warning)' } : { label: '数据新鲜', color: 'var(--color-success)' },
);
</script>

<template>
  <PageShell title="系统状态">
    <dl class="system__list">
      <div class="system__row">
        <dt class="system__term">网络连接</dt>
        <dd class="system__desc">
          <span class="system__dot" aria-hidden="true" :style="{ background: connection.color }"></span>
          <span :style="{ color: connection.color, fontWeight: 700 }">{{ connection.label }}</span>
        </dd>
      </div>
      <div class="system__row">
        <dt class="system__term">最近同步</dt>
        <dd class="system__desc">{{ app.lastSyncAt ?? '尚未同步' }}</dd>
      </div>
      <div class="system__row">
        <dt class="system__term">数据新鲜度</dt>
        <dd class="system__desc" :style="{ color: freshness.color, fontWeight: 700 }">
          {{ freshness.label }}
        </dd>
      </div>
      <div v-if="app.errorCode" class="system__row">
        <dt class="system__term">错误提示</dt>
        <dd class="system__desc system__desc--danger">{{ app.errorCode }}</dd>
      </div>
    </dl>

    <div class="system__demo">
      <button
        type="button"
        class="system__button"
        @click="app.setOffline(!app.offline)"
      >
        {{ app.offline ? '恢复联网' : '模拟离线' }}
      </button>
      <button
        v-if="app.offline || app.errorCode"
        type="button"
        class="system__button system__button--secondary"
        @click="app.retry()"
      >
        重试
      </button>
    </div>
  </PageShell>
</template>

<style scoped>
.system__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  margin: 0;
  border: 2px solid var(--color-brand);
  border-radius: var(--radius-lg);
  padding: var(--space-md);
}

.system__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
}

.system__term {
  font-size: var(--font-size-body);
  font-weight: 700;
}

.system__desc {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  margin: 0;
  font-size: var(--font-size-body);
}

.system__desc--danger {
  color: var(--color-danger);
  font-weight: 700;
}

.system__dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
}

.system__demo {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.system__button {
  min-height: var(--touch-min-target);
  min-width: 160px;
  padding: 0 var(--space-md);
  border: 2px solid var(--color-brand);
  border-radius: var(--radius-md);
  background: var(--color-brand);
  color: var(--color-text-on-dark);
  font-size: var(--font-size-body);
  font-weight: 700;
  cursor: pointer;
}

.system__button--secondary {
  background: var(--color-surface);
  color: var(--color-brand);
}
</style>
