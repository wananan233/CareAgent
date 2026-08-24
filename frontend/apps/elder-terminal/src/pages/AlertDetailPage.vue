<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import PageShell from '@/components/PageShell.vue';
import StateView from '@/components/StateView.vue';
import { useCareStore } from '@/stores/care';
import {
  ALERT_KIND_LABEL,
  ALERT_STATUS_LABEL,
  loadStateFor,
} from '@/contracts/displayMapping';

const route = useRoute();
const care = useCareStore();
const feedback = ref<string | null>(null);

const alert_id = computed(() => route.params.id as string);
const alert = computed(() => care.alerts.find((a) => a.alert_id === alert_id.value));
const errorState = computed(() => (care.loadError ? loadStateFor(care.loadError) : null));

const timeLabel = computed(() =>
  alert.value
    ? new Date(alert.value.occurred_at).toLocaleString('zh-CN', {
        year: 'numeric',
        month: 'numeric',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '--',
);

onMounted(() => {
  if (care.alerts.length === 0) {
    care.refresh();
  }
  // 记录“查看告警”（服务端允许的只读请求）。
  if (alert_id.value) {
    care.viewAlert(alert_id.value);
  }
});

async function acknowledge() {
  feedback.value = null;
  const result = await care.acknowledgeAlert(alert_id.value);
  if (result.ok) {
    feedback.value =
      result.data.status === 'VERSION_CONFLICT'
        ? '数据已更新，请刷新后重试。'
        : '确认请求已接收。';
  } else if (result.error.error.reasonCode === 'NETWORK_OFFLINE') {
    feedback.value = care.blockedAction ?? '离线时无法执行此操作，请联网后再试。';
  } else {
    feedback.value = '操作失败，请稍后重试。';
  }
}
</script>

<template>
  <PageShell title="告警详情">
    <StateView v-if="care.loading && !alert" variant="loading" title="正在加载" />
    <StateView
      v-else-if="errorState"
      :variant="errorState.variant"
      :title="errorState.title"
      :description="errorState.description"
    />
    <StateView
      v-else-if="!alert"
      variant="empty"
      title="暂无告警详情"
      description="未找到该告警。"
    />
    <template v-else>
      <dl class="detail">
        <div class="detail__row">
          <dt class="detail__term">告警类型</dt>
          <dd class="detail__desc">{{ ALERT_KIND_LABEL[alert.kind] }}</dd>
        </div>
        <div class="detail__row">
          <dt class="detail__term">安全等级</dt>
          <dd class="detail__desc">{{ alert.safety_level }}</dd>
        </div>
        <div class="detail__row">
          <dt class="detail__term">状态</dt>
          <dd class="detail__desc">{{ ALERT_STATUS_LABEL[alert.status] }}</dd>
        </div>
        <div class="detail__row">
          <dt class="detail__term">发生时间</dt>
          <dd class="detail__desc">{{ timeLabel }}</dd>
        </div>
        <div class="detail__row">
          <dt class="detail__term">来源</dt>
          <dd class="detail__desc">模拟数据（SIMULATOR）</dd>
        </div>
        <div class="detail__row">
          <dt class="detail__term">数据版本</dt>
          <dd class="detail__desc">{{ alert.version }}</dd>
        </div>
      </dl>

      <button
        v-if="alert.status === 'ACTIVE'"
        type="button"
        class="detail__action"
        :disabled="care.submitting"
        @click="acknowledge"
      >
        我已看到提醒
      </button>
      <p v-else class="detail__done">该告警已确认，无需再次处理。</p>
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
  border: 2px solid var(--color-danger);
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
  border: 2px solid var(--color-danger);
  border-radius: var(--radius-md);
  background: var(--color-danger);
  color: var(--color-text-on-dark);
  font-size: var(--font-size-body);
  font-weight: 700;
  cursor: pointer;
}

.detail__action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

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
