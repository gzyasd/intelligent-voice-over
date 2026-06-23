import client from './client'
import type { DubbingSegment } from '@/types'

/** 用户可手动设置的片段状态（不含系统状态 running/failed） */
export type SegmentUserStatus = 'pending' | 'needs_review' | 'approved' | 'rendered'

export interface RegenerateSegmentRequest {
  target_text?: string
  speaker_id?: string
  emotion?: string
  style_prompt?: string
  speech_rate?: number
}

export interface RegenerateSegmentResult {
  segment: DubbingSegment
  audio_path: string | null
  duration_ms: number | null
}

export interface BatchUpdateRequest {
  segment_ids: string[]
  status: SegmentUserStatus
}

export interface UpdateSegmentChanges {
  target_text?: string
  speaker_id?: string
  emotion?: string | null
  style_prompt?: string | null
  status?: SegmentUserStatus
}

export const segmentsApi = {
  list(projectPath: string): Promise<DubbingSegment[]> {
    return client
      .get('/projects/segments', { params: { path: projectPath } })
      .then((r) => r.data)
  },
  update(
    projectPath: string,
    segmentId: string,
    changes: UpdateSegmentChanges,
  ): Promise<DubbingSegment> {
    return client
      .put(`/projects/segments/${segmentId}`, changes, { params: { path: projectPath } })
      .then((r) => r.data)
  },
  batchUpdateStatus(
    projectPath: string,
    req: BatchUpdateRequest,
  ): Promise<{ updated: number }> {
    return client
      .put('/projects/segments/batch/status', req, { params: { path: projectPath } })
      .then((r) => r.data)
  },
  regenerate(
    projectPath: string,
    segmentId: string,
    req: RegenerateSegmentRequest,
  ): Promise<RegenerateSegmentResult> {
    return client
      .post(`/projects/segments/${segmentId}/regenerate`, req, {
        params: { path: projectPath },
      })
      .then((r) => r.data)
  },
}

export default segmentsApi
