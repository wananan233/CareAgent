<script setup lang="ts">
import { computed, onMounted } from 'vue';
import PageShell from '@/components/PageShell.vue';
import StateView from '@/components/StateView.vue';
import AlertCard from '@/components/AlertCard.vue';
import { useCareStore } from '@/stores/care';
import { loadStateFor } from '@/contracts/displayMapping';

const care = useCareStore();
const errorState = computed(() => (care.loadError ? loadStateFor(care.loadError) : null));

onMounted(() => {
  if (care.alerts.length === 0) {
    care.loadAlerts();
  }
});
</script>

<template>
  <PageShell title="安全提示">
    <StateView
      v-if="care.loading && care.alerts.length === 0"
      variant="loading"
      title="正在加载"
    />
    <StateView
      v-else-if="errorState"
      :variant="errorState.variant"
      :title="errorState.title"
      :description="errorState.description"
    />
    <StateView
      v-else-if="care.alerts.length === 0"
      variant="empty"
      title="暂无安全告警"
      description="当前没有需要处理的安全事件。"
    />
    <ul v-else class="safety__list">
      <li v-for="a in care.alerts" :key="a.alert_id">
        <AlertCard :alert="a" @acknowledge="care.acknowledgeAlert(a.alert_id)" />
      </li>
    </ul>
    <section v-if="care.alerts.length" class="safety__agent">
      <strong>✦ CareAgent 可以帮您解释这条信息</strong>
      <p>这是一个需要立即关注的安全提醒。CareAgent 只负责说明信息，不能解除、降低或处理安全事件。</p>
      <RouterLink to="/agent">听听简单说明</RouterLink>
    </section>
  </PageShell>
</template>

<style scoped>
.safety__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}
.safety__agent{display:flex;flex-direction:column;gap:var(--space-sm);padding:var(--space-md);border-radius:var(--radius-lg);background:#eef4f1}.safety__agent p{margin:0}.safety__agent a{color:var(--color-brand);font-weight:700}
</style>
