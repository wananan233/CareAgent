<script setup lang="ts">
import { onUnmounted, ref } from 'vue'
import BottomTabs from '@/components/BottomTabs.vue'
import { useRoute, useRouter } from 'vue-router'
const route = useRoute()
const router = useRouter()
const transitionName = ref('tab-switch')
const removeHook = router.afterEach((to, from) => {
  const toDepth = Number(to.meta.depth ?? 0)
  const fromDepth = Number(from.meta.depth ?? 0)
  if (toDepth > fromDepth) transitionName.value = 'nav-forward'
  else if (toDepth < fromDepth) transitionName.value = 'nav-back'
  else transitionName.value = 'tab-switch'
})
onUnmounted(removeHook)
</script>
<template>
  <div class="app-stage">
    <RouterView v-slot="{ Component, route: viewRoute }"><Transition :name="transitionName"><component :is="Component" :key="viewRoute.fullPath" /></Transition></RouterView>
  </div>
  <BottomTabs v-if="route.meta.primary" />
</template>
