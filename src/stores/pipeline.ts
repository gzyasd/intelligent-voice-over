import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  pipelineApi,
  createPipelineWebSocket,
  type PipelineProgressEvent,
  type PipelineWsEvent,
  type PipelineWebSocketHandle,
  type PipelineHistory,
} from '@/api/pipeline'

export interface LogEntry {
  timestamp: number
  level: 'info' | 'warning' | 'error' | 'progress'
  stage: string
  stageLabel: string
  message: string
}

export interface StageState {
  name: string
  label: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  message: string
}

const STAGE_ORDER = [
  'import',
  'audio_extract',
  'separation',
  'asr',
  'diarization',
  'translation',
  'tts',
  'export',
] as const

const STAGE_LABELS: Record<string, string> = {
  import: '导入素材',
  audio_extract: '提取音频',
  separation: '分离人声/背景',
  asr: '识别字幕',
  diarization: '识别角色',
  translation: '翻译改写',
  tts: '生成配音',
  export: '合成输出',
}

export const usePipelineStore = defineStore('pipeline', () => {
  const projectPath = ref<string>('')
  const running = ref(false)
  const paused = ref(false)
  const finished = ref(false)
  const error = ref<string | null>(null)
  const overallPercent = ref(0)
  const stages = ref<StageState[]>(
    STAGE_ORDER.map((name) => ({
      name,
      label: STAGE_LABELS[name],
      status: 'pending',
      message: '',
    })),
  )
  const logs = ref<LogEntry[]>([])
  const currentStage = ref<string>('')
  // 是否已从后端恢复历史进度（用于打开失败/中断项目时显示已有阶段状态）
  const hasHistory = ref(false)
  const lastEventId = ref(0)

  let ws: PipelineWebSocketHandle | null = null

  const isRunning = computed(() => running.value && !finished.value)
  const canPause = computed(() => isRunning.value && !paused.value)
  const canResume = computed(() => isRunning.value && paused.value)

  function setProject(path: string): void {
    // 路径未变时不重置，避免切换菜单回来后生成进度消失
    if (projectPath.value === path) return
    projectPath.value = path
    reset()
  }

  function reset(): void {
    closeWs()
    running.value = false
    paused.value = false
    finished.value = false
    error.value = null
    overallPercent.value = 0
    currentStage.value = ''
    hasHistory.value = false
    lastEventId.value = 0
    stages.value = STAGE_ORDER.map((name) => ({
      name,
      label: STAGE_LABELS[name],
      status: 'pending',
      message: '',
    }))
    logs.value = []
  }

  function handleEvent(event: PipelineWsEvent): void {
    if (event.event_id && event.event_id <= lastEventId.value) return
    if (event.event_id) lastEventId.value = event.event_id

    if ('type' in event) {
      if (event.type === 'finished') {
        finished.value = true
        running.value = false
        error.value = event.error
        addLog('info', 'system', '系统', event.error ? `流水线结束（错误）: ${event.error}` : '流水线执行完成')
        closeWs()
      } else if (event.type === 'error') {
        addLog('error', 'system', '系统', event.message)
      } else if (event.type === 'command_log') {
        const commandText = event.command.join(' ')
        if (event.exit_code === -1) {
          addLog('info', event.stage, event.provider, `执行命令：${commandText}`)
        } else {
          const output = [event.stdout.trim(), event.stderr.trim()].filter(Boolean).join('\n')
          const message = output || `命令执行结束，退出码 ${event.exit_code}`
          addLog(event.exit_code === 0 ? 'info' : 'error', event.stage, event.provider, message)
        }
      }
      return
    }

    // 进度事件
    const evt = event as PipelineProgressEvent
    overallPercent.value = evt.overall_percent
    currentStage.value = evt.stage

    // 更新阶段状态
    const stageIdx = STAGE_ORDER.indexOf(evt.stage as (typeof STAGE_ORDER)[number])
    if (stageIdx >= 0) {
      const stage = stages.value[stageIdx]
      if (evt.status === 'started') {
        stage.status = 'running'
        stage.message = evt.message || '开始执行'
      } else if (evt.status === 'progress') {
        stage.status = 'running'
        stage.message = evt.message
      } else if (evt.status === 'completed') {
        stage.status = 'completed'
        stage.message = evt.message || '已完成'
      } else if (evt.status === 'failed') {
        stage.status = 'failed'
        stage.message = evt.message || '失败'
      } else if (evt.status === 'skipped') {
        stage.status = 'skipped'
        stage.message = evt.message || '已跳过'
      }
    }

    // 日志分类
    const level = classifyLog(evt)
    addLog(level, evt.stage, evt.stage_label, evt.message)
  }

  function classifyLog(evt: PipelineProgressEvent): LogEntry['level'] {
    if (evt.status === 'failed') return 'error'
    if (evt.status === 'skipped') return 'warning'
    if (evt.status === 'progress') return 'progress'
    return 'info'
  }

  function addLog(
    level: LogEntry['level'],
    stage: string,
    stageLabel: string,
    message: string,
  ): void {
    logs.value.push({
      timestamp: Date.now(),
      level,
      stage,
      stageLabel,
      message,
    })
    if (logs.value.length > 1000) {
      logs.value = logs.value.slice(-1000)
    }
  }

  function openWs(): void {
    if (ws) closeWs()
    ws = createPipelineWebSocket(
      projectPath.value,
      handleEvent,
      () => {
        ws = null
      },
      () => {
        addLog('error', 'system', '系统', 'WebSocket 连接错误')
      },
    )
  }

  function closeWs(): void {
    if (ws) {
      ws.close()
      ws = null
    }
  }

  /**
   * 从后端 JobStore 恢复历史进度。
   * 用于打开项目时显示已有阶段状态（失败/中断/已完成但未在前端会话中）。
   * 不打开 WebSocket，不设置 running 状态。
   */
  async function restoreFromBackend(path: string): Promise<void> {
    if (!path) return
    projectPath.value = path
    // 先重置，避免残留旧状态
    closeWs()
    running.value = false
    paused.value = false
    finished.value = false
    error.value = null
    overallPercent.value = 0
    currentStage.value = ''
    hasHistory.value = false
    lastEventId.value = 0
    stages.value = STAGE_ORDER.map((name) => ({
      name,
      label: STAGE_LABELS[name],
      status: 'pending',
      message: '',
    }))
    logs.value = []

    try {
      const history: PipelineHistory = await pipelineApi.getHistory(path)
      if (!history.has_history) {
        return
      }

      // 按后端返回更新阶段状态
      const stageMap = new Map<string, { status: string; message: string }>()
      for (const s of history.stages) {
        stageMap.set(s.stage, { status: s.status, message: s.message })
      }
      stages.value = STAGE_ORDER.map((name) => {
        const rec = stageMap.get(name)
        return {
          name,
          label: STAGE_LABELS[name],
          status: (rec?.status as StageState['status']) || 'pending',
          message: rec?.message || '',
        }
      })

      // 计算总进度百分比
      const completedCount = stages.value.filter(
        (s) => s.status === 'completed' || s.status === 'skipped',
      ).length
      overallPercent.value = Math.round((completedCount / STAGE_ORDER.length) * 100)

      if (history.current_stage) {
        currentStage.value = history.current_stage
      }
      if (history.failed_stage) {
        error.value = history.error_message || '流水线执行失败'
      }
      if (history.all_completed) {
        finished.value = true
        overallPercent.value = 100
      }
      hasHistory.value = true
    } catch {
      // 恢复失败时静默处理，不影响页面其他功能
      hasHistory.value = false
    }
  }

  /**
   * 以后端 runner 为事实源同步当前项目。
   * 活跃任务只补连 WebSocket，不清空同项目已有日志；无活跃 runner 时才从 JobStore 恢复。
   */
  async function synchronizeWithBackend(path: string): Promise<void> {
    if (!path) return
    setProject(path)
    const status = await pipelineApi.getStatus(path)

    if (status.running) {
      running.value = true
      paused.value = status.paused
      finished.value = false
      error.value = status.error
      if (!ws) {
        openWs()
      }
      return
    }

    if (status.finished) {
      running.value = false
      paused.value = false
      finished.value = true
      error.value = status.error
      if (logs.value.length > 0 || hasHistory.value) {
        return
      }
    }

    await restoreFromBackend(path)
  }

  function attach(): void {
    if (!projectPath.value) throw new Error('Project path is not set')
    running.value = true
    finished.value = false
    if (!ws) {
      openWs()
    }
  }

  async function start(): Promise<void> {
    if (!projectPath.value) throw new Error('未设置项目路径')
    reset()
    running.value = true
    try {
      await pipelineApi.start(projectPath.value)
      openWs()
    } catch (err) {
      running.value = false
      closeWs()
      throw err
    }
  }

  async function pause(): Promise<void> {
    await pipelineApi.pause(projectPath.value)
    paused.value = true
  }

  async function resume(): Promise<void> {
    await pipelineApi.resume(projectPath.value)
    paused.value = false
  }

  return {
    // 状态
    projectPath,
    running,
    paused,
    finished,
    error,
    overallPercent,
    stages,
    logs,
    currentStage,
    hasHistory,
    // 计算属性
    isRunning,
    canPause,
    canResume,
    // 方法
    setProject,
    reset,
    attach,
    start,
    pause,
    resume,
    restoreFromBackend,
    synchronizeWithBackend,
  }
})
