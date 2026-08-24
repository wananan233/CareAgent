<script setup lang="ts">
import { computed, ref } from 'vue';
import PageShell from '@/components/PageShell.vue';
import StateView from '@/components/StateView.vue';
import AiBadge from '@/components/AiBadge.vue';
import QualityBadge from '@/components/QualityBadge.vue';
import SourceDrawer from '@/components/SourceDrawer.vue';
import { useCareStore } from '@/stores/care';
import { AGENT_FAILURE_LABEL } from '@/contracts/displayMapping';
import { messageFor } from '@/contracts/errorMapping';

const care = useCareStore();
const question = ref('');

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

async function ask() {
  const text = question.value.trim();
  if (!text) return;
  await care.askAgent(text);
}
</script>

<template>
  <PageShell title="小护">
    <form class="agent__form" @submit.prevent="ask">
      <label class="agent__label" for="agent-question">向小护提问</label>
      <div class="agent__input-row">
        <input
          id="agent-question"
          v-model="question"
          class="agent__input"
          type="text"
          placeholder="例如：今天我需要做什么？"
        />
        <button type="submit" class="agent__submit" :disabled="care.agentLoading">
          提问
        </button>
      </div>
    </form>

    <StateView v-if="view.kind === 'loading'" variant="loading" title="小护正在思考" />

    <StateView
      v-else-if="view.kind === 'error'"
      variant="failed"
      title="暂时无法回答"
      :description="messageFor(view.reason)"
    />

    <div v-else-if="view.kind === 'failure'" class="agent__failure" role="status">
      <p class="agent__failure-text">{{ AGENT_FAILURE_LABEL }}</p>
    </div>

    <div v-else-if="view.kind === 'fallback'" class="agent__fallback" role="status">
      <p class="agent__fallback-text">{{ care.agent?.message }}</p>
    </div>

    <section v-else-if="view.kind === 'response' && care.agent" class="agent__response">
      <div class="agent__head">
        <AiBadge />
        <p class="agent__message">{{ care.agent.message }}</p>
      </div>
      <ul v-if="care.agent.facts.length > 0" class="agent__facts">
        <li v-for="(f, i) in care.agent.facts" :key="i" class="agent__fact">
          <p class="agent__statement">{{ f.statement }}</p>
          <div class="agent__fact-meta">
            <QualityBadge :quality="f.confidence" />
            <SourceDrawer :sources="f.source_refs" />
          </div>
        </li>
      </ul>
    </section>
  </PageShell>
</template>

<style scoped>
.agent__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.agent__label {
  font-size: var(--font-size-body);
  font-weight: 700;
}

.agent__input-row {
  display: flex;
  gap: var(--space-sm);
}

.agent__input {
  flex: 1;
  min-height: var(--touch-min-target);
  padding: 0 var(--space-md);
  border: 2px solid var(--color-brand);
  border-radius: var(--radius-md);
  font-size: var(--font-size-body);
  background: var(--color-surface);
}

.agent__submit {
  min-height: var(--touch-min-target);
  padding: 0 var(--space-md);
  border: 2px solid var(--color-brand);
  border-radius: var(--radius-md);
  background: var(--color-brand);
  color: var(--color-text-on-dark);
  font-size: var(--font-size-body);
  font-weight: 700;
  cursor: pointer;
}

.agent__submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.agent__failure,
.agent__fallback {
  padding: var(--space-md);
  border: 2px solid var(--color-warning);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.agent__failure-text,
.agent__fallback-text {
  margin: 0;
  font-size: var(--font-size-body);
}

.agent__response {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  padding: var(--space-md);
  border: 2px solid var(--color-brand);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.agent__head {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.agent__message {
  margin: 0;
  font-size: var(--font-size-body);
}

.agent__facts {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.agent__fact {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  padding: var(--space-sm);
  border: 2px solid var(--color-info);
  border-radius: var(--radius-md);
}

.agent__statement {
  margin: 0;
  font-size: var(--font-size-body);
  font-weight: 700;
}

.agent__fact-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-sm);
}
</style>
