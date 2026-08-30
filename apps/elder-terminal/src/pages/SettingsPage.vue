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
  app.setAgentEnabled(true);
}
</script>

<template>
  <PageShell title="设置">
    <section class="settings__group">
      <h2 class="settings__legend">文字大小</h2>
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
    </section>

    <section class="settings__group">
      <h2 class="settings__legend">提醒与声音</h2>
      <label class="settings__row">
        <span>普通提醒</span><input v-model="app.nonCriticalReminders" type="checkbox" class="settings__switch" role="switch" />
      </label>
      <label class="settings__row">
        <span>声音提醒</span><input v-model="app.soundEnabled" type="checkbox" class="settings__switch" role="switch" />
      </label>
      <label class="settings__row">
        <span>CareHub 智能说明</span><input v-model="app.agentEnabled" type="checkbox" class="settings__switch" role="switch" />
      </label>
    </section>
    <section class="settings__group settings__group--links"><h2 class="settings__legend">系统信息</h2><RouterLink to="/system">查看系统信息 <span>›</span></RouterLink></section>

    <button type="button" class="settings__restore" @click="restoreDefaults">
      恢复默认设置
    </button>
  </PageShell>
</template>

<style scoped>
.settings__group {
  border: 0;
  border-radius: var(--radius-lg);
  padding: var(--space-md);
  background:var(--color-surface);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.settings__legend {
  margin:0;
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

.settings__row {
  display: flex;
  align-items: center;
  justify-content:space-between;
  min-height: var(--touch-min-target);
  font-size: var(--font-size-body);
  cursor: pointer;
}

.settings__switch { appearance:none;width:56px;height:32px;margin:0;border:0;border-radius:999px;background:#c9c5bd;cursor:pointer;position:relative;transition:.2s }.settings__switch::after{content:"";position:absolute;width:26px;height:26px;left:3px;top:3px;border-radius:50%;background:#fff;box-shadow:0 1px 2px #777;transition:.2s}.settings__switch:checked{background:var(--color-brand)}.settings__switch:checked::after{transform:translateX(24px)}
.settings__group--links a{display:flex;justify-content:space-between;align-items:center;min-height:var(--touch-min-target);color:var(--color-text-primary);text-decoration:none}.settings__group--links a span{color:var(--color-brand);font-size:32px}

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
