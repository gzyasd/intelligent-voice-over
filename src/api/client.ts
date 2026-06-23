import axios, { type AxiosError, type AxiosInstance } from 'axios'

// 开发模式默认端口（与 electron/port-utils.ts PORT_RANGE_START 一致）
let apiBaseUrl = 'http://127.0.0.1:17000'

const client: AxiosInstance = axios.create({
  baseURL: 'http://127.0.0.1:17000',
  timeout: 30000,
})

// 响应拦截器：统一错误处理
client.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string }>) => {
    const detail = error.response?.data?.detail || error.message || '请求失败'
    return Promise.reject(new Error(detail))
  },
)

/** 设置后端 API 基地址 */
export function setApiBaseUrl(url: string): void {
  apiBaseUrl = url.replace(/\/$/, '')
  client.defaults.baseURL = apiBaseUrl
}

/** 获取当前 API 基地址 */
export function getApiBaseUrl(): string {
  return apiBaseUrl
}

export default client
