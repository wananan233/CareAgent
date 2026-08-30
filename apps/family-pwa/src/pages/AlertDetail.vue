<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { AlertViewV1, RequestReceiptV1 } from '@carehub/shared-contracts'
import AppIcon from '@/components/AppIcon.vue'
import { coreAdapter, currentSubjectId } from '@/services/adapter'
import { useUiStore } from '@/stores/ui'
const props = defineProps({ id: { type: String, required: true } })
const ui = useUiStore()
const alert = ref<AlertViewV1 | null>(null)
const receipt = ref<RequestReceiptV1 | null>(null)
const busy = ref(false)
const failure = ref('')
const occurred = computed(() => alert.value ? new Date(alert.value.occurred_at).toLocaleString('zh-CN', { month:'long', day:'numeric', hour:'2-digit', minute:'2-digit' }) : '')
onMounted(async () => { alert.value = (await coreAdapter.getAlerts(currentSubjectId)).find(x => x.alert_id === props.id) ?? null })
async function viewed() { if (!alert.value || busy.value || receipt.value) return; busy.value = true; failure.value = ''; try { receipt.value = await coreAdapter.acknowledgeAlert(currentSubjectId, alert.value.alert_id, { command_id: crypto.randomUUID(), idempotency_key: `viewed-${alert.value.alert_id}`, expected_version: alert.value.version, reason_code: 'ACKNOWLEDGE_VIEWED' }); ui.markAlertViewed(alert.value.alert_id) } catch { failure.value = '请求未成功，请稍后重试。' } finally { busy.value = false } }
</script>
<template>
  <main class="detail-shell">
    <nav class="detail-nav"><RouterLink to="/tasks">‹ 提醒</RouterLink><b>告警详情</b><span></span></nav>
    <section v-if="alert" class="alert-hero"><span class="alert-symbol"><AppIcon name="shield" :size="34" /></span><div class="alert-level">{{ alert.safety_level }} · 需要关注</div><h1>烟雾/燃气模拟告警</h1><p>{{ occurred }}</p></section>
    <section v-if="alert" class="inset-group">
      <div class="info-row"><span>当前状态</span><b>{{ receipt ? '已查看请求已记录' : '告警仍处于开放状态' }}</b></div>
      <div class="info-row"><span>事件来源</span><b>{{ alert.source_refs[0].label }}</b></div>
      <div class="info-row"><span>数据质量</span><b>{{ alert.quality }}</b></div>
      <div class="info-row"><span>版本</span><b>v{{ alert.version }}</b></div>
    </section>
    <section class="safety-note"><AppIcon name="shield" /><div><b>重要说明</b><p>“已查看”只会留下审计记录，不会解除、取消或降低安全告警。最终状态由 CareHub Core 管理。</p></div></section>
    <button v-if="alert && !receipt" class="primary-action block" :disabled="busy" @click="viewed">{{ busy ? '正在提交…' : '记录我已查看' }}</button>
    <section v-if="receipt" class="receipt-card"><span><AppIcon name="check" /></span><div><b>已记录</b><p>{{ new Date(receipt.audit_time).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'}) }} · 请求号 {{ receipt.request_id }}</p><small>告警仍由 Core 管理</small></div></section>
    <p v-if="failure" class="inline-error">{{ failure }}</p>
  </main>
</template>
