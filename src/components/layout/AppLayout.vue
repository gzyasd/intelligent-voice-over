<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  NLayout,
  NLayoutSider,
  NLayoutContent,
  NLayoutFooter,
  NMenu,
  type MenuOption,
} from 'naive-ui'
import healthApi from '@/api/health'

const router = useRouter()
const route = useRoute()

const healthOk = ref<boolean | null>(null)
let healthTimer: ReturnType<typeof setInterval> | null = null

async function checkHealth(): Promise<void> {
  try {
    await healthApi.get()
    healthOk.value = true
  } catch {
    healthOk.value = false
  }
}

interface MenuEntry {
  label: string
  key: string
}

const baseEntries: MenuEntry[] = [
  { label: '首页', key: '/home' },
  { label: '项目库', key: '/projects' },
  { label: '当前项目', key: '/current' },
  { label: '模型服务', key: '/model-services' },
  { label: '方案管理', key: '/schemes' },
  { label: '新建项目', key: '/create' },
  { label: '设置', key: '/settings' },
]

const menuOptions = computed<MenuOption[]>(() =>
  baseEntries.map((entry) => ({
    label: entry.label,
    key: entry.key,
  })),
)

const activeKey = computed(() => route.path)

function handleSelect(key: string): void {
  router.push(key)
}

onMounted(() => {
  checkHealth()
  healthTimer = setInterval(checkHealth, 30000)
})

onUnmounted(() => {
  if (healthTimer) {
    clearInterval(healthTimer)
    healthTimer = null
  }
})
</script>

<template>
  <NLayout has-sider class="app-layout">
    <NLayoutSider bordered class="app-sider" :width="200" :native-scrollbar="false">
      <div class="logo">IVO</div>
      <NMenu :options="menuOptions" :value="activeKey" @update:value="handleSelect" />
    </NLayoutSider>
    <NLayout class="app-main">
      <NLayoutContent class="app-content" :native-scrollbar="false">
        <RouterView />
      </NLayoutContent>
      <NLayoutFooter bordered class="app-footer">
        <span class="footer-status">
          <span
            class="health-dot"
            :class="{
              'health-ok': healthOk === true,
              'health-bad': healthOk === false,
              'health-unknown': healthOk === null,
            }"
          ></span>
          服务状态：{{ healthOk === true ? '正常' : healthOk === false ? '异常' : '检测中' }}
        </span>
      </NLayoutFooter>
    </NLayout>
  </NLayout>
</template>

<style scoped>
.app-layout {
  height: 100vh;
  overflow: hidden;
}
.app-sider {
  height: 100vh;
  overflow: hidden;
}
.app-main {
  height: 100vh;
  overflow: hidden;
}
.logo {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 2px;
  color: var(--accent);
  border-bottom: 1px solid var(--border-color);
}
.app-content {
  height: calc(100vh - 28px);
  overflow-y: auto;
  padding: var(--space-6);
  box-sizing: border-box;
}
.app-footer {
  height: 28px;
  display: flex;
  align-items: center;
  padding: 0 var(--space-4);
  font-size: 12px;
  color: var(--text-secondary);
}
.footer-status {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}
.health-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.health-ok {
  background-color: #18a058;
}
.health-bad {
  background-color: #d03050;
}
.health-unknown {
  background-color: #909399;
}
</style>
