import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './locales/en.json'
import ja from './locales/ja.json'
import ko from './locales/ko.json'

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
