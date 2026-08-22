<script setup lang="ts">
import { SIMULATED_DATA_LABEL } from '@carehub/shared-contracts';
</script>

<template>
  <span class="sim-badge" role="status">
    <span class="sim-badge__icon" aria-hidden="true">◈</span>
    {{ SIMULATED_DATA_LABEL }}
  </span>
</template>

<style scoped>
.sim-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  padding: 6px 12px;
  border: 2px solid var(--color-warning);
  border-radius: 999px;
  color: var(--color-warning);
  font-size: var(--font-size-caption);
  font-weight: 700;
  background: var(--color-surface);
}
</style>
