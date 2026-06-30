import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const mocks = vi.hoisted(() => ({
  getStatus: vi.fn(),
  getHistory: vi.fn(),
  createPipelineWebSocket: vi.fn(() => ({ close: vi.fn() })),
}))

vi.mock('@/api/pipeline', () => ({
  pipelineApi: {
    start: vi.fn(),
    pause: vi.fn(),
    resume: vi.fn(),
    getStatus: mocks.getStatus,
    getHistory: mocks.getHistory,
  },
  createPipelineWebSocket: mocks.createPipelineWebSocket,
}))

import { usePipelineStore } from '@/stores/pipeline'

describe('pipeline runtime synchronization', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('preserves same-project logs while reconnecting to a running backend job', async () => {
    const store = usePipelineStore()
    store.setProject('D:/runs/test.ivoproj')
    store.logs.push({
      timestamp: 1,
      level: 'info',
      stage: 'tts',
      stageLabel: '生成配音',
      message: 'existing log',
    })
    mocks.getStatus.mockResolvedValue({
      running: true,
      paused: false,
      finished: false,
      error: null,
    })

    await store.synchronizeWithBackend('D:/runs/test.ivoproj')

    expect(store.logs).toHaveLength(1)
    expect(store.logs[0].message).toBe('existing log')
    expect(store.running).toBe(true)
    expect(store.paused).toBe(false)
    expect(mocks.createPipelineWebSocket).toHaveBeenCalledTimes(1)
    expect(mocks.getHistory).not.toHaveBeenCalled()
  })

  it('restores paused state without treating navigation as an interruption', async () => {
    const store = usePipelineStore()
    mocks.getStatus.mockResolvedValue({
      running: true,
      paused: true,
      finished: false,
      error: null,
    })

    await store.synchronizeWithBackend('D:/runs/test.ivoproj')

    expect(store.running).toBe(true)
    expect(store.paused).toBe(true)
    expect(store.canResume).toBe(true)
    expect(store.canPause).toBe(false)
  })

  it('falls back to job history when there is no live backend runner', async () => {
    const store = usePipelineStore()
    mocks.getStatus.mockResolvedValue({
      running: false,
      paused: false,
      finished: false,
      error: null,
    })
    mocks.getHistory.mockResolvedValue({
      stages: [],
      current_stage: null,
      has_history: false,
      all_completed: false,
      failed_stage: null,
      error_message: null,
    })

    await store.synchronizeWithBackend('D:/runs/test.ivoproj')

    expect(mocks.getHistory).toHaveBeenCalledWith('D:/runs/test.ivoproj')
  })

  it('exposes current stage elapsed seconds when a stage is running', () => {
    const store = usePipelineStore()
    store.currentStage = 'tts'
    store.stages = [
      {
        name: 'tts',
        label: '生成配音',
        status: 'running',
        message: '',
        startedAt: 1000,
        completedAt: null,
        elapsedSeconds: 42,
      },
    ]

    expect(store.currentStageElapsedSeconds).toBe(42)
  })

  it('keeps project total elapsed separate from stage progress elapsed', () => {
    const store = usePipelineStore()
    store.setProject('D:/runs/test.ivoproj')
    store.elapsedSeconds = 120
    store.attach()
    const calls = mocks.createPipelineWebSocket.mock.calls as unknown as Array<
      [string, (event: unknown) => void]
    >
    const onEvent = calls[0]?.[1]
    expect(onEvent).toBeDefined()

    onEvent?.({
      event_id: 1,
      stage: 'tts',
      stage_label: '生成配音',
      status: 'started',
      message: 'started',
      overall_percent: 70,
      output_path: null,
      started_at: 1000,
      elapsed_seconds: 0,
    })

    onEvent?.({
      event_id: 2,
      stage: 'tts',
      stage_label: '生成配音',
      status: 'progress',
      message: '正在生成第 1 / 10 句：seg-001',
      overall_percent: 75,
      current_item: 1,
      total_items: 10,
      output_path: null,
      started_at: 1000,
      elapsed_seconds: 3,
    })

    expect(store.elapsedSeconds).toBe(120)
    expect(store.stages.find((stage) => stage.name === 'tts')?.elapsedSeconds).toBe(0)
  })

  it('returns null for current stage elapsed seconds when no stage is running', () => {
    const store = usePipelineStore()
    store.currentStage = ''
    store.stages = []

    expect(store.currentStageElapsedSeconds).toBeNull()
  })
})
