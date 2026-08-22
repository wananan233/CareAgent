<script setup lang="ts">
defineProps<{ title: string }>();
</script>

<template>
  <section class="page-shell">
    <h1 class="page-shell__title">{{ title }}</h1>
    <div class="page-shell__body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.page-shell {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.page-shell__title {
  margin: 0;
  font-size: var(--font-size-main);
  line-height: 1.2;
}

.page-shell__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}
</style>
