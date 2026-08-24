<script setup lang="ts">
import AppIcon from './AppIcon.vue'
const tabs = [{ label: '概览', icon: 'home', to: '/' }, { label: '提醒', icon: 'bell', to: '/tasks' }, { label: '关怀', icon: 'heart', to: '/care' }, { label: '报告', icon: 'chart', to: '/reports' }, { label: '我的', icon: 'user', to: '/settings' }]
</script>
<template><nav aria-label="主导航" class="tabs"><RouterLink v-for="tab in tabs" :key="tab.label" :to="tab.to" active-class="active" :class="{ active: tab.to === '/' && $route.path === '/' }"><AppIcon :name="tab.icon" :size="22"/><span>{{ tab.label }}</span></RouterLink></nav></template>
