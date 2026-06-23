import client from './client'
import type { MirrorTestResult, PypiConnectionResult, UpdateSettingsRequest, UserSettings } from '@/types'

export default {
  /** 获取用户设置 */
  get(): Promise<UserSettings> {
    return client.get('/settings').then((r) => r.data)
  },
  /** 更新用户设置 */
  update(data: UpdateSettingsRequest): Promise<UserSettings> {
    return client.put('/settings', data).then((r) => r.data)
  },
  /** 测试当前 PyPI 镜像连通性 */
  testPypiConnection(): Promise<PypiConnectionResult> {
    return client.get('/settings/test-pypi-connection', { timeout: 10000 }).then((r) => r.data)
  },
  /** 测试所有 PyPI 镜像的连通性和延迟 */
  testMirrors(): Promise<{ results: MirrorTestResult[] }> {
    return client.get('/settings/test-mirrors', { timeout: 30000 }).then((r) => r.data)
  },
}
