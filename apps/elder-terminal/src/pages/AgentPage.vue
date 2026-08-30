<script setup lang="ts">
import { computed, ref } from 'vue';
import PageShell from '@/components/PageShell.vue';
import StateView from '@/components/StateView.vue';
import AiBadge from '@/components/AiBadge.vue';
import { useCareStore } from '@/stores/care';
import { useAppStore } from '@/stores/app';
import { AGENT_FAILURE_LABEL } from '@/contracts/displayMapping';
import { messageFor } from '@/contracts/errorMapping';

const care = useCareStore();
const app = useAppStore();
const explanationOpen = ref(false);
const helpRequested = ref(false);

type AgentView =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'error'; reason: 'UPSTREAM_TIMEOUT' | 'UPSTREAM_FAILED' }
  | { kind: 'failure' }
  | { kind: 'fallback' }
  | { kind: 'response' };

const view = computed<AgentView>(() => {
  if (care.agentLoading) return { kind: 'loading' };
  if (care.agentError === 'SCHEMA_INVALID') return { kind: 'failure' };
  if (care.agentError === 'AGENT_FALLBACK') return { kind: 'fallback' };
  if (care.agentError === 'UPSTREAM_TIMEOUT' || care.agentError === 'UPSTREAM_FAILED') {
    return { kind: 'error', reason: care.agentError };
  }
  if (care.agentError) return { kind: 'failure' };
  if (care.agent) return { kind: 'response' };
  return { kind: 'idle' };
});

async function ask(capability: 'TODAY_STATUS' | 'DAILY_SUMMARY' = 'TODAY_STATUS') {
  // 老人端只请求经 BFF 提供的只读投影，不开放自由聊天或领域状态修改。
  await care.askAgent(capability);
}

const unknownTask = computed(() => care.tasks.find((task) => task.evidence_state === 'UNKNOWN'));
const reminderTime = computed(() => {
  if (!unknownTask.value) return '今天的提醒';
  return new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
    .format(new Date(unknownTask.value.scheduled_at));
});
</script>

<template>
  <PageShell title="CareAgent 智能助手">
    <section class="agent__intro">
      <AiBadge />
      <p>根据今天已有的照护记录，把重要事情说得更简单。</p>
    </section>

    <section class="agent__card">
      <p class="agent__eyebrow">今天怎么样</p>
      <h2>看看今天</h2>
      <p class="agent__lead">只说明已有记录；信息不足时不会猜测或确认服药结果。</p>
      <button type="button" class="agent__primary" :disabled="care.agentLoading || !app.agentEnabled" @click="ask()">
        {{ care.agent ? '重新看看今天' : '看看今天' }}
      </button>
      <button type="button" class="agent__secondary" :disabled="care.agentLoading || !app.agentEnabled" @click="ask('DAILY_SUMMARY')">查看今日简报</button>
    </section>

    <StateView v-if="view.kind === 'loading'" variant="loading" title="正在整理今天的记录" />

    <StateView
      v-else-if="view.kind === 'error'"
      variant="failed"
      title="智能说明暂时不可用"
      :description="`${messageFor(view.reason)}。提醒、安全和联系家人功能仍然正常。`"
    />

    <div v-else-if="view.kind === 'failure'" class="agent__notice" role="status">
      <p>{{ AGENT_FAILURE_LABEL }}</p>
      <p>提醒、安全和联系家人功能仍然正常。</p>
    </div>

    <div v-else-if="view.kind === 'fallback'" class="agent__notice" role="status">
      <p>{{ care.agent?.message }}</p>
      <p>信息不完整时，CareHub 不会自己猜。</p>
    </div>

    <section v-else-if="view.kind === 'response' && care.agent" class="agent__response">
      <AiBadge />
      <p class="agent__message">{{ care.agent.message }}</p>
      <p v-for="(fact, index) in care.agent.facts" :key="index" class="agent__fact">{{ fact.text }}</p>
      <p v-for="item in care.agent.unknowns" :key="item.field" class="agent__fact">还不知道：{{ item.field }}（{{ item.reason }}）</p>
      <p v-for="line in care.agent.why_it_matters" :key="line" class="agent__fact">{{ line }}</p>
      <p v-for="action in care.agent.suggested_safe_actions" :key="action" class="agent__fact">建议：{{ action }}</p>
      <p class="agent__source-note">本次说明基于 {{ care.agent.facts.reduce((count, fact) => count + fact.source_refs.length, 0) }} 条来源记录{{ care.agent.fallback === 'NONE' ? '' : `；${care.agent.fallback}` }}。</p>
    </section>

    <section class="agent__unknown">
      <p class="agent__eyebrow">还有什么不知道</p>
      <h2>{{ care.agent?.unknowns?.length ? '有些事情还需要确认。' : unknownTask ? '提醒已经看到，完成情况仍待确认。' : '请查看今天的已授权记录。' }}</h2>
      <p v-for="item in care.agent?.unknowns" :key="item.field">{{ item.field }}：{{ item.reason }}</p>
      <p v-if="!care.agent?.unknowns?.length && unknownTask">我知道 {{ reminderTime }} 有一条提醒，但不知道您是否已经完成。信息不完整时，CareHub 不会自己猜。</p>
      <div class="agent__actions"><button v-if="unknownTask" type="button" class="agent__secondary" @click="explanationOpen = true">这是什么意思？</button><button type="button" class="agent__secondary" @click="ask()">更新今天说明</button></div>
    </section>

    <section class="agent__support">
      <p class="agent__eyebrow">需要帮助吗</p>
      <h2>没看懂？联系家人</h2>
      <p v-if="helpRequested">已为您记下需要帮助，您也可以直接联系家人。</p>
      <button v-else type="button" class="agent__secondary" @click="helpRequested = true">联系家人</button>
    </section>

    <div v-if="explanationOpen" class="agent__sheet-backdrop" @click.self="explanationOpen = false">
      <section class="agent__sheet" role="dialog" aria-modal="true" aria-label="提醒说明">
        <p class="agent__eyebrow">这是什么意思？</p>
        <h2>这是一条今天计划中的提醒。</h2>
        <p>系统只知道您已经看到提醒，不能确认是否已经完成。</p>
        <p class="agent__source-note">信息依据：{{ reminderTime }} 的提醒记录。</p>
        <button type="button" class="agent__primary" @click="explanationOpen = false">我知道了</button>
      </section>
    </div>
  </PageShell>
</template>

<style scoped>
.agent__intro,
.agent__response,
.agent__unknown,
.agent__support,
.agent__card {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  padding: var(--space-md);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.agent__intro {
  padding: 0;
  background: transparent;
}

.agent__intro p,
.agent__card p,
.agent__unknown p,
.agent__support p,
.agent__notice p,
.agent__sheet p { margin: 0; }

.agent__card { border: 2px solid var(--color-brand); }
.agent__unknown { border: 2px solid #d8c4ae; }
.agent__support { border: 2px solid var(--color-info); }
.agent__response { border: 2px solid var(--color-brand); }

.agent__eyebrow { color: var(--color-text-secondary); font-size: var(--font-size-caption); font-weight: 700; }
.agent__card h2, .agent__unknown h2, .agent__support h2, .agent__sheet h2 { margin: 0; font-size: var(--font-size-main); line-height: 1.25; }
.agent__lead { color: var(--color-text-secondary); }
.agent__message { margin: 0; font-size: var(--font-size-body); font-weight: 700; }
.agent__fact { margin: 0; padding-top: var(--space-sm); border-top: 1px solid #e7ddd3; }

.agent__primary,
.agent__secondary,
.agent__feedback button {
  min-height: var(--touch-min-target);
  padding: 0 var(--space-md);
  border: 2px solid var(--color-brand);
  border-radius: var(--radius-md);
  font-size: var(--font-size-body);
  font-weight: 700;
  cursor: pointer;
}

.agent__primary { background: var(--color-brand); color: var(--color-text-on-dark); }
.agent__secondary, .agent__feedback button { background: var(--color-surface); color: var(--color-brand); }
.agent__primary:disabled { opacity: .6; cursor: not-allowed; }
.agent__actions{display:flex;flex-wrap:wrap;gap:var(--space-sm)}
.agent__feedback { display: flex; flex-wrap: wrap; gap: var(--space-xs); align-items: center; margin-top: var(--space-sm); }
.agent__feedback span { font-weight: 700; }
.agent__feedback button { min-height: 48px; padding: 0 var(--space-sm); font-size: var(--font-size-caption); }
.agent__feedback--active { background: #f1e4d5 !important; }

.agent__notice { padding: var(--space-md); border: 2px solid var(--color-warning); border-radius: var(--radius-lg); background: var(--color-surface); }
.agent__source-note { color: var(--color-text-secondary); font-size: var(--font-size-caption); }

.agent__sheet-backdrop { position: fixed; inset: 0; z-index: 20; display: grid; align-items: end; background: rgba(0, 0, 0, .48); }
.agent__sheet { padding: var(--space-lg) var(--space-md); display: flex; flex-direction: column; gap: var(--space-md); border-radius: 24px 24px 0 0; background: var(--color-surface); }

@media (min-width: 720px) {
  .agent__sheet { max-width: 720px; width: 100%; justify-self: center; border-radius: 24px 24px 0 0; }
}
</style>
