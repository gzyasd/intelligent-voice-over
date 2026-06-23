<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NCard,
  NButton,
  NSpace,
  NProgress,
  NTag,
  NIcon,
  NEmpty,
  NScrollbar,
  useMessage,
} from 'naive-ui'
import { usePipelineStore } from '@/stores/pipeline'
import type { StageState, LogEntry } from '@/stores/pipeline'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const store = usePipelineStore()

const projectPath = computed(() => (route.query.path as string) || '')

onMounted(() => {
  if (projectPath.value) {
    store.synchronizeWithBackend(projectPath.value).catch((e: unknown) => {
      message.error(e instanceof Error ? e.message : String(e))
    })
  }
})

function handleStart(): void {
  if (!projectPath.value) {
    message.warning('缺少项目路径')
    return
  }
  store.start().catch((e: unknown) => {
    message.error(e instanceof Error ? e.message : String(e))
  })
}

function handlePause(): void {
  store.pause().catch((e: unknown) => {
    message.error(e instanceof Error ? e.message : String(e))
  })
}

function handleResume(): void {
  store.resume().catch((e: unknown) => {
    message.error(e instanceof Error ? e.message : String(e))
  })
}

function stageStatusTag(status: StageState['status']): 'default' | 'info' | 'success' | 'error' | 'warning' {
  switch (status) {
    case 'running':
      return 'info'
    case 'completed':
      return 'success'
    case 'failed':
      return 'error'
    case 'skipped':
      return 'warning'
    default:
      return 'default'
  }
}

function stageStatusText(status: StageState['status']): string {
  switch (status) {
    case 'pending':
      return '等待'
    case 'running':
      return '运行中'
    case 'completed':
      return '完成'
    case 'failed':
      return '失败'
    case 'skipped':
      return '跳过'
    default:
      return status
  }
}

function logLevelColor(level: LogEntry['level']): string {
  switch (level) {
    case 'error':
      return 'var(--error)'
    case 'warning':
      return 'var(--warning)'
    case 'progress':
      return 'var(--accent)'
    default:
      return 'var(--text-secondary)'
  }
}

function formatTime(ts: number): string {
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}
</script>

<template>
  <div class="pipeline-page">
    <div class="page-header">
      <h2 class="page-title">流水线运行</h2>
      <NSpace>
        <NButton
          v-if="!store.isRunning && !store.finished"
          type="primary"
          @click="handleStart"
        >
          启动流水线
        </NButton>
        <NButton
          v-if="store.canPause"
          type="warning"
          @click="handlePause"
        >
          暂停
        </NButton>
        <NButton
          v-if="store.canResume"
          type="primary"
          @click="handleResume"
        >
          恢复
        </NButton>
        <NButton @click="router.back()">返回</NButton>
      </NSpace>
    </div>

    <NCard class="progress-card">
      <div class="progress-header">
        <span class="progress-label">总进度</span>
        <span class="progress-percent">{{ store.overallPercent }}%</span>
      </div>
      <NProgress
        type="line"
        :percentage="store.overallPercent"
        :show-indicator="false"
        :status="store.error ? 'error' : store.finished ? 'success' : 'default'"
      />
      <div v-if="store.paused" class="paused-hint">
        <NTag type="warning">已暂停</NTag>
      </div>
      <div v-if="store.error" class="error-hint">
        <NTag type="error">{{ store.error }}</NTag>
      </div>
    </NCard>

    <div class="content-grid">
      <NCard class="stages-card" title="阶段状态">
        <div class="stages-list">
          <div
            v-for="stage in store.stages"
            :key="stage.name"
            class="stage-item"
            :class="{ active: stage.name === store.currentStage && store.isRunning }"
          >
            <div class="stage-info">
              <span class="stage-label">{{ stage.label }}</span>
              <NTag :type="stageStatusTag(stage.status)" size="small">
                {{ stageStatusText(stage.status) }}
              </NTag>
            </div>
            <div v-if="stage.message" class="stage-message">{{ stage.message }}</div>
          </div>
        </div>
      </NCard>

      <NCard class="logs-card" title="运行日志">
        <NScrollbar class="logs-scroll">
          <NEmpty v-if="store.logs.length === 0" description="暂无日志" />
          <div v-else class="logs-list">
            <div
              v-for="(log, idx) in store.logs"
              :key="idx"
              class="log-entry"
            >
              <span class="log-time">{{ formatTime(log.timestamp) }}</span>
              <span class="log-stage" :style="{ color: logLevelColor(log.level) }">
                [{{ log.stageLabel }}]
              </span>
              <span class="log-message" :style="{ color: logLevelColor(log.level) }">
                {{ log.message }}
              </span>
            </div>
          </div>
        </NScrollbar>
      </NCard>
    </div>
  </div>
</template>

<style scoped>
.pipeline-page {
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  height: 100%;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}
.progress-card {
  flex-shrink: 0;
}
.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
}
.progress-label {
  font-size: 14px;
  color: var(--text-secondary);
}
.progress-percent {
  font-size: 18px;
  font-weight: 600;
  color: var(--accent);
}
.paused-hint,
.error-hint {
  margin-top: var(--space-2);
}
.content-grid {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: var(--space-4);
  flex: 1;
  min-height: 0;
}
.stages-card,
.logs-card {
  display: flex;
  flex-direction: column;
  min-height: 0;
}
/* 穿透 NCard 让 .n-card__content 成为 flex 容器并约束高度 */
:deep(.stages-card > .n-card__content),
:deep(.logs-card > .n-card__content) {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
.stages-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  overflow-y: auto;
  min-height: 0;
}
.stage-item {
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background: var(--bg-elevated);
  border: 1px solid transparent;
  transition: border-color 0.2s;
}
.stage-item.active {
  border-color: var(--accent);
}
.stage-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.stage-label {
  font-size: 14px;
  font-weight: 500;
}
.stage-message {
  margin-top: var(--space-1);
  font-size: 12px;
  color: var(--text-secondary);
}
.logs-scroll {
  height: 100%;
  min-height: 0;
}
.logs-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  font-family: var(--font-mono);
  font-size: 12px;
}
.log-entry {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-1) 0;
  border-bottom: 1px solid var(--border-color);
}
.log-time {
  color: var(--text-tertiary);
  flex-shrink: 0;
}
.log-stage {
  flex-shrink: 0;
  font-weight: 500;
  max-width: 200px;
  overflow-wrap: anywhere;
  word-break: break-all;
}
.log-message {
  flex: 1;
  word-break: break-word;
}
</style>
