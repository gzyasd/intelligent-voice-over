import { app } from 'electron'
import fs from 'fs'
import path from 'path'

let logStream: fs.WriteStream | null = null

/** 初始化日志文件流，写入 app.getPath('logs')/ivo-electron.log */
function getLogStream(): fs.WriteStream {
  if (logStream) return logStream
  const logsDir = app.getPath('logs')
  if (!fs.existsSync(logsDir)) {
    fs.mkdirSync(logsDir, { recursive: true })
  }
  const logFile = path.join(logsDir, 'ivo-electron.log')
  logStream = fs.createWriteStream(logFile, { flags: 'a' })
  return logStream
}

function formatMessage(level: string, msg: unknown): string {
  const timestamp = new Date().toISOString()
  const text = msg instanceof Error ? msg.stack || msg.message : String(msg)
  return `[${timestamp}] [${level}] ${text}\n`
}

export const logger = {
  info(...args: unknown[]): void {
    const msg = args.map((a) => (typeof a === 'string' ? a : JSON.stringify(a))).join(' ')
    console.log(msg)
    try {
      getLogStream().write(formatMessage('INFO', msg))
    } catch {
      // 日志写入失败不影响主流程
    }
  },
  error(...args: unknown[]): void {
    const msg = args.map((a) => (typeof a === 'string' ? a : JSON.stringify(a))).join(' ')
    console.error(msg)
    try {
      getLogStream().write(formatMessage('ERROR', msg))
    } catch {
      // 日志写入失败不影响主流程
    }
  },
}
