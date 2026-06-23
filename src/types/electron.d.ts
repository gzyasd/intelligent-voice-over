export interface IvoBridge {
  onPythonServiceReady: (callback: (apiBaseUrl: string) => void) => () => void
  onPythonServiceCrashed: (callback: () => void) => () => void
  getPythonServiceCurrent: () => Promise<{ port: number; baseUrl: string } | null>
  showOpenDialog: (filters?: Array<{ name: string; extensions: string[] }>) => Promise<string | null>
  showOpenDirectoryDialog: () => Promise<string | null>
  openInFolder: (path: string) => Promise<boolean>
  openPath: (path: string) => Promise<boolean>
}

declare global {
  interface Window {
    ivo?: IvoBridge
  }
}

export {}
