<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  NCard,
  NForm,
  NFormItem,
  NInput,
  NSelect,
  NButton,
  NSpace,
  useMessage,
} from 'naive-ui'
import { useRouter } from 'vue-router'
import projectsApi from '@/api/projects'
import { useModelServicesStore } from '@/stores/modelServices'
import { useProjectStore } from '@/stores/project'
import type { ContentType, SourceLanguage, TargetLanguage } from '@/types'

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

async function loadSchemes() {
  try {
    await modelServicesStore.loadSchemes()
    selectedSchemeId.value =
      modelServicesStore.defaultSchemeId ?? modelServicesStore.schemes[0]?.id ?? null
  } catch (e) {
    message.warning(e instanceof Error ? e.message : String(e))
  }
}

async function chooseSourceMedia() {
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

async function handleCreate() {
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
    const created = projectStore.library.find((p) => p.name === trimmedName)
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

onMounted(() => {
  loadSchemes()
})
</script>

<template>
  <div class="create-page">
    <h2 class="page-title">创建项目</h2>
    <NCard class="create-card">
      <NForm label-placement="left" :label-width="100">
        <NFormItem label="源素材" required>
          <NSpace align="center" style="width: 100%">
            <NInput
              v-model:value="sourceMediaPath"
              placeholder="选择或输入源素材路径"
              style="flex: 1"
            />
            <NButton @click="chooseSourceMedia">选择文件</NButton>
          </NSpace>
        </NFormItem>
        <NFormItem label="项目名称" required>
          <NInput v-model:value="name" placeholder="输入项目名称" />
        </NFormItem>
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
        <NFormItem :label-width="0">
          <NSpace>
            <NButton type="primary" :loading="creating" @click="handleCreate">创建</NButton>
            <NButton @click="router.back()">取消</NButton>
          </NSpace>
        </NFormItem>
      </NForm>
    </NCard>
  </div>
</template>

<style scoped>
.create-page {
  padding: var(--space-6);
}
.page-title {
  margin: 0 0 var(--space-5);
  font-size: 20px;
  font-weight: 600;
}
.create-card {
  max-width: 640px;
}
</style>
