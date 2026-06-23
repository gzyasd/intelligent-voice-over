import client from './client'
import type {
  CreateProjectRequest,
  ProjectLibraryItem,
  ProjectMetadata,
  ProjectStatusSnapshot,
} from '@/types'

export default {
  /** 列出项目库 */
  list(): Promise<ProjectLibraryItem[]> {
    return client.get('/projects').then((r) => r.data)
  },
  /** 创建项目 */
  create(data: CreateProjectRequest): Promise<ProjectMetadata> {
    return client.post('/projects', data).then((r) => r.data)
  },
  /** 获取项目状态快照 */
  getStatus(path: string): Promise<ProjectStatusSnapshot> {
    return client.get('/projects/status', { params: { path } }).then((r) => r.data)
  },
  /** 删除项目（整个文件夹） */
  delete(path: string): Promise<{ deleted: boolean }> {
    return client.delete('/projects', { params: { path } }).then((r) => r.data)
  },
}
