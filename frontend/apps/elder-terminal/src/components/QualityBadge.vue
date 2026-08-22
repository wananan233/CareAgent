<script setup lang="ts">
import { computed } from 'vue';
import type { QualityStatus } from '@carehub/shared-contracts';
import { QUALITY_LABEL } from '@/contracts/displayMapping';

const props = defineProps<{
  quality: QualityStatus;
  reason?: string;
}>();

const STYLES: Record<QualityStatus, { color: string; glyph: string }> = {
  VALID: { color: 'var(--color-success)', glyph: '✓' },
  LOW: { color: 'var(--color-warning)', glyph: '!' },
  CONFLICT: { color: 'var(--color-danger)', glyph: '!' },
  UNKNOWN: { color: 'var(--color-text-primary)', glyph: '?' },
};

const style = computed(() => STYLES[props.quality]);
</script>

<template>
  <span class="quality" :style="{ color: style.color, borderColor: style.color }">
    <span class="quality__glyph" aria-hidden="true">{{ style.glyph }}</span>
    <span class="quality__label">{{ QUALITY_LABEL[quality] }}</span>
    <span v-if="reason" class="quality__reason">（{{ reason }}）</span>
  </span>
</template>

<style scoped>
.quality {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  padding: 4px 10px;
  border: 2px solid;
  border-radius: 999px;
  font-size: var(--font-size-caption);
  font-weight: 700;
  background: var(--color-surface);
}

.quality__glyph {
  font-weight: 900;
}

.quality__reason {
  font-weight: 400;
}
</style>
