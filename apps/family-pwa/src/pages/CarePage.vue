<script setup lang="ts">
import { ref } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import { coreAdapter, currentSubjectId } from '@/services/adapter'
import { useUiStore } from '@/stores/ui'
const ui = useUiStore()
const busy = ref(false)
const selected = ref<'SEND_CARE_NOTE' | 'REMINDER_PREFERENCE' | null>(null)
const toast = ref('')
const labels = { SEND_CARE_NOTE: '发送关怀问候', REMINDER_PREFERENCE: '调整普通提醒偏好' }
async function confirm() {
  if (!selected.value || busy.value) return
  busy.value = true
  try { const result = await coreAdapter.createCareRequest(currentSubjectId, selected.value, `care-${selected.value}`); ui.addCareHistory(result); toast.value = '请求已记录'; selected.value = null; setTimeout(() => toast.value = '', 2200) }
  finally { busy.value = false }
}
</script>
<template>
  <main class="app-shell">
    <header class="top-bar"><div><p class="overline">低风险请求</p><h1>关怀</h1></div><span class="header-symbol pink"><AppIcon name="heart" :size="23" /></span></header>
    <section class="care-hero"><span><AppIcon name="heart" :size="26" /></span><div><h2>表达关心，不替代照护决策</h2><p>所有请求均为站内模拟，不会拨打电话或发送真实消息。</p></div></section>
    <div class="section-heading"><h2>快捷关怀</h2></div>
    <section class="action-grid">
      <button class="action-card" @click="selected='SEND_CARE_NOTE'"><span class="row-icon pink"><AppIcon name="heart" /></span><b>关怀问候</b><small>提交一条预设问候请求</small><em>推荐</em></button>
      <button class="action-card" @click="selected='REMINDER_PREFERENCE'"><span class="row-icon blue"><AppIcon name="bell" /></span><b>提醒偏好</b><small>申请调整普通提醒方式</small></button>
    </section>
    <section class="contact-suggestion"><span class="row-icon amber"><AppIcon name="pill" /></span><div><p>建议联系</p><h2>有 1 项状态建议确认</h2><small>可以联系老人确认提醒是否完成。</small></div><button type="button" @click="selected='SEND_CARE_NOTE'">联系老人确认</button></section>
    <div class="section-heading"><h2>本次会话记录</h2><span>{{ ui.careHistory.length }} 条</span></div>
    <section class="ios-list">
      <div v-if="!ui.careHistory.length" class="empty-row"><span><AppIcon name="clock" /></span><div><b>暂无操作</b><small>提交后的回执会保留在本次会话中</small></div></div>
      <div v-for="item in ui.careHistory" :key="item.request_id" class="list-row"><span class="row-icon green"><AppIcon name="check" /></span><span class="row-main"><b>{{ labels[item.template as keyof typeof labels] }}</b><small>已记录 · {{ new Date(item.audit_time).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }}</small></span><span class="status success">完成</span></div>
    </section>
  </main>
  <Transition name="sheet"><div v-if="selected" class="sheet-backdrop" @click.self="selected=null"><section class="bottom-sheet" role="dialog" aria-modal="true"><div class="sheet-handle"></div><span class="sheet-icon"><AppIcon :name="selected === 'SEND_CARE_NOTE' ? 'heart' : 'bell'" :size="28" /></span><h2>{{ labels[selected] }}</h2><p>将向 CareHub Core 提交一条受限模拟请求。没有自由收件人，也不会产生电话、短信或真实 Push。</p><button class="primary-action" :disabled="busy" @click="confirm">{{ busy ? '正在提交…' : '确认提交' }}</button><button class="sheet-cancel" @click="selected=null">取消</button></section></div></Transition>
  <div v-if="toast" class="toast"><AppIcon name="check" />{{ toast }}</div>
</template>
