<script setup lang="ts">
import { FONT_SCALE_OPTIONS, useAppStore } from '@/stores/app';
import PageShell from '@/components/PageShell.vue';

const app = useAppStore();

const FONT_LABELS: Record<number, string> = {
  1: '标准',
  1.25: '较大',
  1.5: '最大',
};

function restoreDefaults() {
  app.setFontScale(1);
  app.setSoundEnabled(false);
  app.setNonCriticalReminders(true);
}
</script>

<template>
  <PageShell title="设置">
    <fieldset class="settings__group">
      <legend class="settings__legend">文字大小</legend>
      <div class="settings__options" role="radiogroup" aria-label="文字大小">
        <button
          v-for="scale in FONT_SCALE_OPTIONS"
          :key="scale"
          type="button"
          class="settings__option"
          :class="{ 'settings__option--active': app.fontScale === scale }"
          :aria-pressed="app.fontScale === scale"
          @click="app.setFontScale(scale)"
        >
          {{ FONT_LABELS[scale] }}
        </button>
      </div>
      <p class="settings__preview">预览：今天要按时服药。</p>
    </fieldset>

    <fieldset class="settings__group">
      <legend class="settings__legend">提醒与声音</legend>
      <label class="settings__toggle">
        <input
          v-model="app.nonCriticalReminders"
          type="checkbox"
          class="settings__checkbox"
        />
        <span>非紧急提醒</span>
      </label>
      <label class="settings__toggle">
        <input v-model="app.soundEnabled" type="checkbox" class="settings__checkbox" />
        <span>声音提示</span>
      </label>
    </fieldset>

    <button type="button" class="settings__restore" @click="restoreDefaults">
      恢复默认设置
    </button>
  </PageShell>
</template>

<style scoped>
.settings__group {
  border: 2px solid var(--color-brand);
  border-radius: var(--radius-lg);
  padding: var(--space-md);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.settings__legend {
  font-size: var(--font-size-body);
  font-weight: 700;
  padding: 0 var(--space-xs);
}

.settings__options {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.settings__option {
  min-height: var(--touch-min-target);
  min-width: 120px;
  padding: 0 var(--space-md);
  border: 2px solid var(--color-brand);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--font-size-body);
  font-weight: 700;
  cursor: pointer;
}

.settings__option--active {
  background: var(--color-brand);
  color: var(--color-text-on-dark);
}

.settings__preview {
  margin: 0;
  font-size: var(--font-size-body);
}

.settings__toggle {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  min-height: var(--touch-min-target);
  font-size: var(--font-size-body);
  cursor: pointer;
}

.settings__checkbox {
  width: 28px;
  height: 28px;
}

.settings__restore {
  align-self: flex-start;
  min-height: var(--touch-min-target);
  min-width: 180px;
  padding: 0 var(--space-md);
  border: 2px solid var(--color-danger);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-danger);
  font-size: var(--font-size-body);
  font-weight: 700;
  cursor: pointer;
}
</style>
