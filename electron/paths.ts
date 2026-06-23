import { app } from 'electron'
import fs from 'fs'
import path from 'path'

/**
 * 返回 Python 解释器/服务可执行文件路径。
 * - 生产模式：resourcesPath/python/ivo-server（Windows 下为 .exe）
 * - 开发模式：项目根目录下 .venv 的解释器（Windows 用 Scripts/python.exe，Unix 用 bin/python）
 *
 * 生产模式下会检查文件存在性，不存在时抛出友好错误。
 */
export function getPythonPath(): string {
  if (app.isPackaged) {
    const exeName = process.platform === 'win32' ? 'ivo-server.exe' : 'ivo-server'
    const pyPath = path.join(process.resourcesPath, 'python', exeName)
    if (!fs.existsSync(pyPath)) {
      throw new Error(
        `Python 服务可执行文件不存在: ${pyPath}\n安装可能已损坏，请重新安装应用。`,
      )
    }
    return pyPath
  }
  const venvDir = path.join(app.getAppPath(), '.venv')
  return process.platform === 'win32'
    ? path.join(venvDir, 'Scripts', 'python.exe')
    : path.join(venvDir, 'bin', 'python')
}

/**
 * 返回 FastAPI 服务入口 server/main.py 的路径。
 * - 生产模式：返回 null（PyInstaller 已打包为可执行文件，无需额外脚本路径）
 * - 开发模式：项目根目录下 server/main.py
 */
export function getServerPath(): string | null {
  if (app.isPackaged) {
    // 生产模式下，Python 可执行文件本身就是入口，不需要额外的脚本路径
    return null
  }
  return path.join(app.getAppPath(), 'server', 'main.py')
}
