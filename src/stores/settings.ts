import { defineStore } from 'pinia'
import { ref } from 'vue'
import settingsApi from '@/api/settings'
import { setApiBaseUrl as setClientBaseUrl } from '@/api/client'
import type { ThemeMode, UpdateSettingsRequest, UserSettings } from '@/types'

// 系统主题变化监听器（仅在 system 模式下生效）
let systemThemeMql: MediaQueryList | null = null
let systemThemeHandler: ((e: MediaQueryListEvent) => void) | null = null

export const useSettingsStore = defineStore('settings', () => {
  const apiBaseUrl = ref('')
  const userSettings = ref<UserSettings | null>(null)
  const isDark = ref(true)

  /** 加载设置 */
  async function load(): Promise<void> {
    const data = await settingsApi.get()
    userSettings.value = data
    applyTheme(data.theme)
  }

  /** 保存设置 */
  async function save(settings: UpdateSettingsRequest): Promise<void> {
    const data = await settingsApi.update(settings)
    userSettings.value = data
    applyTheme(data.theme)
  }

  /** 设置后端 API 基地址 */
  function setApiBaseUrl(url: string): void {
    apiBaseUrl.value = url
    setClientBaseUrl(url)
  }

  function applyTheme(theme: ThemeMode): void {
    // 清理之前的系统主题监听
    if (systemThemeMql && systemThemeHandler) {
      systemThemeMql.removeEventListener('change', systemThemeHandler)
      systemThemeMql = null
      systemThemeHandler = null
    }

    if (theme === 'dark') {
      isDark.value = true
    } else if (theme === 'light') {
      isDark.value = false
    } else {
      // system 模式：跟随系统主题，并监听变化
      const mql = window.matchMedia?.('(prefers-color-scheme: dark)')
      if (mql) {
        isDark.value = mql.matches
        systemThemeMql = mql
        systemThemeHandler = (e: MediaQueryListEvent) => {
          isDark.value = e.matches
        }
        mql.addEventListener('change', systemThemeHandler)
      } else {
        isDark.value = true
      }
    }
  }

  return { apiBaseUrl, userSettings, isDark, load, save, setApiBaseUrl }
})
