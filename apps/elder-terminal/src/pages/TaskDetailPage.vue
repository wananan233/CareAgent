<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import PageShell from '@/components/PageShell.vue';
import StateView from '@/components/StateView.vue';
import { useCareStore } from '@/stores/care';
import {
  ACKNOWLEDGE_ACTION_LABEL,
  EVIDENCE_LABEL,
  loadStateFor,
  TASK_KIND_LABEL,
  TASK_STATUS_LABEL,
} from '@/contracts/displayMapping';

const route = useRoute();
const care = useCareStore();
const feedback = ref<string | null>(null);

const task_id = computed(() => route.params.id as string);
const task = computed(() => care.tasks.find((t) => t.task_id === task_id.value));
const errorState = computed(() => (care.loadError ? loadStateFor(care.loadError) : null));

const timeLabel = computed(() =>
  task.value
    ? new Date(task.value.scheduled_at).toLocaleString('zh-CN', {
        month: 'numeric',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '--',
);

const alreadyAcknowledged = computed(() => task.value?.status === 'ACKNOWLEDGED');

onMounted(() => {
  if (care.tasks.length === 0) {
    care.refresh();
  }
});

async function acknowledge() {
  feedback.value = null;
  const result = await care.acknowledgeTask(task_id.value);
  if (result.ok) {
    feedback.value = '确认请求已接收。';
  } else if (result.error.code === 'VERSION_CONFLICT') {
    feedback.value = '数据已更新，请刷新后重试。';
  } else if ((result.error.reason_code ?? result.error.code) === 'NETWORK_OFFLINE') {
    feedback.value = care.pendingResubmit?.label ?? '待网络恢复后重新提交';
  } else {
    feedback.value = '操作失败，请稍后重试。';
  }
}
</script>

<template>
  <PageShell title="提醒详情">
    <StateView v-if="care.loading && !task" variant="loading" title="正在加载" />
    <StateView
      v-else-if="errorState"
      :variant="errorState.variant"
      :title="errorState.title"
      :description="errorState.description"
    />
    <StateView
      v-else-if="!task"
      variant="empty"
      title="暂无任务详情"
      description="未找到该任务。"
    />
    <template v-else>
      <dl class="detail">
        <div class="detail__row">
          <dt class="detail__term">提醒</dt>
          <dd class="detail__desc">{{ TASK_KIND_LABEL[task.kind] }}</dd>
        </div>
        <div class="detail__row">
          <dt class="detail__term">时间</dt>
          <dd class="detail__desc">{{ timeLabel }}</dd>
        </div>
        <div class="detail__row">
          <dt class="detail__term">状态</dt>
          <dd class="detail__desc">{{ TASK_STATUS_LABEL[task.status] }}</dd>
        </div>
        <div class="detail__row">
          <dt class="detail__term">完成情况</dt>
          <dd class="detail__desc">{{ EVIDENCE_LABEL[task.evidence_state] }}</dd>
        </div>
        <div class="detail__row">
          <dt class="detail__term">来源</dt>
          <dd class="detail__desc">CareHub 提醒记录</dd>
        </div>
      </dl>

      <button
        v-if="!alreadyAcknowledged"
        type="button"
        class="detail__action"
        :disabled="care.submitting"
        @click="acknowledge"
      >
        {{ ACKNOWLEDGE_ACTION_LABEL }}
      </button>
      <p v-else class="detail__done">已确认看到提醒；系统仍不能确认是否已经完成。</p>
      <RouterLink to="/agent" class="detail__agent">✦ CareAgent：为什么还是待确认？</RouterLink>
      <p v-if="feedback" class="detail__feedback" role="status">{{ feedback }}</p>
    </template>
  </PageShell>
</template>

<style scoped>
.detail {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  margin: 0;
  border: 2px solid var(--color-brand);
  border-radius: var(--radius-lg);
  padding: var(--space-md);
}

.detail__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
}

.detail__term {
  font-size: var(--font-size-body);
  font-weight: 700;
}

.detail__desc {
  margin: 0;
  font-size: var(--font-size-body);
  text-align: right;
}

.detail__action {
  align-self: flex-start;
  min-height: var(--touch-min-target);
  min-width: 220px;
  padding: 0 var(--space-md);
  border: 2px solid var(--color-brand);
  border-radius: var(--radius-md);
  background: var(--color-brand);
  color: var(--color-text-on-dark);
  font-size: var(--font-size-body);
  font-weight: 700;
  cursor: pointer;
}

.detail__action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.detail__agent { display:inline-flex; align-items:center; min-height:var(--touch-min-target); color:var(--color-brand); font-size:var(--font-size-body); font-weight:700; }

.detail__done {
  margin: 0;
  font-size: var(--font-size-body);
  color: var(--color-success);
  font-weight: 700;
}

.detail__feedback {
  margin: 0;
  font-size: var(--font-size-body);
  color: var(--color-info);
}
</style>
