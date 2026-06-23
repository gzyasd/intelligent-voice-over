import client from './client'

export interface VenvInfo {
  name: string
  python_path: string | null
  exists: boolean
  custom_path: string | null
}

export interface VenvsResponse {
  venvs: VenvInfo[]
}

export default {
  /** 获取已解析的 venv Python 路径（只读诊断信息） */
  listVenvs(): Promise<VenvsResponse> {
    return client.get('/environment/venvs').then((r) => r.data)
  },
}
