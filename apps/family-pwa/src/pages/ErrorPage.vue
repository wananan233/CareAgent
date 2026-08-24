<script setup lang="ts">
defineProps({ code: { type: String, required: true } })
</script>
<template><main class="error-page"><p class="eyebrow">CAREHUB · 家属端</p><h1>暂时无法显示</h1><p>请求未成功：{{ code }}。不会用模拟成功数据替代错误结果。</p><RouterLink to="/">返回安全首页</RouterLink></main></template>
