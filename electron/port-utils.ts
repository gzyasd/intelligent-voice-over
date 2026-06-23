import net from 'net'

/**
 * 在 [start, end] 范围内查找一个可用的本地端口。
 * 通过尝试创建 TCP server 来检测端口可用性。
 */
export function findAvailablePort(start: number, end: number): Promise<number> {
  return new Promise<number>((resolve, reject) => {
    const tryPort = (port: number): void => {
      if (port > end) {
        reject(new Error(`No available port found in range ${start}-${end}`))
        return
      }

      const server = net.createServer()
      server.unref()

      server.on('error', () => {
        tryPort(port + 1)
      })

      server.listen(port, '127.0.0.1', () => {
        server.close(() => resolve(port))
      })
    }

    tryPort(start)
  })
}
