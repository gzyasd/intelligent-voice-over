<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  NCard,
  NButton,
  NSpace,
  NDescriptions,
  NDescriptionsItem,
  NTag,
  NEmpty,
  NProgress,
  NScrollbar,
  useMessage,
} from 'naive-ui'
import { useProjectStore } from '@/stores/project'
import { usePipelineStore } from '@/stores/pipeline'
import { languageLabel } from '@/utils/language'

const projectStore = useProjectStore()
const pipelineStore = usePipelineStore()
const message = useMessage()
const router = useRouter()

const snapshot = computed(() => projectStore.currentSnapshot)
const actionLabel = computed(() => {
  if (!snapshot.value) return ''
  switch (snapshot.value.primary_action) {
    case 'start':
      return '开始生成'
    case 'resume':
      return '继续/重试生成'
    case 'progress':
      return '查看进度'
    case 'open_output':
      return '查看成品'
    default:
      return ''
  }
})
const hasProject = computed(() => !!projectStore.currentProjectPath)
const showPipelinePanel = computed(
  () =>
    hasProject.value &&
    (pipelineStore.isRunning ||
      pipelineStore.finished ||
      pipelineStore.logs.length > 0 ||
      pipelineStore.hasHistory),
)

function ensureProjectPath(): string | null {
  if (!projectStore.currentProjectPath) {
    message.warning('请先打开一个项目')
    return null
  }
  return projectStore.currentProjectPath
}

function goTimeline(): void {
  const path = ensureProjectPath()
  if (!path) return
  router.push({ path: '/timeline', query: { path } })
}

function goExport(): void {
  const path = ensureProjectPath()
  if (!path) return
  router.push({ path: '/export', query: { path } })
}

function stageTagType(status: string): 'default' | 'info' | 'success' | 'error' | 'warning' {
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

function stageStatusText(status: string): string {
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

function formatTime(ts: number): string {
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}

async function copyStatusDetail(): Promise<void> {
  if (!snapshot.value?.status_detail) return
  try {
    await navigator.clipboard.writeText(snapshot.value.status_detail)
    message.success('已复制状态详情')
  } catch {
    message.error('复制失败，请手动选择文本复制')
  }
}

async function startOrAttachPipeline(): Promise<void> {
  const path = ensureProjectPath()
  if (!path || !snapshot.value) return

  pipelineStore.setProject(path)

  try {
    if (snapshot.value.primary_action === 'progress') {
      await pipelineStore.synchronizeWithBackend(path)
      return
    }
    if (snapshot.value.primary_action === 'open_output') {
      goExport()
      return
    }
    await pipelineStore.start()
    await projectStore.refreshCurrent()
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  }
}

async function pausePipeline(): Promise<void> {
  try {
    await pipelineStore.pause()
    await projectStore.refreshCurrent()
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  }
}

async function resumePipeline(): Promise<void> {
  try {
    await pipelineStore.resume()
    await projectStore.refreshCurrent()
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  }
}

async function playOutput(): Promise<void> {
  const path = snapshot.value?.final_output_path
  if (!path) return
  if (!window.ivo?.openPath) {
    message.warning('当前环境不支持播放，请在文件夹中手动打开')
    return
  }
  try {
    const ok = await window.ivo.openPath(path)
    if (!ok) message.error('无法打开文件，请检查路径或权限')
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  }
}

onMounted(async () => {
  if (projectStore.currentProjectPath) {
    try {
      await pipelineStore.synchronizeWithBackend(projectStore.currentProjectPath)
      await projectStore.refreshCurrent()
    } catch (e) {
      message.error(e instanceof Error ? e.message : String(e))
    }
  }
})
</script>

<template>
  <div class="overview-page">
    <NEmpty v-if="!snapshot" description="还没有打开项目，请先从项目库选择或创建项目。" class="overview-empty" />

    <template v-else>
      <div class="overview-header">
        <h2 class="page-title">{{ snapshot.name }}</h2>
        <NSpace>
          <NButton
            v-if="actionLabel"
            type="primary"
            :disabled="pipelineStore.isRunning || pipelineStore.paused"
            @click="startOrAttachPipeline"
          >
            {{ actionLabel }}
          </NButton>
          <NButton v-if="pipelineStore.canPause" type="warning" @click="pausePipeline">暂停</NButton>
          <NButton v-if="pipelineStore.canResume" type="primary" @click="resumePipeline">恢复</NButton>
          <NButton @click="goTimeline">时间线编辑</NButton>
          <NButton @click="goExport">导出</NButton>
        </NSpace>
      </div>

      <div class="overview-grid">
        <!-- 左栏：项目信息 -->
        <NCard title="项目信息" class="info-card" content-class="info-card-content">
          <NDescriptions
            :column="1"
            label-placement="left"
            bordered
            size="small"
            label-class="description-label-style"
            content-class="description-content-style"
          >
            <NDescriptionsItem label="状态">
              <NTag :type="snapshot.lifecycle === 'completed' ? 'success' : 'default'" size="small">
                {{ snapshot.status_label }}
              </NTag>
            </NDescriptionsItem>
            <NDescriptionsItem label="内容类型">{{ snapshot.content_type }}</NDescriptionsItem>
            <NDescriptionsItem label="源语言">{{ languageLabel(snapshot.source_language) }}</NDescriptionsItem>
            <NDescriptionsItem label="目标语言">{{ languageLabel(snapshot.target_language) }}</NDescriptionsItem>
            <NDescriptionsItem label="源文件">
              <span class="file-path">{{ snapshot.source_media_path || '-' }}</span>
            </NDescriptionsItem>
            <NDescriptionsItem label="输出文件">
              <div class="output-file-row">
                <span class="file-path">{{ snapshot.final_output_path || '-' }}</span>
                <NButton
                  v-if="snapshot.lifecycle === 'completed' && snapshot.final_output_path"
                  size="small"
                  type="primary"
                  ghost
                  @click="playOutput"
                >
                  播放
                </NButton>
              </div>
            </NDescriptionsItem>
          </NDescriptions>

          <!-- 状态详情：可滚动 + 复制 -->
          <div class="status-detail-section">
            <div class="status-detail-header">
              <span class="status-detail-title">状态详情</span>
              <NButton
                v-if="snapshot.status_detail"
                size="tiny"
                ghost
                @click="copyStatusDetail"
              >
                复制
              </NButton>
            </div>
            <NScrollbar v-if="snapshot.status_detail" style="max-height: 140px">
              <pre class="status-detail-text">{{ snapshot.status_detail }}</pre>
            </NScrollbar>
            <span v-else class="status-detail-empty">-</span>
          </div>
        </NCard>

        <!-- 右栏：生成进度 -->
        <NCard v-if="showPipelinePanel" class="pipeline-card" title="生成进度" content-class="pipeline-card-content">
          <div class="pipeline-progress-row">
            <span class="pipeline-progress-label">总进度</span>
            <span class="pipeline-progress-value">{{ pipelineStore.overallPercent }}%</span>
          </div>
          <NProgress
            type="line"
            :percentage="pipelineStore.overallPercent"
            :show-indicator="false"
            :status="pipelineStore.error ? 'error' : pipelineStore.finished ? 'success' : 'default'"
          />
          <div class="pipeline-grid">
            <div class="pipeline-stages">
              <div
                v-for="stage in pipelineStore.stages"
                :key="stage.name"
                class="stage-item"
                :class="{ active: stage.name === pipelineStore.currentStage && pipelineStore.isRunning }"
              >
                <div class="stage-row">
                  <span class="stage-label">{{ stage.label }}</span>
                  <NTag :type="stageTagType(stage.status)" size="small">
                    {{ stageStatusText(stage.status) }}
                  </NTag>
                </div>
                <div v-if="stage.message" class="stage-message">{{ stage.message }}</div>
              </div>
            </div>

            <div class="pipeline-logs-panel">
              <div class="pipeline-section-title">运行日志</div>
              <NScrollbar class="pipeline-logs">
                <NEmpty v-if="pipelineStore.logs.length === 0" description="暂无日志" />
                <div v-else class="logs-list">
                  <div v-for="(log, idx) in pipelineStore.logs" :key="idx" class="log-entry">
                    <span class="log-time">{{ formatTime(log.timestamp) }}</span>
                    <span class="log-stage">[{{ log.stageLabel }}]</span>
                    <span class="log-message">{{ log.message }}</span>
                  </div>
                </div>
              </NScrollbar>
            </div>
          </div>
        </NCard>

        <!-- 右栏占位：无生成进度时显示提示 -->
        <NCard v-else class="pipeline-card pipeline-empty-card">
          <NEmpty description="尚未开始生成，点击上方按钮开始" />
        </NCard>
      </div>
    </template>
  </div>
</template>

<style scoped>
.overview-page {
  height: calc(100vh - 28px - 2 * var(--space-6));
  min-height: 0;
  padding: 0;
  box-sizing: border-box;
  overflow: hidden;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: var(--space-4);
}
.overview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-3);
  flex-shrink: 0;
}
.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}
.overview-empty {
  padding: var(--space-12) 0;
}
.overview-grid {
  display: grid;
  grid-template-columns: 360px 1fr;
  grid-template-rows: minmax(0, 1fr);
  gap: var(--space-4);
  align-items: stretch;
  min-height: 0;
  overflow: hidden;
}
@media (max-width: 1024px) {
  .overview-page {
    height: auto;
    overflow: visible;
  }
  .overview-grid {
    grid-template-columns: 1fr;
  }
  .pipeline-card {
    min-height: 520px;
  }
}
.info-card {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
:deep(.info-card-content) {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}
:deep(.description-label-style) {
  width: 72px;
  white-space: nowrap;
}
:deep(.description-content-style) {
  padding-top: 8px !important;
  padding-bottom: 8px !important;
}
.file-path {
  word-break: break-all;
  font-family: var(--font-mono);
  font-size: 12px;
}
.output-file-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.output-file-row .file-path {
  flex: 1;
  min-width: 0;
}
.status-detail-section {
  margin-top: var(--space-4);
}
.status-detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
}
.status-detail-title {
  font-size: 14px;
  font-weight: 600;
}
.status-detail-text {
  margin: 0;
  padding: var(--space-2);
  background: var(--bg-elevated);
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--text-secondary);
  user-select: text;
}
.status-detail-empty {
  color: var(--text-tertiary);
}
.pipeline-card {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
:deep(.pipeline-card-content) {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  height: 100%;
  min-height: 0;
  overflow: hidden;
}
.pipeline-empty-card {
  display: flex;
  align-items: center;
  justify-content: center;
}
.pipeline-progress-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
}
.pipeline-progress-label {
  font-size: 14px;
  color: var(--text-secondary);
}
.pipeline-progress-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--accent);
}
.pipeline-grid {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
  gap: var(--space-4);
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.pipeline-stages {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-self: start;
  min-height: 0;
}
.pipeline-logs-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
}
.pipeline-section-title {
  margin-bottom: var(--space-2);
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}
.stage-item {
  padding: 8px 10px;
  border-radius: var(--radius-md);
  background: var(--bg-elevated);
  border: 1px solid transparent;
}
.stage-item.active {
  border-color: var(--accent);
}
.stage-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
}
.stage-label {
  font-size: 14px;
  font-weight: 500;
}
.stage-message {
  margin-top: 2px;
  font-size: 11px;
  line-height: 1.25;
  color: var(--text-secondary);
}
.pipeline-logs {
  flex: 1;
  min-height: 0;
  overflow: hidden;
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
  color: var(--accent);
  flex-shrink: 0;
  font-weight: 500;
  max-width: 200px;
  overflow-wrap: anywhere;
  word-break: break-all;
}
.log-message {
  flex: 1;
  min-width: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
