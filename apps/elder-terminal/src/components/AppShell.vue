<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useAppStore } from '@/stores/app';
import { useCareStore } from '@/stores/care';
import { useNetworkStatus } from '@/composables/useNetworkStatus';
import SystemStatusBar from './SystemStatusBar.vue';
import NavBar from './NavBar.vue';
import GlobalSafetyCard from './GlobalSafetyCard.vue';

const app = useAppStore();
const care = useCareStore();
const asleep = ref(true);
const clock = ref(new Date());
let timer: ReturnType<typeof setInterval> | undefined;
const time = computed(() => clock.value.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }));
const sleepStatus = computed(() => care.dashboard?.safetyStatus === 'OPEN' ? '有一项安全提醒待查看' : '今日状态良好');
const sleepMedication = computed(() => care.tasks.find((task) => task.kind === 'MEDICATION_DUE' && task.status !== 'ACKNOWLEDGED'));
const medicationTime = computed(() => sleepMedication.value ? new Date(sleepMedication.value.scheduled_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : '');
useNetworkStatus();

function applyFontScale() {
  document.documentElement.style.setProperty('--font-scale', String(app.fontScale));
}

onMounted(() => { applyFontScale(); timer = setInterval(() => { clock.value = new Date(); }, 30_000); });
onUnmounted(() => { if (timer) clearInterval(timer); });
watch(() => app.fontScale, applyFontScale);
</script>

<template>
  <div class="app-shell">
    <button v-if="asleep" class="sleep-screen" type="button" aria-label="轻触进入 CareHub 老人端" @click="asleep = false">
      <div class="sleep-screen__panel">
        <div class="sleep-screen__top"><time>{{ time }}</time><span class="sleep-screen__sun" aria-hidden="true">☀</span></div>
        <div class="sleep-screen__line"></div>
        <p><span aria-hidden="true">☻</span> {{ sleepStatus }}</p>
        <span class="sleep-screen__agent">✦ CareAgent 已整理今日照护信息</span>
        <div v-if="sleepMedication" class="sleep-screen__medication">
          <span class="sleep-screen__medication-dot" aria-hidden="true"></span>
          <div><strong>用药提醒</strong><small>{{ medicationTime }} · 完成情况待确认</small></div>
        </div>
        <small>轻触屏幕进入 CareHub</small>
      </div>
    </button>
    <a class="app-shell__skip" href="#main-content">跳到主要内容</a>
    <header class="app-shell__header">
      <span class="app-shell__brand">CareHub 老人端</span>
      <span class="app-shell__greeting">今天，安心陪伴</span>
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
.sleep-screen { position: fixed; z-index: 100; inset: 0; display: grid; place-items: center; width: 100%; border: 0; padding: 24px; background: #050505; cursor: pointer; }
.sleep-screen__panel { width: min(100%, 720px); min-height: 360px; padding: 42px; border: 0; border-radius: 0; background: #050505; color: #fff8e9; box-shadow: none; text-align: left; }
.sleep-screen__top { display: flex; align-items: center; justify-content: space-between; }.sleep-screen__top time { font-size: clamp(44px, 9vw, 76px); font-weight: 500; letter-spacing: -3px; }.sleep-screen__sun { color: #f4d68a; font-size: clamp(46px, 8vw, 72px); }.sleep-screen__line { height: 1px; margin: 24px 0; background: rgba(255,248,233,.35); }.sleep-screen__panel p { margin: 0; color: #d8dfab; font-size: clamp(20px, 4vw, 30px); }.sleep-screen__panel small { display:block; margin-top: 48px; color: rgba(255,248,233,.62); font-size: 16px; }
.sleep-screen__medication { display:flex; align-items:center; gap:18px; margin-top:26px; padding:18px 20px; border-radius:16px; background:rgba(61,119,99,.72); color:#fff; }.sleep-screen__medication-dot { width:20px; height:20px; flex:none; border-radius:50%; background:#c9ffe0; box-shadow:0 0 14px rgba(201,255,224,.65); }.sleep-screen__medication strong { display:block; font-size:24px; }.sleep-screen__medication small { margin:3px 0 0; color:rgba(255,255,255,.85); font-size:15px; }
.sleep-screen__agent { display:block; margin-top:18px; color:#b8d5ca; font-size:18px; }

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
  padding: var(--space-sm) max(var(--space-md), calc((100% - 1120px) / 2));
  background: var(--color-surface);
  color: var(--color-text-primary);
  border-bottom: 1px solid rgba(41, 38, 34, .08);
}

.app-shell__brand {
  font-size: var(--font-size-main);
  font-weight: 700;
}
.app-shell__greeting { color: var(--color-text-secondary); font-size: var(--font-size-caption); }

.app-shell__main {
  flex: 1;
  width: min(100% - 48px, 1040px);
  margin: 0 auto;
  padding: var(--space-md) 0 var(--space-lg);
}
</style>
