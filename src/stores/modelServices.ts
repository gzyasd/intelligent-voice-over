import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import modelServicesApi from '@/api/modelServices'
import type {
  ProviderRegistryEntry,
  ProviderAccount,
  StageProviderConfig,
  DubbingScheme,
  LocalModelService,
  CreateAccountRequest,
  UpdateAccountRequest,
  CreateStageConfigRequest,
  UpdateStageConfigRequest,
  CreateSchemeRequest,
  UpdateSchemeRequest,
  ServiceDependencyGroup,
  DownloadLocalModelRequest,
  DownloadLocalModelResponse,
  InstallDependencyRequest,
  UpgradeDependencyRequest,
  InstallAllMissingResponse,
  UpgradeCheckResponse,
  LocalModelStageGroup,
  LocalModelSummary,
} from '@/types'

export const useModelServicesStore = defineStore('modelServices', () => {
  // 状态
  const providers = ref<ProviderRegistryEntry[]>([])
  const accounts = ref<ProviderAccount[]>([])
  const stageConfigs = ref<StageProviderConfig[]>([])
  const schemes = ref<DubbingScheme[]>([])
  const localModels = ref<LocalModelService[]>([])
  const defaultSchemeId = ref<string | null>(null)
  const loading = ref(false)

  // 依赖管理状态
  const dependencyGroups = ref<ServiceDependencyGroup[]>([])
  const dependenciesLoading = ref(false)
  const installingPackage = ref<string | null>(null) // 当前正在安装/升级的包名
  const installBusy = ref(false) // 全局安装锁（与后端 _install_lock 对应）

  // 阶段分组状态（重构后主用）
  const stageGroups = ref<LocalModelStageGroup[]>([])
  const modelSummary = ref<LocalModelSummary | null>(null)
  const stageGroupsLoading = ref(false)
  const checkingModelKeys = ref<string[]>([])
  const downloadingModelKey = ref<string | null>(null)

  // 计算属性
  const apiProviders = computed(() => providers.value.filter((p) => p.requires_api_key))
  const localProviders = computed(() => providers.value.filter((p) => !p.requires_api_key))

  const stageConfigsByStage = computed(() => {
    const map: Record<string, StageProviderConfig[]> = {}
    for (const cfg of stageConfigs.value) {
      if (!map[cfg.stage]) map[cfg.stage] = []
      map[cfg.stage].push(cfg)
    }
    return map
  })

  const defaultScheme = computed(() =>
    schemes.value.find((s) => s.id === defaultSchemeId.value) ?? null,
  )

  // 依赖管理计算属性
  // 所有依赖的扁平列表
  const allDependencies = computed(() =>
    dependencyGroups.value.flatMap((g) => g.dependencies),
  )
  // 缺失/损坏的依赖数量
  const missingCount = computed(
    () => allDependencies.value.filter((d) => d.status === 'missing' || d.status === 'broken').length,
  )
  // 可升级的依赖数量
  const upgradableCount = computed(
    () => allDependencies.value.filter((d) => d.can_upgrade).length,
  )

  // 加载方法
  async function loadProviders(): Promise<void> {
    providers.value = await modelServicesApi.providers.list()
  }

  async function loadAccounts(): Promise<void> {
    accounts.value = await modelServicesApi.accounts.list()
  }

  async function loadStageConfigs(): Promise<void> {
    stageConfigs.value = await modelServicesApi.stageConfigs.list()
  }

  async function loadSchemes(): Promise<void> {
    const [list, def] = await Promise.all([
      modelServicesApi.schemes.list(),
      modelServicesApi.schemes.getDefault(),
    ])
    schemes.value = list
    defaultSchemeId.value = def.scheme_id
  }

  async function loadLocalModels(): Promise<void> {
    localModels.value = await modelServicesApi.localModels.list()
  }

  async function loadAll(): Promise<void> {
    loading.value = true
    try {
      await Promise.all([
        loadProviders(),
        loadAccounts(),
        loadStageConfigs(),
        loadSchemes(),
        loadLocalModels(),
      ])
    } finally {
      loading.value = false
    }
  }

  // 账户操作
  async function createAccount(req: CreateAccountRequest): Promise<void> {
    await modelServicesApi.accounts.create(req)
    await loadAccounts()
  }

  async function updateAccount(accountId: string, req: UpdateAccountRequest): Promise<void> {
    await modelServicesApi.accounts.update(accountId, req)
    await loadAccounts()
  }

  async function deleteAccount(accountId: string): Promise<void> {
    await modelServicesApi.accounts.delete(accountId)
    await loadAccounts()
  }

  // 阶段配置操作
  async function createStageConfig(req: CreateStageConfigRequest): Promise<void> {
    await modelServicesApi.stageConfigs.create(req)
    await loadStageConfigs()
  }

  async function updateStageConfig(configId: string, req: UpdateStageConfigRequest): Promise<void> {
    await modelServicesApi.stageConfigs.update(configId, req)
    await loadStageConfigs()
  }

  async function deleteStageConfig(configId: string): Promise<void> {
    await modelServicesApi.stageConfigs.delete(configId)
    await loadStageConfigs()
  }

  // 方案操作
  async function createScheme(req: CreateSchemeRequest): Promise<void> {
    await modelServicesApi.schemes.create(req)
    await loadSchemes()
  }

  async function updateScheme(schemeId: string, req: UpdateSchemeRequest): Promise<void> {
    await modelServicesApi.schemes.update(schemeId, req)
    await loadSchemes()
  }

  async function deleteScheme(schemeId: string): Promise<void> {
    await modelServicesApi.schemes.delete(schemeId)
    await loadSchemes()
  }

  async function setDefaultScheme(schemeId: string): Promise<void> {
    await modelServicesApi.schemes.setDefault(schemeId)
    defaultSchemeId.value = schemeId
  }

  // ── 依赖管理操作 ──────────────────────────────────────────────────────

  // 加载阶段分组数据（重构后主用）
  async function loadStageGroups(): Promise<void> {
    stageGroupsLoading.value = true
    try {
      const res = await modelServicesApi.localModels.stageGroups()
      stageGroups.value = res.stages
      modelSummary.value = res.summary
    } finally {
      stageGroupsLoading.value = false
    }
  }

  function isModelChecking(providerKey: string): boolean {
    return checkingModelKeys.value.includes(providerKey)
  }

  function isModelDownloading(providerKey: string): boolean {
    return downloadingModelKey.value === providerKey
  }

  function recomputeModelSummary(): void {
    const models = stageGroups.value.flatMap((group) => group.models)
    for (const group of stageGroups.value) {
      group.ready_count = group.models.filter((model) => model.readiness.status === 'ready').length
    }
    modelSummary.value = {
      total_models: models.length,
      ready_models: models.filter((model) => model.readiness.status === 'ready').length,
      missing_models: models.filter((model) => model.readiness.status !== 'ready').length,
      missing_deps_count: models.reduce(
        (count, model) =>
          count
          + model.dependencies.filter((dep) => dep.status === 'missing' || dep.status === 'broken')
            .length,
        0,
      ),
    }
  }

  async function refreshLocalModel(providerKey: string): Promise<void> {
    if (isModelChecking(providerKey)) return
    checkingModelKeys.value = [...checkingModelKeys.value, providerKey]
    try {
      const refreshed = await modelServicesApi.localModels.status(providerKey)
      for (const group of stageGroups.value) {
        const index = group.models.findIndex((model) => model.provider_key === providerKey)
        if (index < 0) continue
        const previous = group.models[index]
        const upgradeInfo = new Map(
          previous.dependencies.map((dep) => [
            dep.package_name,
            { latest_version: dep.latest_version, can_upgrade: dep.can_upgrade },
          ]),
        )
        for (const dep of refreshed.dependencies) {
          const cached = upgradeInfo.get(dep.package_name)
          if (cached?.latest_version) {
            dep.latest_version = cached.latest_version
            dep.can_upgrade = cached.can_upgrade
          }
        }
        group.models[index] = refreshed
        break
      }
      recomputeModelSummary()
    } finally {
      checkingModelKeys.value = checkingModelKeys.value.filter((key) => key !== providerKey)
    }
  }

  async function downloadLocalModel(
    providerKey: string,
    req: DownloadLocalModelRequest,
  ): Promise<DownloadLocalModelResponse> {
    if (downloadingModelKey.value) {
      throw new Error('已有模型下载任务正在进行中，请等待完成。')
    }
    downloadingModelKey.value = providerKey
    try {
      const res = await modelServicesApi.localModels.download(providerKey, req)
      await Promise.all([loadLocalModels(), refreshLocalModel(providerKey)])
      return res
    } finally {
      downloadingModelKey.value = null
    }
  }

  // 加载所有依赖状态
  async function loadDependenciesStatus(): Promise<void> {
    dependenciesLoading.value = true
    try {
      dependencyGroups.value = await modelServicesApi.localModels.allDependenciesStatus()
    } finally {
      dependenciesLoading.value = false
    }
  }

  // 安装单个依赖（force_reinstall=true 用于修复 broken）
  async function installDependency(
    req: InstallDependencyRequest,
  ): Promise<{ ok: boolean; output: string }> {
    if (installBusy.value) {
      throw new Error('另一个安装任务正在进行中，请等待完成。')
    }
    installBusy.value = true
    installingPackage.value = req.package_name
    try {
      const res = await modelServicesApi.localModels.installDependency(req)
      // 安装完成后刷新阶段分组状态（替代 loadDependenciesStatus）
      await loadStageGroups()
      return { ok: res.ok, output: res.output }
    } finally {
      installBusy.value = false
      installingPackage.value = null
    }
  }

  // 升级单个依赖
  async function upgradeDependency(
    req: UpgradeDependencyRequest,
  ): Promise<{ ok: boolean; output: string }> {
    if (installBusy.value) {
      throw new Error('另一个安装任务正在进行中，请等待完成。')
    }
    installBusy.value = true
    installingPackage.value = req.package_name
    try {
      const res = await modelServicesApi.localModels.upgradeDependency(req)
      await loadStageGroups()
      return { ok: res.ok, output: res.output }
    } finally {
      installBusy.value = false
      installingPackage.value = null
    }
  }

  // 一键安装所有缺失/broken 依赖
  async function installAllMissing(): Promise<InstallAllMissingResponse> {
    if (installBusy.value) {
      throw new Error('另一个安装任务正在进行中，请等待完成。')
    }
    installBusy.value = true
    installingPackage.value = '__all_missing__'
    try {
      const res = await modelServicesApi.localModels.installAllMissing()
      await loadStageGroups()
      return res
    } finally {
      installBusy.value = false
      installingPackage.value = null
    }
  }

  // 检查 PyPI 升级（会更新 stageGroups 中各依赖的 latest_version/can_upgrade）
  async function checkUpgrade(): Promise<UpgradeCheckResponse> {
    const response = await modelServicesApi.localModels.upgradeCheck()
    const items = response.items
    // 将升级信息合并回 stageGroups
    const versionMap = new Map(items.map((i) => [i.package_name, i]))
    for (const group of stageGroups.value) {
      for (const model of group.models) {
        for (const dep of model.dependencies) {
          const info = versionMap.get(dep.package_name)
          if (info) {
            dep.latest_version = info.latest_version
            dep.can_upgrade = info.can_upgrade
          }
        }
      }
    }
    return response
  }

  return {
    // 状态
    providers,
    accounts,
    stageConfigs,
    schemes,
    localModels,
    defaultSchemeId,
    loading,
    // 依赖管理状态
    dependencyGroups,
    dependenciesLoading,
    installingPackage,
    installBusy,
    // 阶段分组状态
    stageGroups,
    modelSummary,
    stageGroupsLoading,
    checkingModelKeys,
    downloadingModelKey,
    // 计算属性
    apiProviders,
    localProviders,
    stageConfigsByStage,
    defaultScheme,
    allDependencies,
    missingCount,
    upgradableCount,
    // 加载
    loadProviders,
    loadAccounts,
    loadStageConfigs,
    loadSchemes,
    loadLocalModels,
    loadAll,
    // 账户操作
    createAccount,
    updateAccount,
    deleteAccount,
    // 阶段配置操作
    createStageConfig,
    updateStageConfig,
    deleteStageConfig,
    // 方案操作
    createScheme,
    updateScheme,
    deleteScheme,
    setDefaultScheme,
    // 依赖管理操作
    loadStageGroups,
    refreshLocalModel,
    isModelChecking,
    isModelDownloading,
    downloadLocalModel,
    loadDependenciesStatus,
    installDependency,
    upgradeDependency,
    installAllMissing,
    checkUpgrade,
  }
})
