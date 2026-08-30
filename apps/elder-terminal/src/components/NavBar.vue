<script setup lang="ts">
import { RouterLink } from 'vue-router';

const items = [
  { to: '/home', label: '今天' },
  { to: '/reminders', label: '提醒' },
  { to: '/safety', label: '安全' },
  { to: '/agent', label: '✦ CareAgent' },
  { to: '/settings', label: '设置' },
];
</script>

<template>
  <nav class="nav" aria-label="主导航">
    <RouterLink
      v-for="item in items"
      :key="item.to"
      :to="item.to"
      class="nav__link"
      active-class="nav__link--active"
    >
      {{ item.label }}
    </RouterLink>
  </nav>
</template>

<style scoped>
.nav {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  width: min(100% - 48px, 1040px);
  margin: var(--space-sm) auto 0;
  padding: 6px;
  border-radius: var(--radius-lg);
  background: var(--color-surface-muted);
}

.nav__link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: var(--touch-min-target);
  flex: 1 1 128px;
  padding: 0 12px;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: var(--font-size-caption);
  font-weight: 700;
  white-space: nowrap;
  text-decoration: none;
}

.nav__link:hover {
  background: rgba(255, 255, 255, 0.72);
}

.nav__link--active {
  background: var(--color-surface);
  color: var(--color-brand);
  box-shadow: 0 1px 3px rgba(41, 38, 34, .12);
}
</style>
