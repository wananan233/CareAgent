<script setup lang="ts">
/** AI 身份标识：标记内容由受控 Agent 生成（红线：不可与真实医疗记录混淆）。 */
</script>

<template>
  <span class="ai-badge" role="status">
    <span class="ai-badge__icon" aria-hidden="true">✦</span>
    AI 生成
  </span>
</template>

<style scoped>
.ai-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  padding: 6px 12px;
  border: 2px solid var(--color-info);
  border-radius: 999px;
  color: var(--color-info);
  font-size: var(--font-size-caption);
  font-weight: 700;
  background: var(--color-surface);
}
</style>
