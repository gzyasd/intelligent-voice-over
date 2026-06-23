import { contextBridge, ipcRenderer, type IpcRendererEvent } from 'electron'

type ReadyCallback = (apiBaseUrl: string) => void
type CrashedCallback = () => void
type PythonServiceInfo = { port: number; baseUrl: string }

/**
 * 注册监听器并返回取消订阅函数，避免内存泄漏。
 */
contextBridge.exposeInMainWorld('ivo', {
  onPythonServiceReady: (callback: ReadyCallback): (() => void) => {
    const handler = (_event: IpcRendererEvent, info: { port: number; baseUrl: string }): void => {
      callback(info.baseUrl)
    }
    ipcRenderer.on('python-service-ready', handler)
    return () => {
      ipcRenderer.removeListener('python-service-ready', handler)
    }
  },
  onPythonServiceCrashed: (callback: CrashedCallback): (() => void) => {
    const handler = (): void => callback()
    ipcRenderer.on('python-service-crashed', handler)
    return () => {
      ipcRenderer.removeListener('python-service-crashed', handler)
    }
  },
  getPythonServiceCurrent: (): Promise<PythonServiceInfo | null> =>
    ipcRenderer.invoke('python-service:get-current'),
  showOpenDialog: (
    filters?: Array<{ name: string; extensions: string[] }>,
  ): Promise<string | null> => ipcRenderer.invoke('dialog:openFile', filters),
  showOpenDirectoryDialog: (): Promise<string | null> =>
    ipcRenderer.invoke('dialog:openDirectory'),
  openInFolder: (path: string): Promise<boolean> => ipcRenderer.invoke('shell:openInFolder', path),
  openPath: (path: string): Promise<boolean> => ipcRenderer.invoke('shell:openPath', path),
})
