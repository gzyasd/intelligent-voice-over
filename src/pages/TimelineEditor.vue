<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed, h, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NCard,
  NButton,
  NSpace,
  NDataTable,
  NTag,
  NModal,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NPopconfirm,
  NSwitch,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import segmentsApi from '@/api/segments'
import { getApiBaseUrl } from '@/api/client'
import type { DubbingSegment } from '@/types'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const projectPath = computed(() => (route.query.path as string) || '')
const segments = ref<DubbingSegment[]>([])
const loading = ref(false)
const checkedRowKeys = ref<string[]>([])
const DEFAULT_REGEN_SPEECH_RATE = 0.9

// 编辑弹窗
const editModalVisible = ref(false)
const editingSegment = ref<DubbingSegment | null>(null)
const editForm = ref({
  target_text: '',
  speaker_id: '',
  emotion: '',
  style_prompt: '',
})

// 重合成弹窗
const regenModalVisible = ref(false)
const regenSegment = ref<DubbingSegment | null>(null)
const regenForm = ref({
  target_text: '',
  speaker_id: '',
  emotion: '',
  style_prompt: '',
  speech_rate: DEFAULT_REGEN_SPEECH_RATE,
})
const regenerating = ref(false)

// 音频播放
const audioPlayer = ref<HTMLAudioElement | null>(null)
const playingSegmentId = ref<string | null>(null)

onMounted(() => {
  if (projectPath.value) {
    loadSegments()
  }
})

async function loadSegments(): Promise<void> {
  loading.value = true
  try {
    segments.value = await segmentsApi.list(projectPath.value)
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  } finally {
    loading.value = false
  }
}

function formatTime(ms: number): string {
  const totalSec = Math.floor(ms / 1000)
  const min = Math.floor(totalSec / 60)
  const sec = totalSec % 60
  return `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

function statusTagType(status: DubbingSegment['status']): 'default' | 'info' | 'success' | 'warning' | 'error' {
  switch (status) {
    case 'rendered':
      return 'success'
    case 'approved':
      return 'info'
    case 'needs_review':
      return 'warning'
    case 'failed':
      return 'error'
    default:
      return 'default'
  }
}

function statusText(status: DubbingSegment['status']): string {
  const map: Record<string, string> = {
    pending: '待处理',
    running: '运行中',
    needs_review: '待审核',
    approved: '已批准',
    failed: '失败',
    rendered: '已合成',
  }
  return map[status] || status
}

function getSegmentAudioUrl(segment: DubbingSegment): string | null {
  if (segment.status !== 'rendered') return null
  const baseUrl = getApiBaseUrl()
  // 假设音频在 work/generated_segments/{id}.wav
  const audioPath = `${projectPath.value}/work/generated_segments/${segment.id}.wav`
  return `${baseUrl}/files/preview?path=${encodeURIComponent(audioPath)}`
}

function playAudio(segment: DubbingSegment): void {
  const url = getSegmentAudioUrl(segment)
  if (!url) {
    message.warning('该片段尚未合成音频')
    return
  }
  if (audioPlayer.value) {
    audioPlayer.value.pause()
  }
  audioPlayer.value = new Audio(url)
  audioPlayer.value.onended = () => {
    playingSegmentId.value = null
  }
  audioPlayer.value.onerror = () => {
    message.error('音频播放失败，可能文件不存在或格式不支持')
    playingSegmentId.value = null
  }
  audioPlayer.value.play().catch((err: Error) => {
    message.error(`音频播放失败: ${err instanceof Error ? err.message : String(err)}`)
    playingSegmentId.value = null
  })
  playingSegmentId.value = segment.id
}

function stopAudio(): void {
  if (audioPlayer.value) {
    audioPlayer.value.pause()
    audioPlayer.value = null
  }
  playingSegmentId.value = null
}

function openEditModal(segment: DubbingSegment): void {
  editingSegment.value = segment
  editForm.value = {
    target_text: segment.target_text,
    speaker_id: segment.speaker_id,
    emotion: segment.emotion || '',
    style_prompt: segment.style_prompt || '',
  }
  editModalVisible.value = true
}

async function saveEdit(): Promise<void> {
  if (!editingSegment.value) return
  try {
    const updated = await segmentsApi.update(
      projectPath.value,
      editingSegment.value.id,
      {
        target_text: editForm.value.target_text,
        speaker_id: editForm.value.speaker_id,
        emotion: editForm.value.emotion || null,
        style_prompt: editForm.value.style_prompt || null,
      },
    )
    const idx = segments.value.findIndex((s) => s.id === updated.id)
    if (idx >= 0) segments.value[idx] = updated
    editModalVisible.value = false
    message.success('已保存')
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  }
}

function openRegenModal(segment: DubbingSegment): void {
  regenSegment.value = segment
  regenForm.value = {
    target_text: segment.target_text,
    speaker_id: segment.speaker_id,
    emotion: segment.emotion || '',
    style_prompt: segment.style_prompt || '',
    speech_rate: DEFAULT_REGEN_SPEECH_RATE,
  }
  regenModalVisible.value = true
}

async function doRegenerate(): Promise<void> {
  if (!regenSegment.value) return
  regenerating.value = true
  try {
    const result = await segmentsApi.regenerate(
      projectPath.value,
      regenSegment.value.id,
      {
        target_text: regenForm.value.target_text,
        speaker_id: regenForm.value.speaker_id,
        emotion: regenForm.value.emotion || undefined,
        style_prompt: regenForm.value.style_prompt || undefined,
        speech_rate: regenForm.value.speech_rate,
      },
    )
    const idx = segments.value.findIndex((s) => s.id === result.segment.id)
    if (idx >= 0) segments.value[idx] = result.segment
    regenModalVisible.value = false
    message.success('重合成完成')
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  } finally {
    regenerating.value = false
  }
}

async function approveSelected(): Promise<void> {
  if (checkedRowKeys.value.length === 0) {
    message.warning('请先选择片段')
    return
  }
  try {
    await segmentsApi.batchUpdateStatus(projectPath.value, {
      segment_ids: checkedRowKeys.value,
      status: 'approved',
    })
    message.success(`已批准 ${checkedRowKeys.value.length} 个片段`)
    checkedRowKeys.value = []
    await loadSegments()
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  }
}

const columns: DataTableColumns<DubbingSegment> = [
  { type: 'selection' },
  {
    title: '#',
    key: 'index',
    width: 50,
    render: (_row, index) => index + 1,
  },
  {
    title: '时间',
    key: 'time',
    width: 120,
    render: (row) => `${formatTime(row.start_ms)} - ${formatTime(row.end_ms)}`,
  },
  {
    title: '说话人',
    key: 'speaker_id',
    width: 80,
  },
  {
    title: '原文',
    key: 'source_text',
    ellipsis: { tooltip: true },
  },
  {
    title: '译文',
    key: 'target_text',
    ellipsis: { tooltip: true },
  },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: (row) =>
      h(NTag, { type: statusTagType(row.status), size: 'small' }, () => statusText(row.status)),
  },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    render: (row) =>
      h(NSpace, { size: 'small' }, () => [
        h(
          NButton,
          {
            size: 'small',
            disabled: row.status !== 'rendered',
            type: playingSegmentId.value === row.id ? 'warning' : 'default',
            onClick: () =>
              playingSegmentId.value === row.id ? stopAudio() : playAudio(row),
          },
          () => (playingSegmentId.value === row.id ? '停止' : '播放'),
        ),
        h(
          NButton,
          { size: 'small', onClick: () => openEditModal(row) },
          () => '编辑',
        ),
        h(
          NButton,
          {
            size: 'small',
            type: 'primary',
            loading: regenerating.value && regenSegment.value?.id === row.id,
            onClick: () => openRegenModal(row),
          },
          () => '重合成',
        ),
      ]),
  },
]

const rowKey = (row: DubbingSegment): string => row.id

const cardRef = ref<InstanceType<typeof NCard> | null>(null)
const tableMaxHeight = ref(600)
let resizeObserver: ResizeObserver | null = null

function updateTableHeight(): void {
  const contentEl = cardRef.value?.$el?.querySelector('.n-card__content')
  if (!contentEl) return
  const height = contentEl.getBoundingClientRect().height
  // 预留 NDataTable 分页器高度（约 48px）
  tableMaxHeight.value = Math.max(200, Math.floor(height - 48))
}

onMounted(() => {
  if (projectPath.value) {
    loadSegments()
  }
  nextTick(() => {
    updateTableHeight()
    const contentEl = cardRef.value?.$el?.querySelector('.n-card__content')
    if (contentEl && typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(() => updateTableHeight())
      resizeObserver.observe(contentEl)
    }
    window.addEventListener('resize', updateTableHeight)
  })
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  window.removeEventListener('resize', updateTableHeight)
})
</script>

<template>
  <div class="timeline-page">
    <div class="page-header">
      <h2 class="page-title">时间线编辑器</h2>
      <NSpace>
        <NButton @click="loadSegments" :loading="loading">刷新</NButton>
        <NPopconfirm @positive-click="approveSelected">
          <template #trigger>
            <NButton type="primary" :disabled="checkedRowKeys.length === 0">
              批量批准 ({{ checkedRowKeys.length }})
            </NButton>
          </template>
          确认批准选中的 {{ checkedRowKeys.length }} 个片段？
        </NPopconfirm>
        <NButton @click="router.back()">返回</NButton>
      </NSpace>
    </div>

    <NCard ref="cardRef" class="timeline-card" content-class="timeline-card-content">
      <NDataTable
        :columns="columns"
        :data="segments"
        :loading="loading"
        :row-key="rowKey"
        v-model:checked-row-keys="checkedRowKeys"
        :pagination="{ pageSize: 50 }"
        :max-height="tableMaxHeight"
        :scroll-x="900"
      />
    </NCard>

    <!-- 编辑弹窗 -->
    <NModal
      v-model:show="editModalVisible"
      preset="card"
      title="编辑片段"
      style="width: 600px"
    >
      <NForm label-placement="top" v-if="editingSegment">
        <NFormItem label="说话人">
          <NInput v-model:value="editForm.speaker_id" />
        </NFormItem>
        <NFormItem label="原文（只读）">
          <NInput
            :value="editingSegment.source_text"
            type="textarea"
            readonly
            :rows="2"
          />
        </NFormItem>
        <NFormItem label="译文">
          <NInput
            v-model:value="editForm.target_text"
            type="textarea"
            :rows="3"
          />
        </NFormItem>
        <NFormItem label="情绪">
          <NInput v-model:value="editForm.emotion" placeholder="如：平静、激动、悲伤" />
        </NFormItem>
        <NFormItem label="风格提示">
          <NInput
            v-model:value="editForm.style_prompt"
            type="textarea"
            :rows="2"
            placeholder="TTS 风格提示词"
          />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="editModalVisible = false">取消</NButton>
          <NButton type="primary" @click="saveEdit">保存</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- 重合成弹窗 -->
    <NModal
      v-model:show="regenModalVisible"
      preset="card"
      title="重新合成片段"
      style="width: 600px"
    >
      <NForm label-placement="top" v-if="regenSegment">
        <NFormItem label="说话人">
          <NInput v-model:value="regenForm.speaker_id" />
        </NFormItem>
        <NFormItem label="译文">
          <NInput
            v-model:value="regenForm.target_text"
            type="textarea"
            :rows="3"
          />
        </NFormItem>
        <NFormItem label="情绪">
          <NInput v-model:value="regenForm.emotion" placeholder="如：平静、激动、悲伤" />
        </NFormItem>
        <NFormItem label="风格提示">
          <NInput
            v-model:value="regenForm.style_prompt"
            type="textarea"
            :rows="2"
          />
        </NFormItem>
        <NFormItem label="语速">
          <NInputNumber
            v-model:value="regenForm.speech_rate"
            :min="0.6"
            :max="1.4"
            :step="0.05"
            :precision="2"
          />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="regenModalVisible = false">取消</NButton>
          <NButton
            type="primary"
            :loading="regenerating"
            @click="doRegenerate"
          >
            开始重合成
          </NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>

<style scoped>
.timeline-page {
  height: 100%;
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  box-sizing: border-box;
  overflow: hidden;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}
.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}
.timeline-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
:deep(.timeline-card > .n-card__content) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
