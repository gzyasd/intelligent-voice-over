import { defineStore } from 'pinia'
import { ref } from 'vue'
import projectsApi from '@/api/projects'
import type { ProjectLibraryItem, ProjectStatusSnapshot } from '@/types'

export const useProjectStore = defineStore('project', () => {
  const library = ref<ProjectLibraryItem[]>([])
  const currentProjectPath = ref<string>('')
  const currentSnapshot = ref<ProjectStatusSnapshot | null>(null)

  /** 刷新项目库 */
  async function refreshLibrary(): Promise<void> {
    library.value = await projectsApi.list()
  }

  /** 加载项目（设置当前路径并拉取状态快照） */
  async function loadProject(path: string): Promise<void> {
    currentProjectPath.value = path
    await refreshCurrent()
  }

  /** 刷新当前项目状态快照 */
  async function refreshCurrent(): Promise<void> {
    if (!currentProjectPath.value) {
      currentSnapshot.value = null
      return
    }
    currentSnapshot.value = await projectsApi.getStatus(currentProjectPath.value)
  }

  return {
    library,
    currentProjectPath,
    currentSnapshot,
    refreshLibrary,
    loadProject,
    refreshCurrent,
  }
})
