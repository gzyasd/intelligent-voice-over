<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import {
  NModal,
  NSteps,
  NStep,
  NSelect,
  NButton,
  NSpace,
  NTag,
  NProgress,
  NLog,
  useMessage,
} from 'naive-ui'
import environmentApi from '@/api/environment'
import type { SetupVenvEvent } from '@/api/environment'
import type { PipMirrorKey } from '@/types'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void
  (e: 'completed'): void
}>()

const message = useMessage()

const mirrorOptions = [
  { label: '官方 PyPI', value: 'official' },
  { label: '清华大学 TUNA', value: 'tsinghua' },
  { label: '阿里云', value: 'aliyun' },
  { label: '中科大 USTC', value: 'ustc' },
]

const selectedMirror = ref<PipMirrorKey>('tsinghua')
const running = ref(false)
const hasError = ref(false)
const completed = ref(false)
const logs = ref<string[]>([])
const currentStep = ref(-1)

const stepLabels = [
  '检查/安装 uv',
  '创建主虚拟环境 .venv',
  '安装主环境依赖',
  '创建 pyannote 环境',
  '安装 pyannote.audio',
]

const stepStatusMap = ref<Record<number, 'wait' | 'process' | 'finish' | 'error'>>({})

const progressPercentage = computed(() => {
  if (completed.value) return 100
  const finished = Object.values(stepStatusMap.value).filter((s) => s === 'finish').length
  return Math.round((finished / stepLabels.length) * 100)
})

let abortController: AbortController | null = null

function appendLog(text: string): void {
  logs.value.push(text)
  if (logs.value.length > 500) {
    logs.value = logs.value.slice(-500)
  }
}

function handleEvent(event: SetupVenvEvent): void {
  const stepIndex = getStepIndex(event.step)
  if (event.status === 'log') {
    appendLog(event.message)
    return
  }

  if (event.message) {
    appendLog(`[${event.step}] ${event.message}`)
  }

  if (event.status === 'running') {
    if (stepIndex >= 0) {
      currentStep.value = stepIndex
      stepStatusMap.value[stepIndex] = 'process'
    }
  } else if (event.status === 'done') {
    if (stepIndex >= 0) {
      stepStatusMap.value[stepIndex] = 'finish'
    }
    if (event.step === 'complete') {
      completed.value = true
      running.value = false
      message.success('环境配置完成！')
      emit('completed')
    }
  } else if (event.status === 'error') {
    if (stepIndex >= 0) {
      stepStatusMap.value[stepIndex] = 'error'
    }
    hasError.value = true
    running.value = false
    message.error(event.message)
  }
}

function getStepIndex(step: string): number {
  const map: Record<string, number> = {
    uv: 0,
    'main-venv': 1,
    'main-deps': 2,
    'pyannote-venv': 3,
    'pyannote-deps': 4,
  }
  return map[step] ?? -1
}

function startSetup(): void {
  running.value = true
  hasError.value = false
  completed.value = false
  logs.value = []
  currentStep.value = 0
  stepStatusMap.value = {}

  appendLog(`开始环境配置（镜像源: ${selectedMirror.value}）`)
  appendLog('')

  abortController = environmentApi.setupVenv(
    selectedMirror.value,
    handleEvent,
  )
}

function cancelSetup(): void {
  abortController?.abort()
  running.value = false
  appendLog('\n[已取消]')
}

function handleClose(): void {
  if (running.value) {
    cancelSetup()
  }
  emit('update:show', false)
}

watch(
  () => props.show,
  (val) => {
    if (!val) {
      if (running.value) {
        cancelSetup()
      }
    } else {
      // 重置状态
      running.value = false
      hasError.value = false
      completed.value = false
      logs.value = []
      currentStep.value = -1
      stepStatusMap.value = {}
    }
  },
)
</script>

<template>
  <NModal
    :show="show"
    @update:show="handleClose"
    preset="card"
    title="环境配置向导"
    style="width: 720px"
    :mask-closable="!running"
    :closable="!running"
  >
    <div class="setup-content">
      <!-- 下载源选择 -->
      <div class="mirror-section">
        <div class="section-label">PyPI 下载源</div>
        <NSpace align="center">
          <NSelect
            v-model:value="selectedMirror"
            :options="mirrorOptions"
            :disabled="running"
            style="width: 240px"
          />
          <span class="mirror-hint">国内网络建议选择清华或阿里云</span>
        </NSpace>
      </div>

      <!-- 步骤进度 -->
      <div class="steps-section">
        <NSteps :current="currentStep + 1" size="small">
          <NStep
            v-for="(label, i) in stepLabels"
            :key="i"
            :title="label"
            :status="stepStatusMap[i] || 'wait'"
          />
        </NSteps>
      </div>

      <!-- 进度条 -->
      <div class="progress-section">
        <NProgress
          :percentage="progressPercentage"
          :status="hasError ? 'error' : completed ? 'success' : 'default'"
          :show-indicator="true"
        />
      </div>

      <!-- 日志区域 -->
      <div class="log-section">
        <div class="log-header">
          <span class="section-label">安装日志</span>
          <NTag v-if="running" size="small" type="info">进行中</NTag>
          <NTag v-else-if="hasError" size="small" type="error">失败</NTag>
          <NTag v-else-if="completed" size="small" type="success">完成</NTag>
        </div>
        <div class="log-container">
          <NLog
            :log="logs.join('\n')"
            trim
            :rows="18"
            :font-size="12"
            class="log-view"
          />
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="actions">
        <NSpace justify="end">
          <NButton v-if="running" type="warning" @click="cancelSetup">
            取消安装
          </NButton>
          <NButton
            v-else-if="hasError"
            type="primary"
            @click="startSetup"
          >
            重新安装
          </NButton>
          <NButton
            v-else-if="completed"
            type="primary"
            @click="handleClose"
          >
            完成
          </NButton>
          <NButton
            v-else
            type="primary"
            @click="startSetup"
          >
            开始安装
          </NButton>
          <NButton v-if="!running && !completed" @click="handleClose">
            关闭
          </NButton>
        </NSpace>
      </div>
    </div>
  </NModal>
</template>

<style scoped>
.setup-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.mirror-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.section-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}
.mirror-hint {
  font-size: 12px;
  color: var(--text-tertiary);
}
.steps-section {
  padding: 8px 0;
}
.progress-section {
  padding: 0 4px;
}
.log-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.log-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.log-container {
  border-radius: 6px;
  overflow: hidden;
}
:deep(.log-view) {
  max-height: 320px;
}
.actions {
  padding-top: 4px;
}
</style>
