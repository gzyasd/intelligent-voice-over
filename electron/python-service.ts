import { ChildProcess, spawn } from 'child_process'
import { app, BrowserWindow, dialog } from 'electron'
import fs from 'fs'
import http from 'http'
import path from 'path'
import { findAvailablePort } from './port-utils'
import { getPythonPath, getServerPath } from './paths'
import { logger } from './logger'

const PORT_RANGE_START = 17000
const PORT_RANGE_END = 17999
const HEALTH_CHECK_INTERVAL_MS = 500
const DEFAULT_HEALTH_CHECK_TIMEOUT_MS = 120000
const SHUTDOWN_GRACE_MS = 5000

function getHealthCheckTimeoutMs(): number {
  const configured = Number(process.env.IVO_PYTHON_HEALTH_TIMEOUT_MS)
  if (Number.isFinite(configured) && configured > 0) {
    return configured
  }
  return DEFAULT_HEALTH_CHECK_TIMEOUT_MS
}

/**
 * 管理 Python FastAPI (uvicorn) 子进程的生命周期：
 * 动态端口分配、健康检查轮询、优雅停止。
 */
export class PythonServiceManager {
  private process: ChildProcess | null = null
  private port: number | null = null
  private stopping = false
  private lastStdout = ''
  private lastStderr = ''

  async start(): Promise<number> {
    const port = await findAvailablePort(PORT_RANGE_START, PORT_RANGE_END)
    this.port = port
    this.stopping = false
    this.lastStdout = ''
    this.lastStderr = ''

    const pythonPath = getPythonPath()
    const serverPath = getServerPath()

    // 生产模式：serverPath 为 null，仅传端口参数
    // 开发模式：serverPath 为 server/main.py，传 [脚本路径, 端口]
    const args: string[] = serverPath ? [serverPath, String(port)] : [String(port)]

    const cwd = path.dirname(pythonPath)
    logger.info(
      `[python-service] spawning pythonPath=${pythonPath}, exists=${fs.existsSync(pythonPath)}, cwd=${cwd}`,
    )

    try {
      const env = {
        ...process.env,
        IVO_USER_DATA_DIR: app.getPath('userData'),
      }
      this.process = spawn(pythonPath, args, {
        cwd,
        env,
        windowsHide: true,
        stdio: ['ignore', 'pipe', 'pipe'],
      })

      // 窗口化应用没有可继承的 stdout/stderr，改为 pipe 后写入日志
      this.process.stdout?.on('data', (data: Buffer) => {
        const text = data.toString().trimEnd()
        this.lastStdout = text
        logger.info('[python-service stdout]', text)
      })
      this.process.stderr?.on('data', (data: Buffer) => {
        const text = data.toString().trimEnd()
        this.lastStderr = text
        logger.error('[python-service stderr]', text)
      })
    } catch (err) {
      throw new Error(
        `无法启动 Python 服务: ${err instanceof Error ? err.message : String(err)} (路径: ${pythonPath})`,
      )
    }

    // spawn 异步错误（如可执行文件不存在、无执行权限）
    this.process.on('error', (err) => {
      logger.error('[python-service] spawn error:', err)
      if (!this.stopping) {
        for (const win of BrowserWindow.getAllWindows()) {
          win.webContents.send('python-service-crashed')
        }
      }
      this.process = null
    })

    this.process.on('exit', (code, signal) => {
      logger.info(`[python-service] exited code=${code} signal=${signal}`)
      if (!this.stopping) {
        for (const win of BrowserWindow.getAllWindows()) {
          win.webContents.send('python-service-crashed')
        }
      }
      this.process = null
    })

    try {
      await this.waitForHealth(port)
    } catch (err) {
      // 健康检查失败时清理已 spawn 的进程
      await this.killProcess()
      throw err
    }
    return port
  }

  private waitForHealth(port: number): Promise<void> {
    return new Promise<void>((resolve, reject) => {
      const startTime = Date.now()
      const timeoutMs = getHealthCheckTimeoutMs()
      let settled = false

      // 监听进程意外退出，立即 reject（避免空等 30 秒）
      const onExit = (): void => {
        if (!settled && !this.stopping) {
          settled = true
          reject(new Error('Python 服务进程在启动期间退出'))
        }
      }
      if (this.process) {
        this.process.once('exit', onExit)
      }

      const cleanup = (): void => {
        if (this.process) {
          this.process.removeListener('exit', onExit)
        }
      }

      const check = (): void => {
        if (settled) return
        if (Date.now() - startTime > timeoutMs) {
          settled = true
          cleanup()
          const details = [
            `Python 服务健康检查超时（${timeoutMs}ms）`,
            this.lastStdout ? `最后 stdout: ${this.lastStdout}` : '',
            this.lastStderr ? `最后 stderr: ${this.lastStderr}` : '',
          ].filter(Boolean)
          reject(
            new Error(details.join('\n')),
          )
          return
        }

        const req = http.get(`http://127.0.0.1:${port}/health`, (res) => {
          res.resume()
          if (res.statusCode === 200) {
            settled = true
            cleanup()
            resolve()
          } else {
            setTimeout(check, HEALTH_CHECK_INTERVAL_MS)
          }
        })

        req.on('error', () => {
          if (!settled) {
            setTimeout(check, HEALTH_CHECK_INTERVAL_MS)
          }
        })

        // 单次请求超时，避免挂死
        req.setTimeout(5000, () => {
          req.destroy()
        })
      }

      check()
    })
  }

  async stop(): Promise<void> {
    const proc = this.process
    if (proc === null || this.stopping) {
      return
    }
    this.stopping = true
    await this.killProcess()
  }

  /** Python 服务是否仍在运行 */
  isRunning(): boolean {
    return this.process !== null && !this.stopping
  }

  /** 获取当前端口（供 macOS activate 重用窗口时使用） */
  getPort(): number | null {
    return this.port
  }

  private async killProcess(): Promise<void> {
    const proc = this.process
    if (proc === null) return

    return new Promise<void>((resolve) => {
      let resolved = false
      const finish = (): void => {
        if (!resolved) {
          resolved = true
          this.process = null
          resolve()
        }
      }

      proc.once('exit', finish)

      if (process.platform === 'win32' && proc.pid !== undefined) {
        // Windows：用 taskkill 终止整个进程树（/T 递归子进程，/F 强制）
        // 避免 Python 服务 spawn 的子进程（FFmpeg 等）变成孤儿进程
        const taskkill = spawn('taskkill', ['/PID', String(proc.pid), '/T', '/F'], {
          windowsHide: true,
        })
        taskkill.on('exit', () => finish())
        taskkill.on('error', () => {
          // taskkill 失败，回退到 proc.kill
          try {
            proc.kill()
          } catch {
            // 进程可能已退出
          }
          finish()
        })
      } else {
        // Unix：SIGTERM 优雅停止，超时后 SIGKILL
        try {
          proc.kill('SIGTERM')
        } catch {
          finish()
          return
        }
        setTimeout(() => {
          if (!resolved) {
            try {
              proc.kill('SIGKILL')
            } catch {
              // 进程可能已退出，忽略
            }
            finish()
          }
        }, SHUTDOWN_GRACE_MS)
      }
    })
  }

  /** 显示启动失败对话框（供 main.ts 调用） */
  static showStartupError(message: string): void {
    dialog.showErrorBox(
      'IVO 启动失败',
      `Python 服务启动失败，应用无法继续运行。\n\n${message}\n\n请检查安装完整性或联系支持。`,
    )
  }
}
