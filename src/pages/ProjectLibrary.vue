<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  NGrid,
  NGridItem,
  NCard,
  NButton,
  NSpace,
  NTag,
  NPopconfirm,
  NEmpty,
  NButtonGroup,
  NTooltip,
  NEllipsis,
  useMessage,
} from 'naive-ui'
import { useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/project'
import projectsApi from '@/api/projects'
import type { ProjectLibraryItem } from '@/types'
import { languageLabel } from '@/utils/language'

const router = useRouter()
const projectStore = useProjectStore()
const message = useMessage()

const filterStatus = ref<string>('all')

const statusOptions = [
  { label: '全部', value: 'all' },
  { label: '未开始', value: 'not_started' },
  { label: '生成中', value: 'running' },
  { label: '已暂停', value: 'paused' },
  { label: '上次中断', value: 'interrupted' },
  { label: '未完成', value: 'incomplete' },
  { label: '已完成', value: 'completed' },
  { label: '失败', value: 'failed' },
]

// 阶段名 -> 中文标签
const STAGE_LABELS: Record<string, string> = {
  import: '导入素材',
  audio_extract: '提取音频',
  separation: '分离人声/背景',
  asr: '识别字幕',
  diarization: '识别角色',
  translation: '翻译改写',
  tts: '生成配音',
  export: '合成输出',
}

const filteredLibrary = computed<ProjectLibraryItem[]>(() => {
  if (filterStatus.value === 'all') return projectStore.library
  // 使用 lifecycle 字段精确匹配（避免中文 status 与英文 filter 比较的 bug）
  return projectStore.library.filter((item) => item.lifecycle === filterStatus.value)
})

function statusTagType(lifecycle: string): 'default' | 'success' | 'warning' | 'error' | 'info' {
  switch (lifecycle) {
    case 'completed':
      return 'success'
    case 'failed':
      return 'error'
    case 'paused':
    case 'interrupted':
    case 'incomplete':
      return 'warning'
    case 'running':
      return 'info'
    default:
      return 'default'
  }
}

function stageLabel(stage: string | null): string {
  if (!stage) return ''
  return STAGE_LABELS[stage] || stage
}

async function handleDelete(item: ProjectLibraryItem) {
  try {
    await projectsApi.delete(item.path)
    message.success(`已删除项目：${item.name}`)
    await projectStore.refreshLibrary()
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  }
}

function openProject(item: ProjectLibraryItem) {
  projectStore
    .loadProject(item.path)
    .then(() => router.push('/current'))
    .catch((e) => message.error(e instanceof Error ? e.message : String(e)))
}

async function playOutput(path: string): Promise<void> {
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

onMounted(() => {
  projectStore.refreshLibrary().catch((e) => {
    message.error(e instanceof Error ? e.message : String(e))
  })
})
</script>

<template>
  <div class="library-page">
    <div class="library-header">
      <h2 class="page-title">项目库</h2>
      <NSpace>
        <NButtonGroup>
          <NButton
            v-for="opt in statusOptions"
            :key="opt.value"
            :type="filterStatus === opt.value ? 'primary' : 'default'"
            size="small"
            @click="filterStatus = opt.value"
          >
            {{ opt.label }}
          </NButton>
        </NButtonGroup>
        <NButton type="primary" @click="router.push('/create')">创建项目</NButton>
      </NSpace>
    </div>

    <NEmpty v-if="filteredLibrary.length === 0" description="暂无项目" class="library-empty" />

    <NGrid v-else :cols="3" :x-gap="16" :y-gap="16" responsive="screen">
      <NGridItem v-for="item in filteredLibrary" :key="item.path">
        <NCard class="project-card" hoverable @click="openProject(item)">
          <div class="card-header">
            <NEllipsis :line-clamp="1" class="card-name" :tooltip="{ width: 'trigger' }">
              {{ item.name }}
            </NEllipsis>
            <NTag :type="statusTagType(item.lifecycle)" size="small" round>
              {{ item.status }}
            </NTag>
          </div>
          <div class="card-meta">
            <div class="meta-row">
              <span>源语言：{{ languageLabel(item.source_language) }}</span>
              <span class="meta-arrow">→</span>
              <span>目标语言：{{ languageLabel(item.target_language) }}</span>
            </div>
            <div>类型：{{ item.content_type }}</div>
            <!-- 失败阶段单独显示为标签 -->
            <div v-if="item.failed_stage" class="card-failed-stage">
              <span class="failed-stage-label">失败阶段：</span>
              <NTag type="error" size="tiny">{{ stageLabel(item.failed_stage) }}</NTag>
            </div>
            <!-- 状态详情：超长时用 tooltip 显示完整内容，卡片内只显示一行 -->
            <NTooltip
              v-if="item.status_detail"
              trigger="hover"
              placement="bottom"
              :style="{ maxWidth: '400px' }"
            >
              <template #trigger>
                <div class="card-detail">
                  <NEllipsis :line-clamp="1">
                    {{ item.status_detail }}
                  </NEllipsis>
                </div>
              </template>
              <div class="detail-tooltip">{{ item.status_detail }}</div>
            </NTooltip>
          </div>
          <template #action>
            <NSpace justify="end" @click.stop>
              <NButton
                v-if="item.lifecycle === 'completed' && item.final_output_path"
                size="small"
                type="primary"
                ghost
                @click="playOutput(item.final_output_path!)"
              >
                播放
              </NButton>
              <NButton size="small" @click="openProject(item)">打开</NButton>
              <NPopconfirm @positive-click="handleDelete(item)">
                <template #trigger>
                  <NButton size="small" type="error" ghost>删除</NButton>
                </template>
                确认删除项目「{{ item.name }}」？此操作不可恢复。
              </NPopconfirm>
            </NSpace>
          </template>
        </NCard>
      </NGridItem>
    </NGrid>
  </div>
</template>

<style scoped>
.library-page {
  padding: var(--space-6);
}
.library-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-5);
}
.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}
.library-empty {
  padding: var(--space-12) 0;
}
.project-card {
  cursor: pointer;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}
.card-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
  min-width: 0;
}
.card-meta {
  margin-top: var(--space-3);
  font-size: 13px;
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.meta-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.meta-arrow {
  color: var(--text-tertiary);
}
.card-failed-stage {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}
.failed-stage-label {
  color: var(--text-tertiary);
}
.card-detail {
  color: var(--text-tertiary);
}
.detail-tooltip {
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
