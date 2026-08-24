<script setup lang="ts">
export type StateVariant = 'loading' | 'empty' | 'denied' | 'offline' | 'failed';

const props = defineProps<{
  variant: StateVariant;
  title: string;
  description?: string;
}>();

const STYLES: Record<StateVariant, { color: string; label: string }> = {
  loading: { color: 'var(--color-info)', label: '加载中' },
  empty: { color: 'var(--color-text-primary)', label: '暂无内容' },
  denied: { color: 'var(--color-danger)', label: '暂无权限' },
  offline: { color: 'var(--color-warning)', label: '当前离线' },
  failed: { color: 'var(--color-danger)', label: '加载失败' },
};

const icon = {
  color: STYLES[props.variant].color,
  label: STYLES[props.variant].label,
};
</script>

<template>
  <div class="state-view" role="status" :aria-live="variant === 'loading' ? 'polite' : undefined">
    <div class="state-view__icon" aria-hidden="true" :style="{ color: icon.color }">
      <span v-if="variant === 'loading'" class="state-view__spinner"></span>
      <svg v-else-if="variant === 'empty'" viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M6 3h9l4 4v14H6z" />
        <path d="M14 3v5h5" />
      </svg>
      <svg v-else-if="variant === 'denied'" viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="5" y="11" width="14" height="10" rx="2" />
        <path d="M8 11V7a4 4 0 0 1 8 0v4" />
      </svg>
      <svg v-else-if="variant === 'failed'" viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 3 2.5 20h19z" />
        <path d="M12 9v5" />
        <path d="M12 17.5v.5" />
      </svg>
      <svg v-else viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M6 17a5 5 0 1 1 4.9-6h3.2a4 4 0 1 1 0 8" />
        <path d="M3 21l18-18" />
      </svg>
    </div>
    <p class="state-view__title" :style="{ color: icon.color }">{{ title }}</p>
    <p v-if="description" class="state-view__description">{{ description }}</p>
  </div>
</template>

<style scoped>
.state-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-lg) var(--space-md);
  text-align: center;
}

.state-view__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: var(--color-surface);
  border: 2px solid currentColor;
}

.state-view__title {
  margin: 0;
  font-size: var(--font-size-main);
  font-weight: 700;
}

.state-view__description {
  margin: 0;
  max-width: 40ch;
  font-size: var(--font-size-caption);
  color: var(--color-text-primary);
}

.state-view__spinner {
  width: 32px;
  height: 32px;
  border: 4px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: state-spin 0.9s linear infinite;
}

@keyframes state-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
