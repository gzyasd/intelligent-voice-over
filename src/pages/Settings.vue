<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  NCard,
  NForm,
  NFormItem,
  NInput,
  NSwitch,
  NSelect,
  NButton,
  NSpace,
  NTag,
  NInputGroup,
  useMessage,
} from 'naive-ui'
import { useSettingsStore } from '@/stores/settings'
import environmentApi from '@/api/environment'
import settingsApi from '@/api/settings'
import type { VenvInfo } from '@/api/environment'
import type { MirrorTestResult, PipMirrorKey, ThemeMode } from '@/types'

const settingsStore = useSettingsStore()
const message = useMessage()

const modelsDir = ref('')
const projectsDir = ref('')
const preferGpu = ref(false)
const theme = ref<ThemeMode>('dark')
const pipMirror = ref<PipMirrorKey>('official')
const lmStudioBaseUrl = ref('')
const customVenvPython = ref('')
const customPyannotePython = ref('')
const saving = ref(false)

// PyPI 镜像测试
const testingMirrors = ref(false)
const mirrorTestResults = ref<MirrorTestResult[]>([])

async function handleTestMirrors() {
  testingMirrors.value = true
  try {
    const res = await settingsApi.testMirrors()
    mirrorTestResults.value = res.results
    const okCount = res.results.filter((r) => r.ok).length
    message.success(`测试完成：${okCount}/${res.results.length} 个镜像可用`)
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  } finally {
    testingMirrors.value = false
  }
}

// venv 路径诊断信息（只读）
const venvs = ref<VenvInfo[]>([])
const venvsLoading = ref(false)

const themeOptions = [
  { label: '深色', value: 'dark' },
  { label: '浅色', value: 'light' },
  { label: '跟随系统', value: 'system' },
]
const pipMirrorOptions = [
  { label: '官方 PyPI', value: 'official' },
  { label: '清华大学 TUNA', value: 'tsinghua' },
  { label: '阿里云', value: 'aliyun' },
  { label: '中科大 USTC', value: 'ustc' },
]

const mainVenv = computed(() => venvs.value.find((v) => v.name === '.venv') ?? null)
const pyannoteVenv = computed(() => venvs.value.find((v) => v.name === '.venv-pyannote') ?? null)

async function loadVenvs() {
  venvsLoading.value = true
  try {
    const res = await environmentApi.listVenvs()
    venvs.value = res.venvs
  } catch (e) {
    // 静默失败，不阻塞设置页面
    console.error('加载 venv 信息失败', e)
  } finally {
    venvsLoading.value = false
  }
}

// Python 可执行文件过滤器
const PYTHON_EXE_FILTERS = [
  { name: 'Python 可执行文件', extensions: ['exe'] },
  { name: '所有文件', extensions: ['*'] },
]

async function browseVenvPython() {
  if (!window.ivo) {
    message.warning('当前环境不支持文件选择，请手动输入路径')
    return
  }
  try {
    const filePath = await window.ivo.showOpenDialog(PYTHON_EXE_FILTERS)
    if (filePath) {
      customVenvPython.value = filePath
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  }
}

async function browsePyannotePython() {
  if (!window.ivo) {
    message.warning('当前环境不支持文件选择，请手动输入路径')
    return
  }
  try {
    const filePath = await window.ivo.showOpenDialog(PYTHON_EXE_FILTERS)
    if (filePath) {
      customPyannotePython.value = filePath
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  }
}

async function handleSave() {
  saving.value = true
  try {
    await settingsStore.save({
      models_dir: modelsDir.value,
      projects_dir: projectsDir.value,
      prefer_gpu: preferGpu.value,
      theme: theme.value,
      pip_mirror: pipMirror.value,
      lm_studio_base_url: lmStudioBaseUrl.value,
      custom_venv_python: customVenvPython.value || null,
      custom_pyannote_python: customPyannotePython.value || null,
    })
    message.success('设置已保存')
    // 保存后刷新 venv 诊断信息（自定义路径可能改变解析结果）
    void loadVenvs()
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    await settingsStore.load()
    const s = settingsStore.userSettings
    if (s) {
      modelsDir.value = s.models_dir
      projectsDir.value = s.projects_dir
      preferGpu.value = s.prefer_gpu
      theme.value = s.theme
      pipMirror.value = s.pip_mirror
      lmStudioBaseUrl.value = s.lm_studio_base_url
      customVenvPython.value = s.custom_venv_python ?? ''
      customPyannotePython.value = s.custom_pyannote_python ?? ''
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  }
  // 加载 venv 路径信息（不阻塞设置加载）
  void loadVenvs()
})
</script>

<template>
  <div class="settings-page">
    <h2 class="page-title">设置</h2>
    <NCard class="settings-card">
      <NForm label-placement="left" :label-width="120">
        <NFormItem label="模型目录">
          <NInput v-model:value="modelsDir" placeholder="模型权重存放目录" />
        </NFormItem>
        <NFormItem label="项目目录">
          <NInput v-model:value="projectsDir" placeholder="项目存放目录" />
        </NFormItem>
        <NFormItem label="GPU 偏好">
          <NSwitch v-model:value="preferGpu" />
        </NFormItem>
        <NFormItem label="主题">
          <NSelect v-model:value="theme" :options="themeOptions" />
        </NFormItem>
        <NFormItem label="PyPI 镜像">
          <NSpace vertical style="width: 100%">
            <NSelect v-model:value="pipMirror" :options="pipMirrorOptions" />
            <NButton size="small" :loading="testingMirrors" @click="handleTestMirrors">
              测试所有镜像连通性
            </NButton>
            <div v-if="mirrorTestResults.length > 0" class="mirror-test-results">
              <div
                v-for="r in mirrorTestResults"
                :key="r.key"
                class="mirror-test-item"
              >
                <NTag size="small" :type="r.ok ? 'success' : 'error'">
                  {{ r.ok ? '可用' : '不可用' }}
                </NTag>
                <span class="mirror-label">{{ r.label }}</span>
                <span class="mirror-latency">{{ r.ok ? `${r.latency_ms}ms` : r.error || '连接失败' }}</span>
              </div>
            </div>
          </NSpace>
        </NFormItem>
        <NFormItem label="LM Studio URL">
          <NInput v-model:value="lmStudioBaseUrl" placeholder="LM Studio 基础 URL" />
        </NFormItem>
        <NFormItem :label-width="0">
          <NSpace>
            <NButton type="primary" :loading="saving" @click="handleSave">保存</NButton>
          </NSpace>
        </NFormItem>
      </NForm>
    </NCard>

    <!-- venv 路径诊断信息 -->
    <NCard class="settings-card venv-card" title="依赖环境路径">
      <template #header-extra>
        <NButton size="small" :loading="venvsLoading" @click="loadVenvs">刷新</NButton>
      </template>
      <div class="venv-info-list">
        <div class="venv-info-row">
          <div class="venv-info-label">
            主 venv (.venv)
            <NTag v-if="mainVenv" size="small" :type="mainVenv.exists ? 'success' : 'error'">
              {{ mainVenv.exists ? '已就绪' : '未找到' }}
            </NTag>
          </div>
          <NInputGroup>
            <NInput
              v-model:value="customVenvPython"
              placeholder="留空则自动搜索，可点击右侧按钮选择 python.exe"
              clearable
            />
            <NButton @click="browseVenvPython">浏览</NButton>
          </NInputGroup>
          <div v-if="mainVenv?.python_path" class="venv-resolved">
            解析路径：<code>{{ mainVenv.python_path }}</code>
          </div>
        </div>
        <div class="venv-info-row">
          <div class="venv-info-label">
            pyannote venv (.venv-pyannote)
            <NTag v-if="pyannoteVenv" size="small" :type="pyannoteVenv.exists ? 'success' : 'error'">
              {{ pyannoteVenv.exists ? '已就绪' : '未找到' }}
            </NTag>
          </div>
          <NInputGroup>
            <NInput
              v-model:value="customPyannotePython"
              placeholder="留空则自动搜索，可点击右侧按钮选择 python.exe"
              clearable
            />
            <NButton @click="browsePyannotePython">浏览</NButton>
          </NInputGroup>
          <div v-if="pyannoteVenv?.python_path" class="venv-resolved">
            解析路径：<code>{{ pyannoteVenv.python_path }}</code>
          </div>
        </div>
        <div class="venv-tip">
          可点击"浏览"按钮选择自定义 Python 解释器（如
          <code>D:\myenv\.venv\Scripts\python.exe</code>），保存后生效。
          留空则自动搜索安装目录 resources/ 下的 .venv 和 .venv-pyannote。
          也可运行
          <code>scripts/copy-venv-to-install.ps1 -InstallDir "&lt;IVO 安装目录&gt;"</code>
          将 .venv 和 .venv-pyannote 复制到安装目录的 resources/ 下。
        </div>
      </div>
    </NCard>
  </div>
</template>

<style scoped>
.settings-page {
  padding: var(--space-6);
}
.page-title {
  margin: 0 0 var(--space-5);
  font-size: 20px;
  font-weight: 600;
}
.settings-card {
  max-width: 640px;
}
.venv-card {
  margin-top: var(--space-4);
}
.venv-info-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.venv-info-row {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.venv-info-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}
.venv-resolved {
  font-size: 12px;
  color: var(--text-tertiary);
  word-break: break-all;
}
.venv-resolved code {
  font-family: var(--font-mono);
  font-size: 11px;
}
.venv-tip {
  margin-top: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: 4px;
  background: var(--bg-secondary, transparent);
  font-size: 12px;
  color: var(--text-tertiary);
  line-height: 1.5;
}
.venv-tip code {
  padding: 1px 4px;
  border-radius: 3px;
  background: var(--bg-tertiary, rgba(128, 128, 128, 0.15));
  font-family: var(--font-mono);
  font-size: 11px;
  word-break: break-all;
}

/* PyPI 镜像测试结果 */
.mirror-test-results {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 4px;
}
.mirror-test-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  background: var(--bg-secondary, rgba(128, 128, 128, 0.08));
  font-size: 12px;
}
.mirror-label {
  flex: 1;
  color: var(--text-secondary);
}
.mirror-latency {
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: 11px;
}
</style>
