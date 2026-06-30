<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  NButton,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NSelect,
  NSpace,
  useMessage,
} from 'naive-ui'
import { useRouter } from 'vue-router'
import projectsApi from '@/api/projects'
import { useModelServicesStore } from '@/stores/modelServices'
import { useProjectStore } from '@/stores/project'
import type { ContentType, SourceLanguage, TargetLanguage } from '@/types'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
  created: [projectPath: string | null]
}>()

const router = useRouter()
const message = useMessage()
const projectStore = useProjectStore()
const modelServicesStore = useModelServicesStore()

const sourceMediaPath = ref('')
const name = ref('')
const sourceLanguage = ref<SourceLanguage>('en')
const targetLanguage = ref<TargetLanguage>('zh')
const contentType = ref<ContentType>('video')
const selectedSchemeId = ref<string | null>(null)
const creating = ref(false)

const sourceLanguageOptions = [
  { label: '英语', value: 'en' },
  { label: '日语', value: 'ja' },
  { label: '韩语', value: 'ko' },
]
const targetLanguageOptions = [{ label: '中文', value: 'zh' }]
const contentTypeOptions = [
  { label: '视频', value: 'video' },
  { label: '音频', value: 'audio' },
]

const schemeOptions = computed(() =>
  modelServicesStore.schemes.map((scheme) => ({
    label:
      scheme.id === modelServicesStore.defaultSchemeId
        ? `${scheme.display_name}（默认）`
        : scheme.display_name,
    value: scheme.id,
  })),
)

function resetForm(): void {
  sourceMediaPath.value = ''
  name.value = ''
  sourceLanguage.value = 'en'
  targetLanguage.value = 'zh'
  contentType.value = 'video'
  selectedSchemeId.value =
    modelServicesStore.defaultSchemeId ?? modelServicesStore.schemes[0]?.id ?? null
}

function updateShow(value: boolean): void {
  if (!creating.value) {
    emit('update:show', value)
  }
}

async function loadSchemes(): Promise<void> {
  try {
    await modelServicesStore.loadSchemes()
    selectedSchemeId.value =
      modelServicesStore.defaultSchemeId ?? modelServicesStore.schemes[0]?.id ?? null
  } catch (e) {
    message.warning(e instanceof Error ? e.message : String(e))
  }
}

async function chooseSourceMedia(): Promise<void> {
  if (!window.ivo) {
    message.warning('当前环境不支持文件选择，请手动输入路径')
    return
  }
  try {
    const filePath = await window.ivo.showOpenDialog()
    if (filePath) {
      sourceMediaPath.value = filePath
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  }
}

async function handleCreate(): Promise<void> {
  if (!sourceMediaPath.value) {
    message.warning('请选择源素材')
    return
  }
  if (!name.value.trim()) {
    message.warning('请输入项目名称')
    return
  }
  creating.value = true
  try {
    const trimmedName = name.value.trim()
    await projectsApi.create({
      source_media_path: sourceMediaPath.value,
      name: trimmedName,
      source_language: sourceLanguage.value,
      target_language: targetLanguage.value,
      content_type: contentType.value,
      scheme_id: selectedSchemeId.value,
    })
    message.success('项目创建成功')
    await projectStore.refreshLibrary()
    const created = projectStore.library.find((p) => p.name === trimmedName) ?? null
    emit('created', created?.path ?? null)
    emit('update:show', false)
    if (created) {
      await projectStore.loadProject(created.path)
      router.push({ path: '/current', query: { path: created.path } })
    } else {
      router.push('/projects')
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  } finally {
    creating.value = false
  }
}

watch(
  () => props.show,
  (show) => {
    if (show) {
      resetForm()
      loadSchemes()
    }
  },
)
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    class="create-project-modal"
    :style="{ width: 'min(760px, calc(100vw - 48px))' }"
    :mask-closable="!creating"
    :bordered="false"
    @update:show="updateShow"
  >
    <template #header>
      <div class="modal-hero">
        <div>
          <div class="modal-eyebrow">新项目</div>
          <div class="modal-title">创建配音项目</div>
          <div class="modal-subtitle">选择源素材和配音方案，创建后会自动进入当前项目。</div>
        </div>
      </div>
    </template>

    <div class="create-dialog-body">
      <NForm class="create-form" label-placement="top" :show-feedback="false">
        <div class="form-section">
          <div class="section-title">素材信息</div>
          <NFormItem label="源素材" required class="span-2">
            <div class="file-picker-row">
              <NInput
                v-model:value="sourceMediaPath"
                placeholder="选择或输入源素材路径"
                class="file-path-input"
              />
              <NButton class="file-button" @click="chooseSourceMedia">选择文件</NButton>
            </div>
          </NFormItem>
          <NFormItem label="项目名称" required class="span-2">
            <NInput v-model:value="name" placeholder="输入项目名称，例如：纪录片第 01 集" />
          </NFormItem>
        </div>

        <div class="form-section form-grid">
          <div class="section-title span-2">配音设置</div>
          <NFormItem label="源语言">
            <NSelect v-model:value="sourceLanguage" :options="sourceLanguageOptions" />
          </NFormItem>
          <NFormItem label="目标语言">
            <NSelect v-model:value="targetLanguage" :options="targetLanguageOptions" />
          </NFormItem>
          <NFormItem label="内容类型">
            <NSelect v-model:value="contentType" :options="contentTypeOptions" />
          </NFormItem>
          <NFormItem label="配音方案">
            <NSelect
              v-model:value="selectedSchemeId"
              :options="schemeOptions"
              :loading="modelServicesStore.loading"
              clearable
              placeholder="未配置方案时将使用项目内默认配置"
            />
          </NFormItem>
        </div>
      </NForm>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <span class="footer-hint">创建后可在时间线继续编辑字幕、角色和语速。</span>
        <NSpace justify="end">
          <NButton :disabled="creating" @click="updateShow(false)">取消</NButton>
          <NButton type="primary" :loading="creating" @click="handleCreate">创建项目</NButton>
        </NSpace>
      </div>
    </template>
  </NModal>
</template>

<style scoped>
:global(.create-project-modal) {
  overflow: hidden;
  border-radius: 18px;
  background:
    radial-gradient(circle at 12% 0%, rgba(94, 234, 212, 0.12), transparent 34%),
    linear-gradient(180deg, #202129 0%, #181a20 100%);
  box-shadow: 0 26px 70px rgba(0, 0, 0, 0.52);
}
:global(.create-project-modal .n-card-header) {
  padding: 0;
}
:global(.create-project-modal .n-card__content) {
  padding: 0 28px 24px;
}
:global(.create-project-modal .n-card__footer) {
  padding: 18px 28px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(12, 13, 17, 0.28);
}
.modal-hero {
  padding: 28px 28px 22px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.modal-eyebrow {
  margin-bottom: 6px;
  color: #5eead4;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
}
.modal-title {
  color: var(--text-primary);
  font-size: 22px;
  font-weight: 700;
  line-height: 1.25;
}
.modal-subtitle {
  margin-top: 8px;
  color: var(--text-tertiary);
  font-size: 13px;
}
.create-dialog-body {
  padding-top: 22px;
}
.create-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.form-section {
  padding: 18px;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.035);
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: 16px;
}
.span-2 {
  grid-column: 1 / -1;
}
.section-title {
  margin-bottom: 14px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 700;
}
.file-picker-row {
  display: flex;
  gap: 10px;
  width: 100%;
}
.file-path-input {
  flex: 1;
  min-width: 0;
}
.file-button {
  flex: 0 0 auto;
}
.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}
.footer-hint {
  color: var(--text-tertiary);
  font-size: 12px;
}
@media (max-width: 720px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  .span-2 {
    grid-column: auto;
  }
  .file-picker-row,
  .dialog-footer {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
