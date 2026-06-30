<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  NTabs,
  NTabPane,
  NDataTable,
  NButton,
  NSpace,
  NTag,
  NModal,
  NForm,
  NFormItem,
  NInput,
  NSelect,
  NSwitch,
  NCard,
  NGrid,
  NGridItem,
  NCollapse,
  NCollapseItem,
  NEmpty,
  NAlert,
  NSpin,
  NTooltip,
  useMessage,
  useDialog,
  type DataTableColumns,
} from 'naive-ui'
import { useModelServicesStore } from '@/stores/modelServices'
import settingsApi from '@/api/settings'
import type {
  ProviderAccount,
  StageProviderConfig,
  StageName,
  ProviderKind,
  CreateAccountRequest,
  CreateStageConfigRequest,
  ProviderRegistryEntry,
  LocalModelService,
  ModelDownloadSource,
  DependencyStatus,
  LocalModelCard,
  LocalModelStageGroup,
} from '@/types'

const store = useModelServicesStore()
const message = useMessage()
const dialog = useDialog()
const router = useRouter()

const STAGES: StageName[] = ['separation', 'asr', 'diarization', 'translation', 'tts']
const STAGE_LABELS: Record<StageName, string> = {
  separation: '人声分离',
  asr: '语音识别',
  diarization: '说话人分离',
  translation: '翻译',
  tts: '语音合成',
}

const stageOptions = STAGES.map((stage) => ({ label: STAGE_LABELS[stage], value: stage }))

const accountProviderOptions = computed(() =>
  store.providers
    .filter((provider) => provider.requires_api_key && provider.implemented && provider.mvp_enabled)
    .map((provider) => ({ label: provider.display_name, value: provider.provider_id })),
)

function providerKindOf(providerKey: string): ProviderKind {
  const provider = store.providers.find((item) => item.provider_id === providerKey)
  return provider?.requires_api_key ? 'api' : 'local'
}

function supportsStage(provider: ProviderRegistryEntry, stage: StageName): boolean {
  return provider.supported_stages.includes(stage)
}

function providerLabel(providerKey: string): string {
  return store.providers.find((item) => item.provider_id === providerKey)?.display_name ?? providerKey
}

function protocolMatchesStage(protocol: string, stage: StageName): boolean {
  const rules: Record<StageName, string[]> = {
    separation: ['separation'],
    asr: ['asr', 'transcribe'],
    diarization: ['diarize', 'diarization'],
    translation: ['translation', 'translate'],
    tts: ['tts'],
  }
  const lower = protocol.toLowerCase()
  return rules[stage].some((keyword) => lower.includes(keyword))
}

function basename(pathValue: string): string {
  const parts = pathValue.split(/[\\/]/).filter(Boolean)
  return parts[parts.length - 1] ?? pathValue
}

// Account management
const accountModalShow = ref(false)
const accountEditingId = ref<string | null>(null)
const accountSaving = ref(false)
const accountForm = reactive({
  display_name: '',
  provider_key: '',
  api_base_url: '',
  api_key: '',
})

function resetAccountForm(): void {
  accountForm.display_name = ''
  accountForm.provider_key = ''
  accountForm.api_base_url = ''
  accountForm.api_key = ''
  accountEditingId.value = null
}

function openCreateAccount(): void {
  resetAccountForm()
  accountForm.provider_key = accountProviderOptions.value[0]?.value ?? ''
  accountModalShow.value = true
}

function openEditAccount(account: ProviderAccount): void {
  accountEditingId.value = account.id
  accountForm.display_name = account.display_name
  accountForm.provider_key = account.provider_key
  accountForm.api_base_url = account.api_base_url
  accountForm.api_key = ''
  accountModalShow.value = true
}

async function submitAccount(): Promise<void> {
  if (!accountForm.display_name.trim()) {
    message.warning('请输入显示名称')
    return
  }
  if (!accountForm.provider_key) {
    message.warning('请选择供应商')
    return
  }
  accountSaving.value = true
  try {
    if (accountEditingId.value) {
      await store.updateAccount(accountEditingId.value, {
        display_name: accountForm.display_name.trim(),
        api_base_url: accountForm.api_base_url,
        api_key: accountForm.api_key || undefined,
      })
      message.success('账户已更新')
    } else {
      const req: CreateAccountRequest = {
        display_name: accountForm.display_name.trim(),
        provider_key: accountForm.provider_key,
        kind: 'api',
        api_base_url: accountForm.api_base_url || undefined,
        api_key: accountForm.api_key || undefined,
      }
      await store.createAccount(req)
      message.success('账户已创建')
    }
    accountModalShow.value = false
    resetAccountForm()
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  } finally {
    accountSaving.value = false
  }
}

function confirmDeleteAccount(account: ProviderAccount): void {
  dialog.warning({
    title: '删除账户',
    content: `确认删除账户“${account.display_name}”？此操作不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await store.deleteAccount(account.id)
        message.success('账户已删除')
      } catch (e) {
        message.error(e instanceof Error ? e.message : String(e))
      }
    },
  })
}

const accountColumns = computed<DataTableColumns<ProviderAccount>>(() => [
  { title: '显示名称', key: 'display_name' },
  {
    title: '供应商',
    key: 'provider_key',
    render: (row) => providerLabel(row.provider_key),
  },
  {
    title: '类型',
    key: 'kind',
    render: (row) =>
      h(NTag, { size: 'small' }, { default: () => (row.kind === 'api' ? 'API' : '本地') }),
  },
  {
    title: '状态',
    key: 'enabled',
    render: (row) =>
      h(
        NTag,
        { size: 'small', type: row.enabled ? 'success' : 'default' },
        { default: () => (row.enabled ? '启用' : '禁用') },
      ),
  },
  {
    title: '操作',
    key: 'actions',
    render: (row) =>
      h(NSpace, null, {
        default: () => [
          h(NButton, { size: 'small', onClick: () => openEditAccount(row) }, { default: () => '编辑' }),
          h(
            NButton,
            {
              size: 'small',
              type: 'error',
              ghost: true,
              onClick: () => confirmDeleteAccount(row),
            },
            { default: () => '删除' },
          ),
        ],
      }),
  },
])

// Stage configuration management
const stageConfigModalShow = ref(false)
const stageConfigEditingId = ref<string | null>(null)
const stageConfigSaving = ref(false)
const stageConfigForm = reactive({
  display_name: '',
  provider_key: '',
  stage: 'separation' as StageName,
  protocol: '',
  account_id: null as string | null,
  model_name: '',
  local_model_path: '',
  device: 'auto',
  precision: 'auto',
  quality_preset: 'standard',
  upload_media_to_cloud: false,
})

const qualityPresetOptions = [
  { label: '快速', value: 'fast' },
  { label: '标准', value: 'standard' },
  { label: '高质量', value: 'high' },
]

const selectedProvider = computed(() =>
  store.providers.find((provider) => provider.provider_id === stageConfigForm.provider_key) ?? null,
)

const isLocalStageProvider = computed(() => selectedProvider.value?.requires_api_key === false)

const selectedLocalModel = computed<LocalModelService | null>(() =>
  store.localModels.find((model) => model.provider_key === stageConfigForm.provider_key) ?? null,
)

const stageProviderOptions = computed(() =>
  store.providers
    .filter(
      (provider) =>
        provider.implemented &&
        provider.mvp_enabled &&
        supportsStage(provider, stageConfigForm.stage),
    )
    .sort((a, b) => Number(a.requires_api_key) - Number(b.requires_api_key))
    .map((provider) => ({
      label: provider.display_name,
      value: provider.provider_id,
    })),
)

const accountOptions = computed(() =>
  store.accounts
    .filter((account) => account.provider_key === stageConfigForm.provider_key && account.enabled)
    .map((account) => ({ label: account.display_name, value: account.id })),
)

const protocolOptions = computed(() => {
  const protocols = selectedProvider.value?.protocols ?? []
  const filtered = protocols.filter((protocol) => protocolMatchesStage(protocol, stageConfigForm.stage))
  const options = filtered.length > 0 ? filtered : protocols
  return options.map((protocol) => ({ label: protocol, value: protocol }))
})

const deviceOptions = computed(() =>
  (selectedLocalModel.value?.supported_devices ?? ['auto', 'cuda', 'cpu']).map((device) => ({
    label: device,
    value: device,
  })),
)

const precisionOptions = computed(() =>
  (selectedLocalModel.value?.precision_options ?? ['auto', 'float16', 'float32', 'int8']).map(
    (precision) => ({ label: precision, value: precision }),
  ),
)

function applyProviderDefaults(): void {
  const firstProtocol = protocolOptions.value[0]?.value ?? ''
  stageConfigForm.protocol = firstProtocol
  stageConfigForm.account_id = null
  stageConfigForm.model_name = ''
  stageConfigForm.local_model_path = ''
  stageConfigForm.device = 'auto'
  stageConfigForm.precision = 'auto'
  stageConfigForm.upload_media_to_cloud = selectedProvider.value?.requires_api_key === true

  const localModel = selectedLocalModel.value
  if (localModel) {
    stageConfigForm.model_name = basename(localModel.model_path)
    stageConfigForm.local_model_path = localModel.model_path
    stageConfigForm.device = localModel.default_device || 'auto'
    stageConfigForm.precision = localModel.precision_options.includes('auto')
      ? 'auto'
      : (localModel.precision_options[0] ?? 'auto')
  }
}

function resetStageConfigForm(): void {
  stageConfigForm.display_name = ''
  stageConfigForm.provider_key = ''
  stageConfigForm.stage = 'separation'
  stageConfigForm.protocol = ''
  stageConfigForm.account_id = null
  stageConfigForm.model_name = ''
  stageConfigForm.local_model_path = ''
  stageConfigForm.device = 'auto'
  stageConfigForm.precision = 'auto'
  stageConfigForm.quality_preset = 'standard'
  stageConfigForm.upload_media_to_cloud = false
  stageConfigEditingId.value = null
}

function pickFirstProviderForStage(): void {
  stageConfigForm.provider_key = stageProviderOptions.value[0]?.value ?? ''
  applyProviderDefaults()
}

function handleStageChanged(): void {
  if (!selectedProvider.value || !supportsStage(selectedProvider.value, stageConfigForm.stage)) {
    pickFirstProviderForStage()
  } else {
    applyProviderDefaults()
  }
}

function handleProviderChanged(): void {
  applyProviderDefaults()
  if (!stageConfigForm.display_name.trim() && selectedProvider.value) {
    stageConfigForm.display_name = `${STAGE_LABELS[stageConfigForm.stage]} - ${selectedProvider.value.display_name}`
  }
}

function openCreateStageConfig(stage?: StageName): void {
  resetStageConfigForm()
  if (stage) stageConfigForm.stage = stage
  pickFirstProviderForStage()
  if (selectedProvider.value) {
    stageConfigForm.display_name = `${STAGE_LABELS[stageConfigForm.stage]} - ${selectedProvider.value.display_name}`
  }
  stageConfigModalShow.value = true
}

function openEditStageConfig(config: StageProviderConfig): void {
  stageConfigEditingId.value = config.id
  stageConfigForm.display_name = config.display_name
  stageConfigForm.provider_key = config.provider_key
  stageConfigForm.stage = config.stage
  stageConfigForm.protocol = config.protocol
  stageConfigForm.account_id = config.account_id
  stageConfigForm.model_name = config.model_name
  stageConfigForm.local_model_path = config.local_model_path
  stageConfigForm.device = config.device || 'auto'
  stageConfigForm.precision = config.precision || 'auto'
  stageConfigForm.quality_preset = config.quality_preset
  stageConfigForm.upload_media_to_cloud = config.upload_media_to_cloud
  stageConfigModalShow.value = true
}

async function chooseLocalModelPath(): Promise<void> {
  const selected = await window.ivo?.showOpenDirectoryDialog()
  if (selected) {
    stageConfigForm.local_model_path = selected
    if (!stageConfigForm.model_name.trim()) {
      stageConfigForm.model_name = basename(selected)
    }
  }
}

async function submitStageConfig(): Promise<void> {
  if (!stageConfigForm.display_name.trim()) {
    message.warning('请输入显示名称')
    return
  }
  if (!stageConfigForm.provider_key) {
    message.warning('请选择供应商')
    return
  }
  if (!stageConfigForm.protocol) {
    message.warning('请选择协议')
    return
  }
  stageConfigSaving.value = true
  try {
    if (stageConfigEditingId.value) {
      await store.updateStageConfig(stageConfigEditingId.value, {
        display_name: stageConfigForm.display_name.trim(),
        account_id: stageConfigForm.account_id,
        model_name: stageConfigForm.model_name,
        local_model_path: stageConfigForm.local_model_path,
        device: stageConfigForm.device,
        precision: stageConfigForm.precision,
        quality_preset: stageConfigForm.quality_preset,
        upload_media_to_cloud: stageConfigForm.upload_media_to_cloud,
      })
      message.success('阶段配置已更新')
    } else {
      const req: CreateStageConfigRequest = {
        display_name: stageConfigForm.display_name.trim(),
        provider_key: stageConfigForm.provider_key,
        kind: providerKindOf(stageConfigForm.provider_key),
        stage: stageConfigForm.stage,
        protocol: stageConfigForm.protocol,
        account_id: stageConfigForm.account_id,
        model_name: stageConfigForm.model_name,
        local_model_path: stageConfigForm.local_model_path,
        device: stageConfigForm.device,
        precision: stageConfigForm.precision,
        quality_preset: stageConfigForm.quality_preset,
        upload_media_to_cloud: stageConfigForm.upload_media_to_cloud,
      }
      await store.createStageConfig(req)
      message.success('阶段配置已创建')
    }
    stageConfigModalShow.value = false
    resetStageConfigForm()
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  } finally {
    stageConfigSaving.value = false
  }
}

function confirmDeleteStageConfig(config: StageProviderConfig): void {
  dialog.warning({
    title: '删除阶段配置',
    content: `确认删除阶段配置“${config.display_name}”？此操作不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await store.deleteStageConfig(config.id)
        message.success('阶段配置已删除')
      } catch (e) {
        message.error(e instanceof Error ? e.message : String(e))
      }
    },
  })
}

const stageConfigColumns = computed<DataTableColumns<StageProviderConfig>>(() => [
  { title: '显示名称', key: 'display_name' },
  {
    title: '供应商',
    key: 'provider_key',
    render: (row) => providerLabel(row.provider_key),
  },
  { title: '协议', key: 'protocol' },
  { title: '模型', key: 'model_name' },
  { title: '设备', key: 'device' },
  { title: '精度', key: 'precision' },
  {
    title: '操作',
    key: 'actions',
    render: (row) =>
      h(NSpace, null, {
        default: () => [
          h(
            NButton,
            { size: 'small', onClick: () => openEditStageConfig(row) },
            { default: () => '编辑' },
          ),
          h(
            NButton,
            {
              size: 'small',
              type: 'error',
              ghost: true,
              onClick: () => confirmDeleteStageConfig(row),
            },
            { default: () => '删除' },
          ),
        ],
      }),
  },
])

function stageConfigsOf(stage: StageName): StageProviderConfig[] {
  return store.stageConfigsByStage[stage] ?? []
}

// Local models
const localModelsRefreshing = ref(false)
const modelDownloadSource = ref<ModelDownloadSource>('hf_mirror')
const modelDownloadSourceOptions: Array<{ label: string; value: ModelDownloadSource }> = [
  { label: '国内镜像 https://hf-mirror.com/', value: 'hf_mirror' },
  { label: 'Hugging Face https://huggingface.co/', value: 'huggingface' },
]

async function refreshLocalModels(): Promise<void> {
  localModelsRefreshing.value = true
  try {
    await Promise.all([store.loadLocalModels(), store.loadStageGroups()])
    message.success('本地模型状态已刷新')
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  } finally {
    localModelsRefreshing.value = false
  }
}

async function checkLocalModel(model: LocalModelCard): Promise<void> {
  try {
    await store.refreshLocalModel(model.provider_key)
    message.success(`${model.display_name} 检测完成`)
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  }
}

function openModelPathSettings(): void {
  router.push('/settings')
}

async function downloadLocalModel(model: LocalModelCard): Promise<void> {
  if (!model.huggingface_repo) {
    message.warning('该模型暂未配置可自动下载的 Hugging Face 仓库，请在设置中确认模型目录后手动放置。')
    return
  }
  try {
    const res = await store.downloadLocalModel(model.provider_key, {
      source: modelDownloadSource.value,
    })
    if (res.ok) {
      message.success(res.skipped ? '模型目录已存在，无需重复下载。' : `模型已下载到 ${res.local_dir}`)
    } else {
      message.error(`模型下载失败：${res.output.slice(0, 220)}`)
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  }
}

// ── 依赖管理（阶段分组重构） ──────────────────────────────────────────

const upgradeChecking = ref(false)
const activeStageTab = ref<string>('')

// 当前激活的阶段分组
const currentStageGroup = computed<LocalModelStageGroup | null>(() => {
  if (store.stageGroups.length === 0) return null
  if (!activeStageTab.value) {
    return store.stageGroups[0]
  }
  return store.stageGroups.find((g) => g.stage === activeStageTab.value) ?? store.stageGroups[0]
})

// 阶段 Tab 选项（带就绪数）
const stageTabOptions = computed(() =>
  store.stageGroups.map((g) => ({
    label: `${g.display_name} ${g.ready_count}/${g.total_count}`,
    value: g.stage,
  })),
)

// 依赖状态标签类型映射
function depStatusTagType(status: string): 'success' | 'warning' | 'error' {
  if (status === 'installed') return 'success'
  if (status === 'broken') return 'error'
  return 'warning'
}

function depStatusText(status: string): string {
  if (status === 'installed') return '已安装'
  if (status === 'broken') return '损坏'
  return '未安装'
}

// 模型就绪状态徽章
function readinessTagType(status: string): 'success' | 'warning' | 'error' {
  if (status === 'ready') return 'success'
  if (status === 'broken_deps') return 'error'
  return 'warning'
}

function readinessText(status: string): string {
  if (status === 'ready') return '就绪'
  if (status === 'missing_model') return '缺少模型文件'
  if (status === 'missing_deps') return '缺少依赖'
  if (status === 'broken_deps') return '依赖损坏'
  return status
}

// 模型依赖整体状态摘要
function modelDepsSummary(model: LocalModelCard): string {
  const total = model.dependencies.length
  const installed = model.dependencies.filter((d) => d.status === 'installed').length
  return `${installed}/${total} 已安装`
}

// 判断依赖是否正在安装中
function isDepInstalling(dep: DependencyStatus): boolean {
  return store.installBusy && store.installingPackage === dep.package_name
}

// 判断模型是否有任何依赖正在安装
function isModelBusy(model: LocalModelCard): boolean {
  if (!store.installBusy) return false
  if (store.installingPackage === '__all_missing__') return true
  return model.dependencies.some((d) => d.package_name === store.installingPackage)
}

// 安装前检查 PyPI 镜像连通性
async function checkPypiConnection(): Promise<boolean> {
  try {
    const conn = await settingsApi.testPypiConnection()
    if (!conn.ok) {
      message.warning(
        `当前 PyPI 镜像不可用（${conn.error || '连接失败'}）。` +
          '请到"设置 → PyPI 镜像"切换到国内镜像（如清华大学 TUNA）后重试。',
      )
      return false
    }
    return true
  } catch {
    // 网络检查本身失败，不阻塞安装（可能只是检查端点有问题）
    return true
  }
}

// 安装/修复单个依赖
async function handleInstallDep(dep: DependencyStatus): Promise<void> {
  const isBroken = dep.status === 'broken'
  const action = isBroken ? '修复' : '安装'
  const sharedHint =
    dep.shared_by_count && dep.shared_by_count > 1
      ? `（此依赖被 ${dep.shared_by_count} 个模型共用，安装后所有模型受益）`
      : ''

  // 安装前检查网络
  if (!(await checkPypiConnection())) return

  try {
    const res = await store.installDependency({
      package_name: dep.package_name,
      venv_name: dep.venv_name,
      force_reinstall: isBroken,
    })
    if (res.ok) {
      message.success(`${action} ${dep.package_name} 成功${sharedHint}`)
    } else {
      message.error(`${action} ${dep.package_name} 失败：${res.output.slice(0, 200)}`)
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  }
}

// 升级单个依赖
async function handleUpgradeDep(dep: DependencyStatus): Promise<void> {
  if (!(await checkPypiConnection())) return
  try {
    const res = await store.upgradeDependency({
      package_name: dep.package_name,
      venv_name: dep.venv_name,
    })
    if (res.ok) {
      message.success(`升级 ${dep.package_name} 成功`)
    } else {
      message.error(`升级 ${dep.package_name} 失败：${res.output.slice(0, 200)}`)
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  }
}

// 一键安装模型所有缺失/损坏依赖
async function handleInstallModelMissing(model: LocalModelCard): Promise<void> {
  const missing = model.dependencies.filter(
    (d) => d.status === 'missing' || d.status === 'broken',
  )
  if (missing.length === 0) {
    message.info('该模型没有缺失或损坏的依赖')
    return
  }
  dialog.warning({
    title: '安装缺失依赖',
    content: `将为模型"${model.display_name}"安装 ${missing.length} 个缺失/损坏的依赖：${missing.map((d) => d.package_name).join(', ')}。是否继续？`,
    positiveText: '开始安装',
    negativeText: '取消',
    onPositiveClick: async () => {
      for (const dep of missing) {
        try {
          const res = await store.installDependency({
            package_name: dep.package_name,
            venv_name: dep.venv_name,
            force_reinstall: dep.status === 'broken',
          })
          if (!res.ok) {
            message.error(`安装 ${dep.package_name} 失败：${res.output.slice(0, 200)}`)
          }
        } catch (e) {
          message.error(e instanceof Error ? e.message : String(e))
        }
      }
      message.success('模型依赖安装完成')
    },
  })
}

// 一键安装所有缺失/损坏依赖
async function handleInstallAllMissing(): Promise<void> {
  if (store.modelSummary?.missing_deps_count === 0) {
    message.info('没有缺失或损坏的依赖')
    return
  }
  dialog.warning({
    title: '一键安装缺失依赖',
    content: `将安装 ${store.modelSummary?.missing_deps_count ?? 0} 个缺失/损坏的依赖包，可能需要较长时间。是否继续？`,
    positiveText: '开始安装',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const res = await store.installAllMissing()
        if (res.failed === 0) {
          message.success(`全部安装成功（共 ${res.succeeded} 个）`)
        } else {
          message.warning(`安装完成：成功 ${res.succeeded} 个，失败 ${res.failed} 个`)
        }
      } catch (e) {
        message.error(e instanceof Error ? e.message : String(e))
      }
    },
  })
}

// 检查 PyPI 升级
async function handleCheckUpgrade(): Promise<void> {
  if (!(await checkPypiConnection())) return
  upgradeChecking.value = true
  try {
    const result = await store.checkUpgrade()
    const upgradable = result.items.filter((i) => i.can_upgrade).length
    if (upgradable === 0) {
      if (result.failed > 0) {
        message.warning(`已检查 ${result.checked} 个依赖，${result.failed} 个查询失败，请稍后重试`)
      } else {
        message.success('所有依赖均为最新版本')
      }
    } else {
      const failedHint = result.failed > 0 ? `，另有 ${result.failed} 个查询失败` : ''
      message.info(`发现 ${upgradable} 个可升级的依赖${failedHint}`)
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : String(e))
  } finally {
    upgradeChecking.value = false
  }
}

const apiProviders = computed(() => store.apiProviders.filter((provider) => provider.mvp_enabled))
const localProviders = computed(() => store.localProviders)

onMounted(() => {
  store.loadAll().catch((e) => {
    message.error(e instanceof Error ? e.message : String(e))
  })
  // 加载阶段分组数据（重构后主用），完成后默认选中第一个阶段标签
  store.loadStageGroups().then(() => {
    if (store.stageGroups.length > 0 && !activeStageTab.value) {
      activeStageTab.value = store.stageGroups[0].stage
    }
  }).catch((e) => {
    message.error(e instanceof Error ? e.message : String(e))
  })
})
</script>

<template>
  <div class="model-center-page">
    <h2 class="page-title">模型中心</h2>

    <NTabs type="line" animated>
      <NTabPane name="accounts" tab="供应商账户">
        <div class="tab-toolbar">
          <NButton type="primary" @click="openCreateAccount">新增账户</NButton>
        </div>
        <NDataTable
          :columns="accountColumns"
          :data="store.accounts"
          :bordered="false"
          :loading="store.loading"
        />
      </NTabPane>

      <NTabPane name="stage-configs" tab="阶段配置">
        <NCollapse :default-expanded-names="STAGES">
          <NCollapseItem
            v-for="stage in STAGES"
            :key="stage"
            :name="stage"
            :title="STAGE_LABELS[stage]"
          >
            <div class="tab-toolbar">
              <NButton size="small" type="primary" @click="openCreateStageConfig(stage)">
                新增配置
              </NButton>
            </div>
            <NDataTable
              :columns="stageConfigColumns"
              :data="stageConfigsOf(stage)"
              :bordered="false"
              size="small"
            />
          </NCollapseItem>
        </NCollapse>
      </NTabPane>

      <NTabPane name="local-models" tab="本地模型">
        <!-- 顶部概览栏 -->
        <div class="local-models-overview">
          <div class="overview-stats">
            <div class="stat-item">
              <span class="stat-label">总模型数</span>
              <span class="stat-value">{{ store.modelSummary?.total_models ?? 0 }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">已就绪</span>
              <span class="stat-value stat-ready">{{ store.modelSummary?.ready_models ?? 0 }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">未就绪</span>
              <span class="stat-value stat-missing">{{ store.modelSummary?.missing_models ?? 0 }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">缺失依赖</span>
              <span class="stat-value stat-warning">{{ store.modelSummary?.missing_deps_count ?? 0 }}</span>
            </div>
          </div>
          <NSpace :size="8" align="center">
            <NSelect
              v-model:value="modelDownloadSource"
              :options="modelDownloadSourceOptions"
              size="small"
              class="model-download-source-select"
            />
            <NButton
              :loading="upgradeChecking"
              :disabled="store.installBusy"
              @click="handleCheckUpgrade"
            >
              检查升级
            </NButton>
            <NButton
              type="warning"
              :disabled="(store.modelSummary?.missing_deps_count ?? 0) === 0 || store.installBusy"
              :loading="store.installBusy && store.installingPackage === '__all_missing__'"
              @click="handleInstallAllMissing"
            >
              一键安装缺失 ({{ store.modelSummary?.missing_deps_count ?? 0 }})
            </NButton>
            <NButton
              :loading="localModelsRefreshing || store.stageGroupsLoading"
              :disabled="store.installBusy"
              @click="refreshLocalModels"
            >
              刷新状态
            </NButton>
          </NSpace>
        </div>

        <!-- 缺失依赖警告 -->
        <NAlert
          v-if="(store.modelSummary?.missing_deps_count ?? 0) > 0"
          type="warning"
          :show-icon="true"
          style="margin-bottom: 12px"
        >
          检测到 <strong>{{ store.modelSummary?.missing_deps_count }}</strong> 个依赖缺失或损坏，本地模型流水线可能无法正常运行。点击"一键安装缺失"快速修复。
        </NAlert>

        <NEmpty
          v-if="store.stageGroups.length === 0 && !store.stageGroupsLoading"
          description="暂无本地模型"
          class="tab-empty"
        />

        <!-- 加载中提示（不阻塞用户看到页面结构） -->
        <div v-if="store.stageGroupsLoading && store.stageGroups.length === 0" class="stage-loading-hint">
          <NSpin size="medium" />
          <p style="margin-top: 12px; color: var(--text-tertiary)">正在检查依赖环境状态...</p>
        </div>

        <NSpin :show="store.stageGroupsLoading">
          <!-- 阶段切换 Tab -->
          <NTabs
            v-if="store.stageGroups.length > 0"
            v-model:value="activeStageTab"
            type="line"
            animated
            style="margin-bottom: 16px"
          >
            <NTabPane
              v-for="group in store.stageGroups"
              :key="group.stage"
              :name="group.stage"
              :tab="`${group.display_name} ${group.ready_count}/${group.total_count}`"
            >
              <!-- 当前阶段的模型卡片列表 -->
              <NSpace vertical :size="16">
                <NCard
                  v-for="model in group.models"
                  :key="model.provider_key"
                  size="small"
                  hoverable
                >
                  <!-- 卡片头部：模型名 + 标签 + 就绪状态 -->
                  <template #header>
                    <NSpace align="center" :size="8">
                      <span>{{ model.display_name }}</span>
                      <NTag v-if="model.recommended" size="small" type="success">推荐</NTag>
                      <NTag
                        v-for="tag in model.tags.filter((t) => t !== '推荐')"
                        :key="tag"
                        size="small"
                        type="info"
                      >
                        {{ tag }}
                      </NTag>
                    </NSpace>
                  </template>
                  <template #header-extra>
                    <NTag size="small" :type="readinessTagType(model.readiness.status)">
                      {{ readinessText(model.readiness.status) }}
                    </NTag>
                  </template>

                  <div class="model-card-content">
                    <!-- 模型文件区 -->
                    <div class="model-section">
                      <div class="section-title">模型文件</div>
                      <div class="model-file-row">
                        <NTag size="small" :type="model.model_dir_exists ? 'success' : 'warning'">
                          {{ model.model_dir_exists ? '已下载' : '未下载' }}
                        </NTag>
                        <span class="model-path-text" :title="model.model_path">
                          {{ model.model_path }}
                        </span>
                        <NButton
                          v-if="model.huggingface_repo && !model.model_dir_exists"
                          size="tiny"
                          type="primary"
                          :loading="store.isModelDownloading(model.provider_key)"
                          :disabled="store.downloadingModelKey !== null && !store.isModelDownloading(model.provider_key)"
                          @click="downloadLocalModel(model)"
                        >
                          下载模型
                        </NButton>
                        <NButton
                          v-if="!model.model_dir_exists"
                          size="tiny"
                          quaternary
                          @click="openModelPathSettings"
                        >
                          设置模型路径
                        </NButton>
                      </div>
                      <div v-if="!model.model_dir_exists" class="model-path-hint">
                        模型会下载到上方路径；根目录可在“设置 → 模型文件目录”中维护。
                      </div>
                      <div v-if="model.readiness.messages.length > 0" class="model-messages">
                        <div v-for="(msg, idx) in model.readiness.messages" :key="idx" class="model-message">
                          · {{ msg }}
                        </div>
                      </div>
                    </div>

                    <!-- 依赖环境区 -->
                    <div class="model-section">
                      <div class="section-title-row">
                        <span class="section-title">依赖环境</span>
                        <span class="deps-summary">{{ modelDepsSummary(model) }}</span>
                      </div>
                      <div class="dep-list">
                        <div v-for="dep in model.dependencies" :key="dep.package_name" class="dep-item">
                          <div class="dep-info">
                            <div class="dep-name-row">
                              <span class="dep-name">{{ dep.package_name }}</span>
                              <NTag size="tiny" :type="depStatusTagType(dep.status)">
                                {{ depStatusText(dep.status) }}
                              </NTag>
                              <NTooltip v-if="dep.shared_by_count && dep.shared_by_count > 1">
                                <template #trigger>
                                  <NTag size="tiny" type="default" round>
                                    共用 {{ dep.shared_by_count }}
                                  </NTag>
                                </template>
                                此依赖被 {{ dep.shared_by_count }} 个模型共用，安装后所有模型受益
                              </NTooltip>
                            </div>
                            <div class="dep-version-row">
                              <span class="dep-version-label">版本：</span>
                              <span class="dep-version-value">{{ dep.version || '-' }}</span>
                              <template v-if="dep.latest_version && dep.can_upgrade">
                                <span class="dep-version-arrow">→</span>
                                <NTooltip>
                                  <template #trigger>
                                    <NTag size="tiny" type="info">{{ dep.latest_version }}</NTag>
                                  </template>
                                  PyPI 最新版本
                                </NTooltip>
                              </template>
                            </div>
                            <div v-if="dep.venv_name !== '.venv'" class="dep-venv-row">
                              <span class="dep-version-label">venv：</span>
                              <span class="dep-version-value">{{ dep.venv_name }}</span>
                            </div>
                          </div>
                          <div class="dep-actions">
                            <!-- 安装/修复按钮 -->
                            <NButton
                              v-if="dep.status === 'missing' || dep.status === 'broken'"
                              size="small"
                              :type="dep.status === 'broken' ? 'error' : 'primary'"
                              :loading="isDepInstalling(dep)"
                              :disabled="store.installBusy && !isDepInstalling(dep)"
                              @click="handleInstallDep(dep)"
                            >
                              {{ dep.status === 'broken' ? '修复' : '安装' }}
                            </NButton>
                            <!-- 升级按钮 -->
                            <NButton
                              v-if="dep.can_upgrade && dep.status === 'installed'"
                              size="small"
                              type="info"
                              :loading="isDepInstalling(dep)"
                              :disabled="store.installBusy && !isDepInstalling(dep)"
                              @click="handleUpgradeDep(dep)"
                            >
                              升级
                            </NButton>
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- 操作按钮区 -->
                    <div class="model-actions">
                      <NButton
                        size="small"
                        :disabled="isModelBusy(model) || store.installBusy"
                        :loading="store.isModelChecking(model.provider_key)"
                        @click="checkLocalModel(model)"
                      >
                        检测
                      </NButton>
                      <NButton
                        size="small"
                        type="primary"
                        :disabled="isModelBusy(model) || store.installBusy"
                        @click="handleInstallModelMissing(model)"
                      >
                        安装缺失依赖
                      </NButton>
                    </div>
                  </div>
                </NCard>
              </NSpace>
            </NTabPane>
          </NTabs>
        </NSpin>
      </NTabPane>

      <NTabPane name="provider-catalog" tab="供应商目录">
        <NGrid :cols="2" :x-gap="16" :y-gap="16" responsive="screen">
          <NGridItem>
            <NCard title="API 供应商" size="small">
              <NEmpty v-if="apiProviders.length === 0" description="暂无" />
              <NSpace v-else vertical :size="12">
                <div v-for="provider in apiProviders" :key="provider.provider_id" class="provider-item">
                  <div class="provider-name">{{ provider.display_name }}</div>
                  <div class="provider-id">{{ provider.provider_id }}</div>
                  <NSpace :size="4" style="margin-top: 4px">
                    <NTag
                      v-for="stage in provider.supported_stages"
                      :key="stage"
                      size="small"
                      type="info"
                    >
                      {{ stage }}
                    </NTag>
                  </NSpace>
                </div>
              </NSpace>
            </NCard>
          </NGridItem>
          <NGridItem>
            <NCard title="本地供应商" size="small">
              <NEmpty v-if="localProviders.length === 0" description="暂无" />
              <NSpace v-else vertical :size="12">
                <div v-for="provider in localProviders" :key="provider.provider_id" class="provider-item">
                  <div class="provider-name">{{ provider.display_name }}</div>
                  <div class="provider-id">{{ provider.provider_id }}</div>
                  <NSpace :size="4" style="margin-top: 4px">
                    <NTag
                      v-for="stage in provider.supported_stages"
                      :key="stage"
                      size="small"
                      type="info"
                    >
                      {{ stage }}
                    </NTag>
                  </NSpace>
                </div>
              </NSpace>
            </NCard>
          </NGridItem>
        </NGrid>
      </NTabPane>
    </NTabs>

    <NModal
      v-model:show="accountModalShow"
      preset="card"
      :title="accountEditingId ? '编辑账户' : '新增账户'"
      style="width: 520px; max-width: 90vw"
    >
      <NForm label-placement="left" :label-width="100">
        <NFormItem label="显示名称" required>
          <NInput v-model:value="accountForm.display_name" placeholder="输入显示名称" />
        </NFormItem>
        <NFormItem label="供应商" required>
          <NSelect
            v-model:value="accountForm.provider_key"
            :options="accountProviderOptions"
            :disabled="accountEditingId !== null"
            placeholder="选择供应商"
          />
        </NFormItem>
        <NFormItem label="API Base URL">
          <NInput v-model:value="accountForm.api_base_url" placeholder="https://..." />
        </NFormItem>
        <NFormItem label="API Key">
          <NInput
            v-model:value="accountForm.api_key"
            type="password"
            show-password-on="click"
            :placeholder="accountEditingId ? '留空则不修改' : '输入 API Key'"
          />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="accountModalShow = false">取消</NButton>
          <NButton type="primary" :loading="accountSaving" @click="submitAccount">
            保存
          </NButton>
        </NSpace>
      </template>
    </NModal>

    <NModal
      v-model:show="stageConfigModalShow"
      preset="card"
      :title="stageConfigEditingId ? '编辑阶段配置' : '新增阶段配置'"
      style="width: 620px; max-width: 90vw"
    >
      <NForm label-placement="left" :label-width="110">
        <NFormItem label="显示名称" required>
          <NInput v-model:value="stageConfigForm.display_name" placeholder="输入显示名称" />
        </NFormItem>
        <NFormItem label="阶段" required>
          <NSelect
            v-model:value="stageConfigForm.stage"
            :options="stageOptions"
            :disabled="stageConfigEditingId !== null"
            @update:value="handleStageChanged"
          />
        </NFormItem>
        <NFormItem label="供应商" required>
          <NSelect
            v-model:value="stageConfigForm.provider_key"
            :options="stageProviderOptions"
            :disabled="stageConfigEditingId !== null"
            placeholder="选择供应商"
            @update:value="handleProviderChanged"
          />
        </NFormItem>
        <NFormItem label="协议" required>
          <NSelect
            v-model:value="stageConfigForm.protocol"
            :options="protocolOptions"
            :disabled="stageConfigEditingId !== null"
            placeholder="选择协议"
          />
        </NFormItem>
        <NFormItem v-if="!isLocalStageProvider" label="关联账户">
          <NSelect
            v-model:value="stageConfigForm.account_id"
            :options="accountOptions"
            clearable
            placeholder="选择关联账户"
          />
        </NFormItem>
        <NFormItem label="模型名称">
          <NInput v-model:value="stageConfigForm.model_name" placeholder="自动填充，可修改" />
        </NFormItem>
        <NFormItem v-if="isLocalStageProvider" label="本地模型路径">
          <NSpace vertical :size="8" style="width: 100%">
            <NInput
              v-model:value="stageConfigForm.local_model_path"
              placeholder="自动使用设置页模型目录，可重新选择"
            />
            <NButton size="small" @click="chooseLocalModelPath">重新选择目录</NButton>
          </NSpace>
        </NFormItem>
        <NFormItem v-if="isLocalStageProvider" label="设备">
          <NSelect v-model:value="stageConfigForm.device" :options="deviceOptions" />
        </NFormItem>
        <NFormItem v-if="isLocalStageProvider" label="精度">
          <NSelect v-model:value="stageConfigForm.precision" :options="precisionOptions" />
        </NFormItem>
        <NFormItem label="质量预设">
          <NSelect
            v-model:value="stageConfigForm.quality_preset"
            :options="qualityPresetOptions"
            placeholder="选择质量预设"
          />
        </NFormItem>
        <NFormItem v-if="!isLocalStageProvider" label="上传媒体到云端">
          <NSwitch v-model:value="stageConfigForm.upload_media_to_cloud" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="stageConfigModalShow = false">取消</NButton>
          <NButton type="primary" :loading="stageConfigSaving" @click="submitStageConfig">
            保存
          </NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>

<style scoped>
.model-center-page {
  padding: var(--space-6);
}
.page-title {
  margin: 0 0 var(--space-5);
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}
.tab-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-bottom: var(--space-4);
}
.tab-empty {
  padding: var(--space-10) 0;
}
.model-card-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.model-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  font-size: 13px;
}
.model-label {
  color: var(--text-secondary);
}
.model-value {
  color: var(--text-primary);
}
.model-path {
  overflow-wrap: anywhere;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: 12px;
}
.provider-item {
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--border-color);
}
.provider-item:last-child {
  border-bottom: none;
}

/* 依赖管理样式 */
.local-models-toolbar {
  justify-content: flex-start;
}
.dep-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.dep-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--bg-secondary, transparent);
}
.dep-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.dep-name-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 13px;
}
.dep-name {
  font-weight: 500;
  color: var(--text-primary);
  font-family: var(--font-mono);
  overflow-wrap: anywhere;
}
.dep-version-row,
.dep-venv-row {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}
.dep-version-label {
  color: var(--text-tertiary);
}
.dep-version-value {
  color: var(--text-secondary);
  font-family: var(--font-mono);
}
.dep-version-arrow {
  color: var(--text-tertiary);
  margin: 0 2px;
}
.dep-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}
.provider-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}
.provider-id {
  font-size: 12px;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}

/* 本地模型阶段分组样式 */
.local-models-overview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-4);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--bg-secondary, transparent);
}
.overview-stats {
  display: flex;
  align-items: center;
  gap: var(--space-5);
  flex-wrap: wrap;
}
.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 64px;
}
.stat-label {
  font-size: 12px;
  color: var(--text-tertiary);
}
.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}
.stat-ready {
  color: var(--success-color, #18a058);
}
.stat-missing {
  color: var(--error-color, #d03050);
}
.stat-warning {
  color: var(--warning-color, #f0a020);
}
.model-download-source-select {
  width: 230px;
}
.model-card-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.model-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-2) 0;
  border-top: 1px dashed var(--border-color);
}
.model-section:first-child {
  border-top: none;
  padding-top: 0;
}
.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}
.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}
.deps-summary {
  font-size: 12px;
  color: var(--text-tertiary);
}
.model-file-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.model-path-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: 12px;
}
.model-path-hint {
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-tertiary);
}
.model-messages {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-left: var(--space-2);
  font-size: 12px;
  color: var(--text-secondary);
}
.model-message {
  line-height: 1.5;
}
.model-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px dashed var(--border-color);
}
</style>
