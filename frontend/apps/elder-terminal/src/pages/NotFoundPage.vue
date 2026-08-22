<script setup lang="ts">
import PageShell from '@/components/PageShell.vue';
import StateView from '@/components/StateView.vue';
</script>

<template>
  <PageShell title="页面不存在">
    <StateView variant="empty" title="您访问的页面不存在" />
  </PageShell>
</template>
