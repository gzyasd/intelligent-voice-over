// 源语言与目标语言
export type SourceLanguage = 'en' | 'ja' | 'ko'
export type TargetLanguage = 'zh'

// 内容类型
export type ContentType = 'video' | 'audio'

// 片段状态
export type SegmentStatusValue =
  | 'pending'
  | 'running'
  | 'needs_review'
  | 'approved'
  | 'failed'
  | 'rendered'

// 项目生命周期
export type ProjectLifecycle =
  | 'unreadable'
  | 'not_started'
  | 'running'
  | 'paused'
  | 'interrupted'
  | 'incomplete'
  | 'failed'
  | 'completed'

// 项目主要操作
export type ProjectPrimaryAction = 'create' | 'start' | 'resume' | 'progress' | 'open_output'

// 主题模式
export type ThemeMode = 'light' | 'dark' | 'system'

// PyPI 镜像
export type PipMirrorKey = 'official' | 'tsinghua' | 'aliyun' | 'ustc'

// 配音片段
export interface DubbingSegment {
  id: string
  start_ms: number
  end_ms: number
  speaker_id: string
  source_language: SourceLanguage
  source_text: string
  target_language: TargetLanguage
  target_text: string
  emotion: string | null
  style_prompt: string | null
  status: SegmentStatusValue
  quality_flags: string[]
}

// 项目库条目
export interface ProjectLibraryItem {
  name: string
  path: string
  content_type: string
  source_media_path: string | null
  source_language: string
  target_language: string
  updated_at: number
  status: string
  status_detail: string
  lifecycle: ProjectLifecycle | ''
  failed_stage: string | null
  elapsed_seconds: number | null
  generation_started_at: number | null
  generation_completed_at: number | null
  generation_elapsed_seconds: number | null
  final_output_path: string | null
}

// 项目状态快照
export interface ProjectStatusSnapshot {
  project_path: string
  name: string
  content_type: string
  source_media_path: string | null
  source_language: string
  target_language: string
  lifecycle: ProjectLifecycle
  status_label: string
  status_detail: string
  primary_action: ProjectPrimaryAction
  elapsed_seconds: number | null
  generation_started_at: number | null
  generation_completed_at: number | null
  generation_elapsed_seconds: number | null
  final_output_path: string | null
  open_output_enabled: boolean
  updated_at: number
}

// 项目元数据（详情）
export interface ProjectMetadata {
  name: string
  source_language: SourceLanguage
  target_language: TargetLanguage
  content_type: ContentType
  source_media_path: string | null
  scheme_id: string | null
  source_video_path: string | null
  generation_status: string
  generation_started_at: number | null
  generation_completed_at: number | null
  generation_elapsed_seconds: number | null
}

// 用户设置
export interface UserSettings {
  models_dir: string
  projects_dir: string
  preferred_preset_id: string
  prefer_gpu: boolean
  lm_studio_base_url: string
  recent_projects: string[]
  theme: ThemeMode
  pip_mirror: PipMirrorKey
  custom_venv_python: string | null
  custom_pyannote_python: string | null
}

// 创建项目请求
export interface CreateProjectRequest {
  source_media_path: string
  name: string
  source_language: SourceLanguage
  target_language: TargetLanguage
  content_type: ContentType
  scheme_id?: string | null
}

// 更新设置请求
export type UpdateSettingsRequest = Partial<
  Pick<
    UserSettings,
    | 'models_dir'
    | 'projects_dir'
    | 'prefer_gpu'
    | 'lm_studio_base_url'
    | 'preferred_preset_id'
    | 'theme'
    | 'pip_mirror'
    | 'custom_venv_python'
    | 'custom_pyannote_python'
  >
>

// PyPI 镜像测试结果
export interface MirrorTestResult {
  key: string
  label: string
  url: string
  ok: boolean
  latency_ms: number
  status_code: number | null
  error: string | null
}

// PyPI 连通性测试结果
export interface PypiConnectionResult {
  ok: boolean
  latency_ms: number
  status_code: number | null
  url: string
  error: string | null
}

// 最近项目条目
export interface RecentProjectItem {
  path: string
}

// ============ 模型服务相关类型 ============

export type ProviderKind = 'api' | 'local'
export type StageName = 'separation' | 'asr' | 'diarization' | 'translation' | 'tts'

/** 供应商能力描述：某供应商在某阶段能产出什么 */
export interface ProviderCapability {
  stage: StageName
  output_keys: string[]
  can_merge_with: StageName[]
}

// 供应商注册表条目
export interface ConfigField {
  name: string
  display_name: string
  field_type: 'api_key' | 'text' | 'url' | 'select'
  required: boolean
  default: string | null
  placeholder: string | null
  options: string[] | null
  validation_pattern: string | null
}

export interface ProviderRegistryEntry {
  provider_id: string
  display_name: string
  supported_stages: string[]
  protocols: string[]
  capabilities: string[]
  requires_api_key: boolean
  requires_base_url: boolean
  default_base_url: string | null
  config_fields: ConfigField[]
  stage_config_fields: Record<string, ConfigField[]>
  implemented: boolean
  mvp_enabled: boolean
  scenario: string
  external_docs_url: string
}

// 供应商账户
export interface ProviderAccount {
  id: string
  display_name: string
  provider_key: string
  kind: ProviderKind
  enabled: boolean
  api_base_url: string
  api_key_ref: string | null
  auth_fields: Record<string, string>
  extra: Record<string, unknown>
  last_validation_status: string
  last_validation_message: string
}

export interface CreateAccountRequest {
  display_name: string
  provider_key: string
  kind: ProviderKind
  api_base_url?: string
  api_key?: string
  auth_fields?: Record<string, string>
  extra?: Record<string, unknown>
}

export interface UpdateAccountRequest {
  display_name?: string
  api_base_url?: string
  api_key?: string
  auth_fields?: Record<string, string>
  extra?: Record<string, unknown>
  enabled?: boolean
}

// 阶段配置
export interface StageProviderConfig {
  id: string
  display_name: string
  provider_key: string
  kind: ProviderKind
  stage: StageName
  protocol: string
  account_id: string | null
  capabilities: ProviderCapability[]
  model_name: string
  local_model_path: string
  device: string
  precision: string
  quality_preset: string
  upload_media_to_cloud: boolean
  extra: Record<string, unknown>
  last_validation_status: string
  last_validation_message: string
}

export interface CreateStageConfigRequest {
  display_name: string
  provider_key: string
  kind: ProviderKind
  stage: StageName
  protocol: string
  account_id?: string | null
  model_name?: string
  local_model_path?: string
  device?: string
  precision?: string
  quality_preset?: string
  upload_media_to_cloud?: boolean
  extra?: Record<string, unknown>
}

export interface UpdateStageConfigRequest {
  display_name?: string
  account_id?: string | null
  model_name?: string
  local_model_path?: string
  device?: string
  precision?: string
  quality_preset?: string
  upload_media_to_cloud?: boolean
  extra?: Record<string, unknown>
}

// 配音方案
export interface SchemeStageBinding {
  stage: StageName
  stage_config_id: string
  execution_group: string | null
  skip_when_execution_group_has_output: boolean
}

export interface DubbingScheme {
  id: string
  display_name: string
  description: string
  bindings: SchemeStageBinding[]
  prefer_gpu: boolean
  content_types: string[]
}

export interface CreateSchemeRequest {
  display_name: string
  description?: string
  bindings: SchemeStageBinding[]
  prefer_gpu?: boolean
  content_types?: string[]
}

export interface UpdateSchemeRequest {
  display_name?: string
  description?: string
  bindings?: SchemeStageBinding[]
  prefer_gpu?: boolean
  content_types?: string[]
}

// 本地模型
export interface LocalModelService {
  provider_key: string
  display_name: string
  stage: string
  model_dir_name: string
  model_path: string
  default_device: string
  supported_devices: string[]
  precision_options: string[]
  license_name: string
  license_url: string
  license_notes: string
  commercial_ok: boolean | null
  huggingface_repo: string
  source_url: string
  model_dir_exists: boolean
}

export interface LocalModelReadinessResult {
  provider_key: string
  stage: string
  status: 'ready' | 'missing' | 'warning'
  model_dir_exists: boolean
  missing_dependencies: string[]
  messages: string[]
}

export interface DependencyStatus {
  package_name: string
  import_name: string
  status: 'installed' | 'missing' | 'broken'
  version: string
  latest_version: string
  venv_name: string
  pip_install_hint: string
  can_upgrade?: boolean
  action_label?: string
  shared_by_count?: number
}

// 依赖管理：按服务分组的依赖状态
export interface ServiceDependencyGroup {
  provider_key: string
  display_name: string
  stage: string
  dependencies: DependencyStatus[]
}

// 安装/升级单个依赖的请求
export interface InstallDependencyRequest {
  package_name: string
  venv_name: string
  force_reinstall?: boolean
}

export interface UpgradeDependencyRequest {
  package_name: string
  venv_name: string
}

export type ModelDownloadSource = 'huggingface' | 'hf_mirror'

export interface DownloadLocalModelRequest {
  source: ModelDownloadSource
}

export interface DownloadLocalModelResponse {
  ok: boolean
  skipped: boolean
  provider_key: string
  repo_id: string
  source: ModelDownloadSource
  endpoint: string
  local_dir: string
  output: string
}

// 安装/升级单个依赖的响应
export interface InstallDependencyResponse {
  ok: boolean
  output: string
  package_name: string
}

// 一键安装缺失依赖的响应
export interface InstallAllMissingResponse {
  results: Array<{
    package_name: string
    ok: boolean
    output: string
  }>
  total: number
  succeeded: number
  failed: number
}

// 升级检查响应
export interface UpgradeCheckItem {
  package_name: string
  current_version: string
  latest_version: string
  can_upgrade: boolean
}

export interface UpgradeCheckResponse {
  items: UpgradeCheckItem[]
  checked: number
  failed: number
}

// ── 本地模型阶段分组（重构后） ──────────────────────────────────────────────

// 模型就绪状态
export interface LocalModelReadiness {
  status: 'ready' | 'missing_model' | 'missing_deps' | 'broken_deps'
  model_dir_exists: boolean
  missing_dependencies: string[]
  broken_dependencies: string[]
  messages: string[]
}

// 带依赖和就绪状态的模型卡片数据
export interface LocalModelCard extends LocalModelService {
  recommended: boolean
  tags: string[]
  readiness: LocalModelReadiness
  dependencies: DependencyStatus[]
}

// 阶段分组
export interface LocalModelStageGroup {
  stage: string
  display_name: string
  ready_count: number
  total_count: number
  models: LocalModelCard[]
}

// 顶部概览
export interface LocalModelSummary {
  total_models: number
  ready_models: number
  missing_models: number
  missing_deps_count: number
}

// 阶段分组响应
export interface LocalModelStageGroupsResponse {
  stages: LocalModelStageGroup[]
  summary: LocalModelSummary
}
