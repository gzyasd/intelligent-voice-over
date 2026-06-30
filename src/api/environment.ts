import client, { getApiBaseUrl } from './client'

export interface VenvInfo {
  name: string
  python_path: string | null
  exists: boolean
  custom_path: string | null
}

export interface VenvsResponse {
  venvs: VenvInfo[]
}

export interface SetupVenvEvent {
  step: string
  status: 'running' | 'done' | 'error' | 'log'
  message: string
}

export type SetupVenvCallback = (event: SetupVenvEvent) => void

export default {
  /** 获取已解析的 venv Python 路径（只读诊断信息） */
  listVenvs(): Promise<VenvsResponse> {
    return client.get('/environment/venvs').then((r) => r.data)
  },

  /**
   * 自动创建 .venv 和 .venv-pyannote（SSE 流式推送进度）。
   * 使用 fetch 消费 text/event-stream，通过 callback 实时返回事件。
   * 返回一个 AbortController 供前端取消请求。
   */
  setupVenv(
    mirror: string,
    onEvent: SetupVenvCallback,
    signal?: AbortSignal,
  ): AbortController {
    const controller = new AbortController()
    const mergedSignal = signal ?? controller.signal

    const baseUrl = getApiBaseUrl()
    const url = `${baseUrl}/environment/setup-venv`

    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mirror }),
      signal: mergedSignal,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }
        const reader = response.body?.getReader()
        if (!reader) return
        const decoder = new TextDecoder()
        let buffer = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const event = JSON.parse(line.slice(6)) as SetupVenvEvent
                onEvent(event)
              } catch {
                // 忽略解析失败的行
              }
            }
          }
        }
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          onEvent({
            step: 'error',
            status: 'error',
            message: err instanceof Error ? err.message : String(err),
          })
        }
      })

    return controller
  },
}
