import { createInstance } from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './locales/en.json'
import ja from './locales/ja.json'
import ko from './locales/ko.json'

const i18n = createInstance()

export const locales = ['en', 'ja', 'ko'] as const
export type Locale = typeof locales[number]
export const languageNames: Record<Locale, string> = { en: 'English', ja: '日本語', ko: '한국어' }
export function supportedLocale(value: string): Locale {
  const language = value.toLowerCase().split('-')[0]
  return locales.includes(language as Locale) ? language as Locale : 'en'
}
function initialLocale(): Locale {
  try {
    const saved = localStorage.getItem('yuoyuo-locale')
    if (saved) return supportedLocale(saved)
  } catch { /* Storage is optional in private browsing. */ }
  return supportedLocale(typeof navigator === 'undefined' ? 'en' : navigator.language)
}
void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, ja: { translation: ja }, ko: { translation: ko } },
  lng: initialLocale(), fallbackLng: 'en', supportedLngs: [...locales],
  interpolation: { escapeValue: false }, returnNull: false,
})
i18n.on('languageChanged', (language) => {
  if (typeof document !== 'undefined') document.documentElement.lang = supportedLocale(language)
  try { localStorage.setItem('yuoyuo-locale', supportedLocale(language)) } catch { /* Optional cache. */ }
})
if (typeof document !== 'undefined') document.documentElement.lang = i18n.language
export default i18n

/** Resolve once before mounting: saved choice wins over trusted IP detection. */
export async function initializeLocale(): Promise<void> {
  if (import.meta.env.VITE_INTERNATIONAL !== 'true') return
  try { if (localStorage.getItem('yuoyuo-locale')) return } catch { /* Optional cache. */ }
  try {
    const response = await fetch('/api/locale', {
      headers: { 'Accept-Language': typeof navigator === 'undefined' ? 'en' : navigator.languages.join(',') },
      cache: 'no-store', signal: AbortSignal.timeout(1500),
    })
    if (!response.ok) return
    const data = await response.json()
    if (typeof data.language === 'string' && locales.includes(data.language as Locale)) {
      // A manual selection made while detection was in flight always wins.
      try { if (localStorage.getItem('yuoyuo-locale')) return } catch { /* Optional cache. */ }
      await i18n.changeLanguage(data.language)
    }
  } catch { /* Offline/timeout keeps the browser-language fallback. */ }
}
