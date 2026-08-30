<script setup lang="ts">
import { ref } from 'vue'
import type { AgentResponseV1 } from '@carehub/shared-contracts'
import AppIcon from '@/components/AppIcon.vue'
import { coreAdapter, currentSubjectId } from '@/services/adapter'

defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [value: boolean] }>()
const question = ref('')
const answer = ref<AgentResponseV1 | null>(null)
const loading = ref(false)
const unavailable = ref(false)
const sourcesOpen = ref(false)
const prompts = ['今天有什么值得注意？', '最近一周有什么变化？', '为什么这条信息还不能确认？', '最近有什么需要我确认？']
const sourceCount = () => [...new Set(answer.value?.facts.flatMap((fact) => fact.source_refs) ?? [])].length

async function ask(value = question.value) {
  if (!value.trim() || loading.value) return
  loading.value = true; unavailable.value = false
  try { answer.value = await coreAdapter.askReadOnly(currentSubjectId, value) }
  catch { unavailable.value = true }
  finally { loading.value = false; question.value = '' }
}
function close() { emit('update:open', false) }
</script>

<template>
  <Transition name="sheet"><div v-if="open" class="sheet-backdrop" @click.self="close"><section class="bottom-sheet careagent-sheet" role="dialog" aria-modal="true" aria-label="问 CareAgent"><div class="sheet-handle"/><span class="sheet-icon"><AppIcon name="sparkles" :size="27" /></span><h2>问 CareAgent</h2><p>只分析当前已授权的照护记录，不会修改提醒、告警或安全状态。</p>
    <div class="careagent-sheet__chips"><button v-for="prompt in prompts" :key="prompt" @click="ask(prompt)">{{ prompt }}</button></div>
    <label class="careagent-sheet__input"><span class="sr-only">输入照护相关问题</span><input v-model="question" maxlength="120" placeholder="输入一个照护相关问题" @keyup.enter="ask()"/></label>
    <button class="primary-action block" :disabled="loading || !question.trim()" @click="ask()">{{ loading ? '正在整理…' : '发送问题' }}</button>
    <section v-if="unavailable" class="careagent-sheet__notice"><b>CareAgent 暂时不可用</b><span>提醒、安全和联系家人功能仍然正常。</span></section>
    <section v-if="answer" class="careagent-sheet__answer"><h3>CareAgent 回答</h3><p>{{ answer.message }}</p><h4>依据</h4><p v-for="fact in answer.facts" :key="`${fact.text}-${fact.source_refs.join('-')}`">{{ fact.text }}</p><p v-if="!answer.facts.length">没有足够的已授权记录。</p><h4>还不知道什么</h4><p v-for="item in answer.unknowns" :key="item.field">{{ item.field }}：{{ item.reason }}</p><p v-if="!answer.unknowns?.length">本次回复没有返回额外未知项。</p><h4 v-if="answer.why_it_matters?.length">为什么值得关注</h4><p v-for="line in answer.why_it_matters" :key="line">{{ line }}</p><h4 v-if="answer.suggested_safe_actions?.length">建议下一步</h4><p v-for="action in answer.suggested_safe_actions" :key="action">{{ action }}</p><p v-if="answer.fallback !== 'NONE'" class="careagent-sheet__sources">已使用 {{ answer.fallback }}；请以来源记录为准。</p><button class="inline-link" @click="sourcesOpen = !sourcesOpen">{{ sourcesOpen ? '收起来源' : '查看来源' }}</button><p v-if="sourcesOpen" class="careagent-sheet__sources">本次使用 {{ sourceCount() }} 条已授权来源记录；内部编号不会显示。</p></section>
    <button class="sheet-cancel" @click="close">完成</button>
  </section></div></Transition>
</template>

<style scoped>
.careagent-sheet{text-align:left}.careagent-sheet>.sheet-icon{display:grid;margin:0 auto}.careagent-sheet>h2,.careagent-sheet>p{text-align:center}.careagent-sheet__chips{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}.careagent-sheet__chips button{min-height:38px;border:0;border-radius:11px;background:#edf5ff;color:#075ca8;font-size:12px}.careagent-sheet__input{display:block;margin:10px 0}.careagent-sheet__input input{width:100%;min-height:44px;padding:0 11px;border:1px solid #d8d8dd;border-radius:11px;font:inherit}.careagent-sheet__notice,.careagent-sheet__answer{margin-top:14px;padding:13px;border-radius:14px;background:#f2f2f7}.careagent-sheet__notice{display:grid;gap:4px;color:#6d6d72;font-size:12px}.careagent-sheet__answer h3{margin:0 0 7px;font-size:16px}.careagent-sheet__answer h4{margin:12px 0 3px;font-size:12px}.careagent-sheet__answer p{margin:0;color:#515154;font-size:13px;line-height:1.5;text-align:left}.careagent-sheet__sources{margin-top:6px!important;color:#8e8e93!important;font-size:12px!important}.careagent-sheet .inline-link{margin-top:10px;padding:0;border:0;background:transparent;color:#007aff;font-size:13px}@media(prefers-reduced-motion:reduce){.careagent-sheet__chips button{transition:none}}
</style>
