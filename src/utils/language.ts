/**
 * 语言代码与中文标签的映射工具。
 * 用于在页面上显示语言时，将代码（如 'en'、'zh'）转为中文标签（如 '英语'、'中文'）。
 */

const LANGUAGE_LABELS: Record<string, string> = {
  en: '英语',
  ja: '日语',
  ko: '韩语',
  zh: '中文',
}

/**
 * 将语言代码转为中文标签。未知代码原样返回。
 * @param code 语言代码，如 'en'、'ja'、'ko'、'zh'
 * @returns 中文标签，如 '英语'、'日语'、'韩语'、'中文'；空值返回 '-'
 */
export function languageLabel(code: string | null | undefined): string {
  if (!code) return '-'
  return LANGUAGE_LABELS[code] || code
}
