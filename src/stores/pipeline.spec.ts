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
})
