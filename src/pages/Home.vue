<script setup lang="ts">
import { NH1, NP, NCard, NButton, NSpace } from 'naive-ui'
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="home-page">
    <NCard class="welcome-card">
      <NH1>欢迎使用 IVO 智能视频配音</NH1>
      <NP depth="3">
        将英文 / 日文 / 韩文视频对白重新配成自然的中文音频，支持本地模型流水线与自定义 HTTP API 适配器两种接入模式。
      </NP>
      <NSpace>
        <NButton type="primary" @click="router.push('/create')">新建项目</NButton>
        <NButton @click="router.push('/projects')">打开项目库</NButton>
      </NSpace>
    </NCard>
  </div>
</template>

<style scoped>
.home-page {
  padding: var(--space-8);
}
.welcome-card {
  max-width: 720px;
}
</style>
