import client from './client'

export interface HealthStatus {
  status: string
  version: string
  python_version: string
}

export default {
  /** 健康检查 */
  get(): Promise<HealthStatus> {
    return client.get('/health').then((r) => r.data)
  },
}
