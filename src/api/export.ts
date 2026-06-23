import client from './client'

export interface ExportVideoRequest {
  project_path: string
  watermark_text: string | null
  accepted: boolean
}

export interface ExportAudioRequest {
  project_path: string
  format: 'wav' | 'mp3'
  accepted: boolean
}

export interface ExportResult {
  output_path: string
  segment_count: number
}

export const exportApi = {
  exportVideo(req: ExportVideoRequest): Promise<ExportResult> {
    return client.post('/export/video', req).then((r) => r.data)
  },
  exportAudio(req: ExportAudioRequest): Promise<ExportResult> {
    return client.post('/export/audio', req).then((r) => r.data)
  },
}

export default exportApi
