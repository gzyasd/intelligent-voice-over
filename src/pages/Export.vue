<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NCard,
  NButton,
  NSpace,
  NRadioGroup,
  NRadio,
  NInput,
  NCheckbox,
  NAlert,
  NTag,
  NSpin,
  useMessage,
} from 'naive-ui'
import exportApi from '@/api/export'
import { getApiBaseUrl } from '@/api/client'
import type { ExportResult } from '@/api/export'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const projectPath = computed(() => (route.query.path as string) || '')

const exportType = ref<'video' | 'audio'>('video')
const audioFormat = ref<'wav' | 'mp3'>('wav')
const watermarkText = ref('AI Dubbed')
const enableWatermark = ref(true)
const accepted = ref(false)
const exporting = ref(false)
const exportResult = ref<ExportResult | null>(null)

const canExport = computed(() => accepted.value && !exporting.value)
const hasElectronBridge = computed(() => typeof window !== 'undefined' && !!window.ivo)

async function handleExport(): Promise<void> {
  if (!projectPath.value) {
    message.warning('缺少项目路径')
    return
  }
  if (!accepted.value) {
    message.warning('请先确认 AI 配音合规声明')
    return
  }

  exporting.value = true
  exportResult.value = null
  try {
    if (exportType.value === 'video') {
      exportResult.value = await exportApi.exportVideo({
        project_path: projectPath.value,
        watermark_text: enableWatermark.value ? watermarkText.value : null,
        accepted: true,
      })
    } else {
      exportResult.value = await exportApi.exportAudio({
        project_path: projectPath.value,
        format: audioFormat.value,
        accepted: true,
      })
    }
    message.success('导出完成')
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  } finally {
    exporting.value = false
  }
}

function getOutputPreviewUrl(): string | null {
  if (!exportResult.value) return null
  const baseUrl = getApiBaseUrl()
  return `${baseUrl}/files/preview?path=${encodeURIComponent(exportResult.value.output_path)}`
}

function openInFolder(): void {
  if (!exportResult.value || !window.ivo) return
  window.ivo.openInFolder(exportResult.value.output_path)
}
</script>

<template>
  <div class="export-page">
    <div class="page-header">
      <h2 class="page-title">导出配音</h2>
      <NButton @click="router.back()">返回</NButton>
    </div>

    <NCard class="export-card">
      <div class="section">
        <h3 class="section-title">导出类型</h3>
        <NRadioGroup v-model:value="exportType">
          <NSpace>
            <NRadio value="video">视频（MP4，含画面 + 水印）</NRadio>
            <NRadio value="audio">音频（WAV/MP3，纯音频）</NRadio>
          </NSpace>
        </NRadioGroup>
      </div>

      <div v-if="exportType === 'audio'" class="section">
        <h3 class="section-title">音频格式</h3>
        <NRadioGroup v-model:value="audioFormat">
          <NSpace>
            <NRadio value="wav">WAV（无损）</NRadio>
            <NRadio value="mp3">MP3（压缩，192kbps）</NRadio>
          </NSpace>
        </NRadioGroup>
      </div>

      <div v-if="exportType === 'video'" class="section">
        <h3 class="section-title">水印设置</h3>
        <NSpace vertical>
          <NCheckbox v-model:checked="enableWatermark">
            启用 AI 配音水印（右上角半透明标注）
          </NCheckbox>
          <NInput
            v-if="enableWatermark"
            v-model:value="watermarkText"
            placeholder="水印文本"
            style="max-width: 300px"
          />
        </NSpace>
      </div>

      <div class="section">
        <NAlert type="warning" title="AI 配音合规声明" class="compliance-alert">
          <NSpace vertical>
            <span>导出的内容将包含 AI 生成配音，请确认：</span>
            <ul class="compliance-list">
              <li>您有权对源素材进行配音处理</li>
              <li>导出内容将标注 AI 配音元数据</li>
              <li v-if="exportType === 'video'">视频右上角将显示 AI 水印</li>
              <li>您将遵守相关法律法规和平台政策</li>
            </ul>
            <NCheckbox v-model:checked="accepted">
              我已阅读并同意上述声明
            </NCheckbox>
          </NSpace>
        </NAlert>
      </div>

      <div class="section actions">
        <NButton
          type="primary"
          size="large"
          :disabled="!canExport"
          :loading="exporting"
          @click="handleExport"
        >
          {{ exporting ? '正在导出...' : '开始导出' }}
        </NButton>
      </div>

      <div v-if="exporting" class="section">
        <NSpin size="small" />
        <span class="exporting-hint">正在使用 FFmpeg 混合音频和视频，请稍候...</span>
      </div>

      <div v-if="exportResult" class="section result-section">
        <NAlert type="success" title="导出完成">
          <NSpace vertical>
            <span>已导出 {{ exportResult.segment_count }} 个片段</span>
            <div class="result-path">
              <NTag size="small">输出路径</NTag>
              <span class="path-text">{{ exportResult.output_path }}</span>
            </div>
            <NSpace>
              <NButton
                v-if="hasElectronBridge"
                size="small"
                @click="openInFolder"
              >
                在文件夹中显示
              </NButton>
              <NButton
                size="small"
                tag="a"
                :href="getOutputPreviewUrl() || undefined"
                target="_blank"
              >
                预览文件
              </NButton>
            </NSpace>
          </NSpace>
        </NAlert>
      </div>
    </NCard>
  </div>
</template>

<style scoped>
.export-page {
  padding: var(--space-6);
  max-width: 720px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
}
.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}
.export-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
.section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.section-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}
.compliance-alert {
  max-width: 100%;
}
.compliance-list {
  margin: var(--space-1) 0;
  padding-left: var(--space-5);
  font-size: 13px;
  color: var(--text-secondary);
}
.compliance-list li {
  margin: var(--space-1) 0;
}
.actions {
  align-items: flex-start;
}
.exporting-hint {
  margin-left: var(--space-2);
  color: var(--text-secondary);
  font-size: 13px;
}
.result-section {
  margin-top: var(--space-2);
}
.result-path {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.path-text {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-secondary);
  word-break: break-all;
}
</style>
