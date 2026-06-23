<script setup lang="ts">
import { NSpin, NResult } from 'naive-ui'

defineProps<{
  error?: string
}>()
</script>

<template>
  <div class="loading-page">
    <template v-if="error">
      <NResult status="error" title="服务启动失败" :description="error" />
    </template>
    <template v-else>
      <NSpin size="large" />
      <p class="loading-text">正在启动 IVO 服务...</p>
    </template>
  </div>
</template>

<style scoped>
.loading-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: var(--space-6);
}
.loading-text {
  margin: 0;
  color: var(--text-secondary);
  font-size: 15px;
}
</style>
