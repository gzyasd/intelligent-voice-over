<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  NConfigProvider,
  NMessageProvider,
  NDialogProvider,
  darkTheme,
  zhCN,
  dateZhCN,
} from 'naive-ui'
import { useSettingsStore } from '@/stores/settings'
import AppLayout from '@/components/layout/AppLayout.vue'
import LoadingPage from '@/pages/Loading.vue'

const settingsStore = useSettingsStore()
const ready = ref(false)
const error = ref('')
const crashed = ref(false)

const theme = computed(() => (settingsStore.isDark ? darkTheme : null))

// 同步主题到根元素 data-theme，驱动 CSS 变量切换
watch(
  () => settingsStore.isDark,
  (dark) => {
    document.documentElement.dataset.theme = dark ? 'dark' : 'light'
  },
  { immediate: true },
)

let unsubscribeReady: (() => void) | null = null
let unsubscribeCrashed: (() => void) | null = null

function markReady(apiBaseUrl: string): void {
  if (ready.value) {
    return
  }
  settingsStore.setApiBaseUrl(apiBaseUrl)
  settingsStore
    .load()
    .catch((e: unknown) => {
      error.value = e instanceof Error ? e.message : String(e)
    })
    .finally(() => {
      ready.value = true
    })
}

onMounted(() => {
  if (window.ivo?.onPythonServiceReady) {
    unsubscribeReady = window.ivo.onPythonServiceReady((apiBaseUrl: string) => {
      markReady(apiBaseUrl)
    })

    // 监听 Python 服务崩溃
    if (window.ivo.onPythonServiceCrashed) {
      unsubscribeCrashed = window.ivo.onPythonServiceCrashed(() => {
        crashed.value = true
      })
    }
    if (window.ivo.getPythonServiceCurrent) {
      window.ivo
        .getPythonServiceCurrent()
        .then((current) => {
          if (current?.baseUrl) {
            markReady(current.baseUrl)
          }
        })
        .catch((e: unknown) => {
          error.value = e instanceof Error ? e.message : String(e)
        })
    }
  } else {
    // 非 Electron 环境（纯浏览器开发），直接进入应用
    ready.value = true
  }
})

onUnmounted(() => {
  unsubscribeReady?.()
  unsubscribeCrashed?.()
})
</script>

<template>
  <NConfigProvider :theme="theme" :locale="zhCN" :date-locale="dateZhCN">
    <NMessageProvider>
      <NDialogProvider>
        <LoadingPage v-if="!ready" :error="error" />
        <AppLayout v-else-if="!crashed" />
        <div v-else class="crash-screen">
          <div class="crash-content">
            <h2>后端服务已停止</h2>
            <p>IVO 的 Python 后端服务意外退出，应用无法继续工作。</p>
            <p>请重启应用。如果问题持续出现，请检查安装完整性或联系支持。</p>
          </div>
        </div>
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>

<style scoped>
.crash-screen {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-base, #1a1a1e);
  color: var(--text-primary, #e5e5e5);
}
.crash-content {
  text-align: center;
  max-width: 480px;
  padding: var(--space-8, 32px);
}
.crash-content h2 {
  margin: 0 0 var(--space-4, 16px) 0;
  color: var(--error, #ef4444);
}
.crash-content p {
  margin: var(--space-2, 8px) 0;
  line-height: 1.6;
}
</style>
