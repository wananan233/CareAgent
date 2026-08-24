<script setup lang="ts">
import { RouterLink } from 'vue-router';

const items = [
  { to: '/home', label: '今日' },
  { to: '/safety', label: '安全提示' },
  { to: '/agent', label: '小护' },
  { to: '/timeline', label: '时间线' },
  { to: '/settings', label: '设置' },
  { to: '/system', label: '系统状态' },
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
  gap: var(--space-xs);
  padding: var(--space-xs) var(--space-md);
  background: var(--color-brand);
}

.nav__link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: var(--touch-min-target);
  padding: 0 var(--space-sm);
  border-radius: var(--radius-md);
  color: var(--color-text-on-dark);
  font-size: var(--font-size-caption);
  font-weight: 700;
  text-decoration: none;
}

.nav__link:hover {
  background: rgba(255, 255, 255, 0.12);
}

.nav__link--active {
  background: var(--color-focus-ring);
  color: var(--color-text-primary);
}
</style>
