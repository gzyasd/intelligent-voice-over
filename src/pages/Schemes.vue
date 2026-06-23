<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import {
  NLayout,
  NLayoutSider,
  NLayoutContent,
  NButton,
  NSpace,
  NList,
  NListItem,
  NThing,
  NTag,
  NInput,
  NSwitch,
  NSelect,
  NDataTable,
  NForm,
  NFormItem,
  NEmpty,
  useMessage,
  useDialog,
  type DataTableColumns,
} from 'naive-ui'
import { useModelServicesStore } from '@/stores/modelServices'
import type {
  DubbingScheme,
  SchemeStageBinding,
  StageName,
  CreateSchemeRequest,
  UpdateSchemeRequest,
} from '@/types'

const store = useModelServicesStore()
const message = useMessage()
const dialog = useDialog()

const STAGES: StageName[] = ['separation', 'asr', 'diarization', 'translation', 'tts']
const STAGE_LABELS: Record<StageName, string> = {
  separation: '人声分离',
  asr: '语音识别',
  diarization: '说话人分离',
  translation: '翻译',
  tts: '语音合成',
}

interface EditableBinding {
  stage: StageName
  stage_config_id: string | null
  execution_group: string
  skip: boolean
}

const selectedSchemeId = ref<string | null>(null)
const saving = ref(false)
const editForm = reactive({
  display_name: '',
  description: '',
  prefer_gpu: false,
  content_types_text: '',
  bindings: [] as EditableBinding[],
})

function blankBindings(): EditableBinding[] {
  return STAGES.map((stage) => ({
    stage,
    stage_config_id: null,
    execution_group: '',
    skip: false,
  }))
}

function resetForm(): void {
  editForm.display_name = ''
  editForm.description = ''
  editForm.prefer_gpu = false
  editForm.content_types_text = ''
  editForm.bindings = blankBindings()
}

function selectScheme(scheme: DubbingScheme): void {
  selectedSchemeId.value = scheme.id
  editForm.display_name = scheme.display_name
  editForm.description = scheme.description
  editForm.prefer_gpu = scheme.prefer_gpu
  editForm.content_types_text = scheme.content_types.join(', ')
  editForm.bindings = STAGES.map((stage) => {
    const existing = scheme.bindings.find((b) => b.stage === stage)
    return {
      stage,
      stage_config_id: existing?.stage_config_id ?? null,
      execution_group: existing?.execution_group ?? '',
      skip: existing?.skip_when_execution_group_has_output ?? false,
    }
  })
}

function handleCreate(): void {
  selectedSchemeId.value = null
  resetForm()
}

function stageConfigOptionsFor(
  stage: StageName,
): { label: string; value: string }[] {
  return store.stageConfigs
    .filter((c) => c.stage === stage)
    .map((c) => ({ label: c.display_name, value: c.id }))
}

function updateBinding(index: number, patch: Partial<EditableBinding>): void {
  editForm.bindings = editForm.bindings.map((b, i) =>
    i === index ? { ...b, ...patch } : b,
  )
}

function parseContentTypes(text: string): string[] {
  return text
    .split(',')
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
}

const bindingColumns = computed<DataTableColumns<EditableBinding>>(() => [
  {
    title: '阶段',
    key: 'stage',
    render: (row) => STAGE_LABELS[row.stage],
  },
  {
    title: '阶段配置',
    key: 'stage_config_id',
    render: (row, index) =>
      h(NSelect, {
        value: row.stage_config_id,
        options: stageConfigOptionsFor(row.stage),
        clearable: true,
        placeholder: '选择阶段配置',
        onUpdateValue: (val: string | number | null) => {
          updateBinding(index, {
            stage_config_id: val === null ? null : String(val),
          })
        },
      }),
  },
  {
    title: '执行组',
    key: 'execution_group',
    render: (row, index) =>
      h(NInput, {
        value: row.execution_group,
        placeholder: '可选',
        onUpdateValue: (val: string) => {
          updateBinding(index, { execution_group: val })
        },
      }),
  },
  {
    title: '跳过',
    key: 'skip',
    render: (row, index) =>
      h(NSwitch, {
        value: row.skip,
        onUpdateValue: (val: boolean) => {
          updateBinding(index, { skip: val })
        },
      }),
  },
])

const isDefault = computed(
  () => selectedSchemeId.value !== null && store.defaultSchemeId === selectedSchemeId.value,
)

async function handleSave(): Promise<void> {
  if (!editForm.display_name.trim()) {
    message.warning('请输入方案名称')
    return
  }
  const bindings: SchemeStageBinding[] = editForm.bindings
    .filter((b) => b.stage_config_id !== null)
    .map((b) => ({
      stage: b.stage,
      stage_config_id: b.stage_config_id as string,
      execution_group: b.execution_group || null,
      skip_when_execution_group_has_output: b.skip,
    }))
  saving.value = true
  try {
    const content_types = parseContentTypes(editForm.content_types_text)
    if (selectedSchemeId.value) {
      const req: UpdateSchemeRequest = {
        display_name: editForm.display_name.trim(),
        description: editForm.description,
        bindings,
        prefer_gpu: editForm.prefer_gpu,
        content_types,
      }
      await store.updateScheme(selectedSchemeId.value, req)
      message.success('方案已保存')
    } else {
      const req: CreateSchemeRequest = {
        display_name: editForm.display_name.trim(),
        description: editForm.description,
        bindings,
        prefer_gpu: editForm.prefer_gpu,
        content_types,
      }
      await store.createScheme(req)
      message.success('方案已创建')
      resetForm()
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  } finally {
    saving.value = false
  }
}

async function handleSetDefault(): Promise<void> {
  if (!selectedSchemeId.value) return
  try {
    await store.setDefaultScheme(selectedSchemeId.value)
    message.success('已设为默认方案')
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  }
}

function confirmDelete(scheme: DubbingScheme): void {
  dialog.warning({
    title: '删除方案',
    content: `确认删除方案「${scheme.display_name}」？此操作不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await store.deleteScheme(scheme.id)
        message.success('方案已删除')
        if (selectedSchemeId.value === scheme.id) {
          selectedSchemeId.value = null
          resetForm()
        }
      } catch (e) {
        message.error(e instanceof Error ? e.message : String(e))
      }
    },
  })
}

onMounted(async () => {
  try {
    await store.loadAll()
    if (store.schemes.length > 0) {
      const target = store.defaultScheme ?? store.schemes[0]
      if (target) selectScheme(target)
    } else {
      resetForm()
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  }
})
</script>

<template>
  <div class="schemes-page">
    <NLayout has-sider class="schemes-layout">
      <NLayoutSider :width="300" bordered class="schemes-sider">
        <div class="sider-header">
          <span class="sider-title">方案列表</span>
          <NButton size="small" type="primary" @click="handleCreate">新增</NButton>
        </div>
        <div class="sider-list">
          <NEmpty v-if="store.schemes.length === 0" description="暂无方案" size="small" />
          <NList v-else hoverable clickable>
            <NListItem
              v-for="scheme in store.schemes"
              :key="scheme.id"
              :class="{ 'list-item-active': selectedSchemeId === scheme.id }"
              @click="selectScheme(scheme)"
            >
              <NThing
                :title="scheme.display_name"
                :description="scheme.description || '暂无描述'"
              >
                <template #footer>
                  <NTag
                    v-if="store.defaultSchemeId === scheme.id"
                    size="small"
                    type="success"
                  >
                    默认
                  </NTag>
                </template>
              </NThing>
              <template #suffix>
                <NButton
                  size="tiny"
                  type="error"
                  ghost
                  @click.stop="confirmDelete(scheme)"
                >
                  删除
                </NButton>
              </template>
            </NListItem>
          </NList>
        </div>
      </NLayoutSider>

      <NLayoutContent class="schemes-content">
        <div class="content-inner">
          <div class="content-header">
            <h3 class="content-title">
              {{ selectedSchemeId ? '编辑方案' : '新建方案' }}
            </h3>
            <NSpace>
              <NButton
                v-if="selectedSchemeId"
                :disabled="isDefault"
                @click="handleSetDefault"
              >
                设为默认
              </NButton>
              <NButton type="primary" :loading="saving" @click="handleSave">
                保存
              </NButton>
            </NSpace>
          </div>

          <NForm label-placement="left" :label-width="100">
            <NFormItem label="方案名称" required>
              <NInput v-model:value="editForm.display_name" placeholder="输入方案名称" />
            </NFormItem>
            <NFormItem label="描述">
              <NInput
                v-model:value="editForm.description"
                type="textarea"
                :rows="2"
                placeholder="方案描述"
              />
            </NFormItem>
            <NFormItem label="优先 GPU">
              <NSwitch v-model:value="editForm.prefer_gpu" />
            </NFormItem>
            <NFormItem label="内容类型">
              <NInput
                v-model:value="editForm.content_types_text"
                placeholder="多个类型用逗号分隔，如 video, audio"
              />
            </NFormItem>
            <NFormItem label="阶段绑定">
              <NDataTable
                :columns="bindingColumns"
                :data="editForm.bindings"
                :bordered="false"
                size="small"
              />
            </NFormItem>
          </NForm>
        </div>
      </NLayoutContent>
    </NLayout>
  </div>
</template>

<style scoped>
.schemes-page {
  height: 100%;
  padding: var(--space-6);
}
.schemes-layout {
  height: 100%;
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.schemes-sider {
  background-color: var(--bg-surface);
}
.sider-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-color);
}
.sider-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}
.sider-list {
  overflow-y: auto;
  max-height: calc(100% - 57px);
}
.list-item-active {
  background-color: var(--bg-hover);
}
.schemes-content {
  background-color: var(--bg-base);
}
.content-inner {
  padding: var(--space-6);
}
.content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-5);
}
.content-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}
</style>
