import { BrowserWindow, Menu, session, shell } from 'electron'
import path from 'path'

const DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL

/**
 * 管理应用主窗口的创建与生命周期。
 */
export class WindowManager {
  private mainWindow: BrowserWindow | null = null

  async createMainWindow(pythonPort: number): Promise<BrowserWindow> {
    // 注入 CSP 响应头（仅注入一次）
    if (!session.defaultSession.webRequest.onHeadersReceived) {
      session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
        callback({
          responseHeaders: {
            ...details.responseHeaders,
            'Content-Security-Policy': [
              "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self' ws: wss: http://127.0.0.1:* http://localhost:*",
            ],
          },
        })
      })
    }

    const win = new BrowserWindow({
      width: 1280,
      height: 800,
      minWidth: 1024,
      minHeight: 680,
      show: false,
      webPreferences: {
        preload: path.join(__dirname, 'preload.js'),
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: true,
      },
    })

    this.mainWindow = win

    win.once('ready-to-show', () => {
      win.show()
    })

    // 窗口关闭时清理引用
    win.on('closed', () => {
      this.mainWindow = null
    })

    // 外部链接用系统浏览器打开；默认拒绝新窗口
    win.webContents.setWindowOpenHandler(({ url }) => {
      if (url.startsWith('http://') || url.startsWith('https://')) {
        shell.openExternal(url)
      }
      return { action: 'deny' }
    })

    // 右键菜单：打开开发者工具
    win.webContents.on('context-menu', () => {
      const menu = Menu.buildFromTemplate([
        {
          label: '打开开发者工具',
          click: () => {
            win.webContents.openDevTools()
          },
        },
        { type: 'separator' },
        {
          label: '刷新页面',
          click: () => {
            win.webContents.reload()
          },
        },
      ])
      menu.popup({ window: win })
    })

    // 注入 Python 服务端口到前端（仅首次加载触发，避免重复注册监听器）
    let readySent = false
    const sendReady = (): void => {
      if (readySent) return
      readySent = true
      win.webContents.send('python-service-ready', {
        port: pythonPort,
        baseUrl: `http://127.0.0.1:${pythonPort}`,
      })
    }
    win.webContents.once('did-finish-load', sendReady)

    if (DEV_SERVER_URL) {
      await win.loadURL(DEV_SERVER_URL)
    } else {
      await win.loadFile(path.join(__dirname, '..', 'dist', 'renderer', 'index.html'))
    }

    return win
  }
}
