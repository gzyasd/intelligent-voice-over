import { app, BrowserWindow, dialog, ipcMain, shell } from 'electron'
import path from 'path'

const MEDIA_FILTERS = [
  { name: 'Videos', extensions: ['mp4', 'mkv', 'mov', 'avi', 'webm', 'flv'] },
  { name: 'Audio', extensions: ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'] },
  { name: 'All Files', extensions: ['*'] },
]

/**
 * 校验路径是否安全：
 * - 拒绝空路径
 * - 拒绝包含 .. 的路径遍历
 * - 必须是绝对路径
 * - 禁止打开系统目录（Windows、Program Files 等）下的文件
 */
function isSafePath(filePath: string): boolean {
  if (!filePath || typeof filePath !== 'string') return false
  if (filePath.includes('..')) return false
  if (!path.isAbsolute(filePath)) return false
  const resolved = path.resolve(filePath).toLowerCase()
  // 黑名单：禁止打开系统目录下的文件
  const forbidden: string[] = []
  if (process.env.WINDIR) forbidden.push(path.resolve(process.env.WINDIR).toLowerCase())
  if (process.env.ProgramFiles) forbidden.push(path.resolve(process.env.ProgramFiles).toLowerCase())
  if (process.env['ProgramFiles(x86)']) {
    forbidden.push(path.resolve(process.env['ProgramFiles(x86)']).toLowerCase())
  }
  if (process.env.ProgramData) forbidden.push(path.resolve(process.env.ProgramData).toLowerCase())
  // Windows 系统目录的常见兜底路径
  const fallbacks = ['C:\\Windows', 'C:\\Program Files', 'C:\\Program Files (x86)', 'C:\\ProgramData']
  for (const fb of fallbacks) {
    const p = path.resolve(fb).toLowerCase()
    if (!forbidden.includes(p)) forbidden.push(p)
  }
  for (const dir of forbidden) {
    if (resolved.startsWith(dir + path.sep.toLowerCase()) || resolved === dir) return false
  }
  return true
}

/**
 * 注册主进程 IPC 处理器，供 preload 暴露的 API 调用。
 */
export function setupIpcHandlers(mainWindow: BrowserWindow): void {
  // 重复注册保护
  const channels = ['dialog:openFile', 'dialog:openDirectory', 'shell:openInFolder', 'shell:openPath']
  for (const ch of channels) {
    ipcMain.removeHandler(ch)
  }

  ipcMain.handle(
    'dialog:openFile',
    async (_event, filters?: Array<{ name: string; extensions: string[] }>) => {
      const result = await dialog.showOpenDialog(mainWindow, {
        title: '选择文件',
        properties: ['openFile'],
        filters: filters && filters.length > 0 ? filters : MEDIA_FILTERS,
      })
      if (result.canceled || result.filePaths.length === 0) {
        return null
      }
      return result.filePaths[0]
    },
  )

  ipcMain.handle('dialog:openDirectory', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
      title: '选择目录',
      properties: ['openDirectory', 'createDirectory'],
    })
    if (result.canceled || result.filePaths.length === 0) {
      return null
    }
    return result.filePaths[0]
  })

  ipcMain.handle('shell:openInFolder', (_event, filePath: string) => {
    if (!isSafePath(filePath)) return false
    shell.showItemInFolder(filePath)
    return true
  })

  ipcMain.handle('shell:openPath', (_event, filePath: string) => {
    if (!isSafePath(filePath)) return false
    void shell.openPath(filePath)
    return true
  })
}
