import client from './client'
import { getApiBaseUrl } from './client'

/** 流水线阶段名（含非模型阶段：import/audio_extract/export） */
export type PipelineStageName =
  | 'import'
  | 'audio_extract'
  | 'separation'
  | 'asr'
  | 'diarization'
  | 'translation'
  | 'tts'
  | 'export'
  | 'system'

export interface PipelineProgressEvent {
  event_id?: number
  stage: PipelineStageName
  stage_label: string
  status: 'started' | 'progress' | 'completed' | 'failed' | 'skipped'
  message: string
  overall_percent: number
  current_item: number | null
  total_items: number | null
  output_path: string | null
}

export interface PipelineFinishedEvent {
  type: 'finished'
  event_id?: number
  error: string | null
}

export interface PipelineErrorEvent {
  type: 'error'
  event_id?: number
  message: string
}

export interface PipelineCommandLogEvent {
  type: 'command_log'
  event_id?: number
  stage: PipelineStageName
  provider: string
  command: string[]
  stdout: string
  stderr: string
  exit_code: number
}

export type PipelineWsEvent =
  | PipelineProgressEvent
  | PipelineFinishedEvent
  | PipelineErrorEvent
  | PipelineCommandLogEvent

export interface PipelineStatus {
  running: boolean
  paused: boolean
  finished: boolean
  error: string | null
}

export interface PipelineHistoryStage {
  stage: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  message: string
}

export interface PipelineHistory {
  stages: PipelineHistoryStage[]
  current_stage: string | null
  has_history: boolean
  all_completed: boolean
  failed_stage: string | null
  error_message: string | null
}

export const pipelineApi = {
  start(projectPath: string): Promise<{ status: string; project_path: string }> {
    return client
      .post('/pipeline/start', null, { params: { project_path: projectPath } })
      .then((r) => r.data)
  },
  pause(projectPath: string): Promise<{ status: string }> {
    return client
      .post('/pipeline/pause', null, { params: { project_path: projectPath } })
      .then((r) => r.data)
  },
  resume(projectPath: string): Promise<{ status: string }> {
    return client
      .post('/pipeline/resume', null, { params: { project_path: projectPath } })
      .then((r) => r.data)
  },
  getStatus(projectPath: string): Promise<PipelineStatus> {
    return client
      .get('/pipeline/status', { params: { project_path: projectPath } })
      .then((r) => r.data)
  },
  getHistory(projectPath: string): Promise<PipelineHistory> {
    return client
      .get('/pipeline/history', { params: { project_path: projectPath }, timeout: 15000 })
      .then((r) => r.data)
  },
}

/** WebSocket 连接句柄，支持主动关闭（停止重连） */
export interface PipelineWebSocketHandle {
  close(): void
}

const MAX_RECONNECT_ATTEMPTS = 5
const RECONNECT_BASE_DELAY_MS = 1000

/** 创建 WebSocket 连接监听流水线进度（含指数退避重连，最多 5 次） */
export function createPipelineWebSocket(
  projectPath: string,
  onEvent: (event: PipelineWsEvent) => void,
  onClose?: () => void,
  onError?: (error: Event) => void,
): PipelineWebSocketHandle {
  const baseUrl = getApiBaseUrl()
  const wsBaseUrl = baseUrl.replace(/^http/, 'ws')

  let ws: WebSocket | null = null
  let closed = false
  let reconnectAttempts = 0
  let lastEventId = 0
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  const connect = (): void => {
    const url = `${wsBaseUrl}/pipeline/ws?project_path=${encodeURIComponent(projectPath)}&after_event_id=${lastEventId}`
    ws = new WebSocket(url)

    ws.onmessage = (e) => {
      // 收到消息说明连接正常，重置重连计数
      reconnectAttempts = 0
      try {
        const data = JSON.parse(e.data) as PipelineWsEvent
        if (data.event_id && data.event_id > lastEventId) {
          lastEventId = data.event_id
        }
        onEvent(data)
      } catch {
        // 忽略解析失败的消息
      }
    }

    ws.onclose = () => {
      ws = null
      if (closed) {
        onClose?.()
        return
      }
      // 意外关闭，尝试重连
      if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts++
        const delay = RECONNECT_BASE_DELAY_MS * Math.pow(2, reconnectAttempts - 1)
        reconnectTimer = setTimeout(connect, delay)
      } else {
        // 重连耗尽，通知关闭
        onClose?.()
      }
    }

    ws.onerror = (e) => {
      onError?.(e)
    }
  }

  connect()

  return {
    close(): void {
      closed = true
      if (reconnectTimer) {
        clearTimeout(reconnectTimer)
        reconnectTimer = null
      }
      if (ws) {
        ws.close()
        ws = null
      }
    },
  }
}
