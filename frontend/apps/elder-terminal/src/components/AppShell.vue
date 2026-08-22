<script setup lang="ts">
import { onMounted, watch } from 'vue';
import { useAppStore } from '@/stores/app';
import { useNetworkStatus } from '@/composables/useNetworkStatus';
import SimulatedDataBadge from './SimulatedDataBadge.vue';
import SystemStatusBar from './SystemStatusBar.vue';
import NavBar from './NavBar.vue';
import GlobalSafetyCard from './GlobalSafetyCard.vue';

const app = useAppStore();
useNetworkStatus();

function applyFontScale() {
  document.documentElement.style.setProperty('--font-scale', String(app.fontScale));
}

onMounted(applyFontScale);
watch(() => app.fontScale, applyFontScale);
</script>

<template>
  <div class="app-shell">
    <a class="app-shell__skip" href="#main-content">跳到主要内容</a>
    <header class="app-shell__header">
      <span class="app-shell__brand">CareHub 老人端</span>
      <SimulatedDataBadge />
    </header>
    <SystemStatusBar />
    <NavBar />
    <main id="main-content" class="app-shell__main" tabindex="-1">
      <GlobalSafetyCard />
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-shell__skip {
  position: absolute;
  left: -9999px;
  top: 0;
  padding: var(--space-sm);
  background: var(--color-brand);
  color: var(--color-text-on-dark);
  font-size: var(--font-size-body);
  font-weight: 700;
}

.app-shell__skip:focus {
  left: 0;
  z-index: 10;
}

.app-shell__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
  padding: var(--space-md);
  background: var(--color-brand);
  color: var(--color-text-on-dark);
}

.app-shell__brand {
  font-size: var(--font-size-main);
  font-weight: 700;
}

.app-shell__main {
  flex: 1;
  padding: var(--space-md);
}
</style>
