import client from './client'
import type {
  ProviderRegistryEntry,
  ProviderAccount,
  CreateAccountRequest,
  UpdateAccountRequest,
  StageProviderConfig,
  CreateStageConfigRequest,
  UpdateStageConfigRequest,
  DubbingScheme,
  CreateSchemeRequest,
  UpdateSchemeRequest,
  LocalModelService,
  ServiceDependencyGroup,
  DownloadLocalModelRequest,
  DownloadLocalModelResponse,
  InstallDependencyRequest,
  UpgradeDependencyRequest,
  InstallDependencyResponse,
  InstallAllMissingResponse,
  UpgradeCheckResponse,
  LocalModelCard,
  LocalModelStageGroupsResponse,
} from '@/types'

// ============ 供应商注册表 ============

export const providersApi = {
  list(): Promise<ProviderRegistryEntry[]> {
    return client.get('/providers').then((r) => r.data)
  },
}

// ============ 供应商账户 ============

export const accountsApi = {
  list(): Promise<ProviderAccount[]> {
    return client.get('/accounts').then((r) => r.data)
  },
  create(req: CreateAccountRequest): Promise<ProviderAccount> {
    return client.post('/accounts', req).then((r) => r.data)
  },
  update(accountId: string, req: UpdateAccountRequest): Promise<ProviderAccount> {
    return client.put(`/accounts/${accountId}`, req).then((r) => r.data)
  },
  delete(accountId: string): Promise<{ deleted: boolean }> {
    return client.delete(`/accounts/${accountId}`).then((r) => r.data)
  },
}

// ============ 阶段配置 ============

export const stageConfigsApi = {
  list(): Promise<StageProviderConfig[]> {
    return client.get('/stage-configs').then((r) => r.data)
  },
  create(req: CreateStageConfigRequest): Promise<StageProviderConfig> {
    return client.post('/stage-configs', req).then((r) => r.data)
  },
  update(configId: string, req: UpdateStageConfigRequest): Promise<StageProviderConfig> {
    return client.put(`/stage-configs/${configId}`, req).then((r) => r.data)
  },
  delete(configId: string): Promise<{ deleted: boolean }> {
    return client.delete(`/stage-configs/${configId}`).then((r) => r.data)
  },
}

// ============ 配音方案 ============

export const schemesApi = {
  list(): Promise<DubbingScheme[]> {
    return client.get('/schemes').then((r) => r.data)
  },
  create(req: CreateSchemeRequest): Promise<DubbingScheme> {
    return client.post('/schemes', req).then((r) => r.data)
  },
  update(schemeId: string, req: UpdateSchemeRequest): Promise<DubbingScheme> {
    return client.put(`/schemes/${schemeId}`, req).then((r) => r.data)
  },
  delete(schemeId: string): Promise<{ deleted: boolean }> {
    return client.delete(`/schemes/${schemeId}`).then((r) => r.data)
  },
  getDefault(): Promise<{ scheme_id: string | null }> {
    return client.get('/schemes/default-scheme').then((r) => r.data)
  },
  setDefault(schemeId: string): Promise<{ scheme_id: string }> {
    return client.put('/schemes/default-scheme', { scheme_id: schemeId }).then((r) => r.data)
  },
}

// ============ 本地模型 ============

export const localModelsApi = {
  list(): Promise<LocalModelService[]> {
    return client.get('/local-models', { timeout: 10000 }).then((r) => r.data)
  },

  // 阶段分组（重构后主用）—— 依赖检查可能较慢，给 60 秒
  stageGroups(): Promise<LocalModelStageGroupsResponse> {
    return client.get('/local-models/stage-groups', { timeout: 60000 }).then((r) => r.data)
  },
  status(providerKey: string): Promise<LocalModelCard> {
    return client.get(`/local-models/${providerKey}/status`, { timeout: 60000 }).then((r) => r.data)
  },
  download(
    providerKey: string,
    req: DownloadLocalModelRequest,
  ): Promise<DownloadLocalModelResponse> {
    return client.post(`/local-models/${providerKey}/download`, req, { timeout: 3600000 })
      .then((r) => r.data)
  },

  // 依赖管理
  allDependenciesStatus(): Promise<ServiceDependencyGroup[]> {
    return client.get('/local-models/dependencies/all-status', { timeout: 60000 }).then((r) => r.data)
  },
  // pip install 大包可能要几分钟，给 10 分钟（与后端 600s 对齐）
  installDependency(req: InstallDependencyRequest): Promise<InstallDependencyResponse> {
    return client.post('/local-models/dependencies/install', req, { timeout: 600000 }).then((r) => r.data)
  },
  upgradeDependency(req: UpgradeDependencyRequest): Promise<InstallDependencyResponse> {
    return client.post('/local-models/dependencies/upgrade', req, { timeout: 600000 }).then((r) => r.data)
  },
  installAllMissing(): Promise<InstallAllMissingResponse> {
    return client.post('/local-models/dependencies/install-all-missing', null, { timeout: 600000 }).then((r) => r.data)
  },
  // PyPI 升级检查是网络请求，给 60 秒
  upgradeCheck(): Promise<UpgradeCheckResponse> {
    return client.get('/local-models/dependencies/upgrade-check', { timeout: 60000 }).then((r) => r.data)
  },
}

export default {
  providers: providersApi,
  accounts: accountsApi,
  stageConfigs: stageConfigsApi,
  schemes: schemesApi,
  localModels: localModelsApi,
}
