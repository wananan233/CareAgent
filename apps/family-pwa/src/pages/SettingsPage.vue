<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/components/AppIcon.vue'
import { coreAdapter } from '@/services/adapter'
import { familyDashboardFixture } from '@/scenarios/fixtures'
import { useUiStore } from '@/stores/ui'
const router = useRouter(); const ui = useUiStore(); const busy = ref(false); const confirmRevoke = ref(false); const localNotices = ref(true)
async function revoke() { if (busy.value) return; busy.value = true; try { await coreAdapter.revokeConsent('subject-demo-parent-01', familyDashboardFixture.consent.scope, familyDashboardFixture.consent.version); ui.clearSensitiveState(); router.replace('/error/CONSENT_REVOKED') } finally { busy.value = false; confirmRevoke.value = false } }
function logout() { ui.clearSensitiveState(); router.replace('/error/SIGNED_OUT') }
</script>
<template>
  <main class="app-shell">
    <header class="top-bar"><div><p class="overline">家庭管理员</p><h1>我的</h1></div><span class="profile-avatar">林</span></header>
    <section class="profile-card"><span class="profile-avatar large">林</span><div><h2>林女士</h2><p>演示家庭 · 家属角色</p></div><AppIcon name="chevron" class="chevron" /></section>
    <div class="section-heading"><h2>关怀设置</h2></div>
    <section class="ios-list settings-list">
      <div class="list-row"><span class="row-icon blue"><AppIcon name="bell" /></span><span class="row-main"><b>站内模拟通知</b><small>不发送真实 Push、短信或电话</small></span><button class="switch" :class="{on:localNotices}" :aria-pressed="localNotices" @click="localNotices=!localNotices"><i></i></button></div>
      <div class="list-row"><span class="row-icon purple"><AppIcon name="user" /></span><span class="row-main"><b>当前家庭成员</b><small>演示家庭成员</small></span><AppIcon name="chevron" class="chevron" /></div>
    </section>
    <div class="section-heading"><h2>隐私与授权</h2></div>
    <section class="ios-list settings-list">
      <div class="list-row"><span class="row-icon green"><AppIcon name="lock" /></span><span class="row-main"><b>今日概览读取</b><small>用于展示经授权的家庭摘要</small></span><span class="status success">有效</span></div>
      <div class="list-row"><span class="row-icon amber"><AppIcon name="clock" /></span><span class="row-main"><b>授权有效期</b><small>至 2026 年 12 月 31 日</small></span></div>
      <button class="list-row destructive-row" @click="confirmRevoke=true"><span class="row-icon red"><AppIcon name="lock" /></span><span class="row-main"><b>撤销概览读取授权</b><small>相关页面数据将立即从内存清除</small></span><AppIcon name="chevron" class="chevron" /></button>
    </section>
    <section class="privacy-note"><AppIcon name="shield" /><p>Token、健康正文、完整对话与时间线不会写入浏览器持久存储。</p></section>
    <button class="logout-button" @click="logout">退出演示账户</button>
    <p class="version-label">CareHub 家属端 · 软件仿真演示版</p>
  </main>
  <Transition name="sheet"><div v-if="confirmRevoke" class="sheet-backdrop" @click.self="confirmRevoke=false"><section class="bottom-sheet" role="alertdialog" aria-modal="true"><div class="sheet-handle"></div><span class="sheet-icon danger"><AppIcon name="lock" :size="28" /></span><h2>撤销读取授权？</h2><p>撤销后，概览与报告数据会立即从本次会话内存清除，并跳转到安全说明页。</p><button class="danger-action" :disabled="busy" @click="revoke">{{ busy ? '正在撤销…' : '确认撤销' }}</button><button class="sheet-cancel" @click="confirmRevoke=false">取消</button></section></div></Transition>
</template>
