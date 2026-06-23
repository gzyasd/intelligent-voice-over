import { app, BrowserWindow, ipcMain } from 'electron'
import { PythonServiceManager } from './python-service'
import { WindowManager } from './window-manager'
import { setupIpcHandlers } from './ipc-handlers'

const pythonService = new PythonServiceManager()
const windowManager = new WindowManager()

ipcMain.handle('python-service:get-current', () => {
  const port = pythonService.getPort()
  if (port === null || !pythonService.isRunning()) {
    return null
  }
  return {
    port,
    baseUrl: `http://127.0.0.1:${port}`,
  }
})

// 全局未捕获异常处理，避免静默崩溃
process.on('uncaughtException', (err) => {
  console.error('[main] uncaughtException:', err)
})

process.on('unhandledRejection', (reason) => {
  console.error('[main] unhandledRejection:', reason)
})

app.whenReady().then(async () => {
  try {
    const port = await pythonService.start()
    const win = await windowManager.createMainWindow(port)
    setupIpcHandlers(win)
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    console.error('[main] 启动失败:', message)
    PythonServiceManager.showStartupError(message)
    app.quit()
  }
})

app.on('window-all-closed', async () => {
  await pythonService.stop()
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', async (event) => {
  // 阻止立即退出，等 Python 服务清理完成
  if (!pythonService.isRunning()) {
    return
  }
  event.preventDefault()
  await pythonService.stop()
  app.exit()
})

// macOS：点击 Dock 图标时重新创建窗口
app.on('activate', async () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    try {
      const port = pythonService.getPort()
      if (port === null) {
        // Python 服务已停止，重启
        const newPort = await pythonService.start()
        const win = await windowManager.createMainWindow(newPort)
        setupIpcHandlers(win)
      } else {
        const win = await windowManager.createMainWindow(port)
        setupIpcHandlers(win)
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      PythonServiceManager.showStartupError(message)
      app.quit()
    }
  }
})
