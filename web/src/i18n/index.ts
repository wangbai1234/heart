import { createInstance } from 'i18next'
import { initReactI18next } from 'react-i18next'
import legacy from './legacy.json'
import { localeAliases, localeRegistry, locales, registryVersion, resourceVersion, type Locale } from './registry'

export { locales, type Locale }
export const languageNames = Object.fromEntries(localeRegistry.map(row => [row.code, row.nativeName])) as Record<Locale, string>
const localized = import.meta.env.VITE_LOCALIZATION === 'true'
const deviceKey = 'yuoyuo-explicit-locale'
let enabled: Locale[] = ['zh']
let deviceEpoch = 0
let accountEpoch = 0
export function accountLocaleRevision(): number { return accountEpoch }
export function invalidateAccountLocaleRequests(): void { accountEpoch++ }
let detectedLocale: Locale = 'en'
const i18n = createInstance()
const catalogs = import.meta.glob<Record<string, string>>('./locales/*.json', { eager: true, import: 'default' })
const resources = Object.fromEntries(locales.map(code => [code, { translation: {
  ...(code === 'zh' ? legacy : {}), ...catalogs[`./locales/${code}.json`],
} }]))
const fallbackLng = localized ? Object.fromEntries(localeRegistry.map(row => [row.code, [row.fallback]])) : 'zh'

export function normalizeLocale(value: string): Locale | undefined {
  let code = value.trim().toLowerCase()
  while (code) {
    if (localeAliases[code]) return localeAliases[code]
    if (code.startsWith('zh-hant') || ['zh-tw', 'zh-hk', 'zh-mo'].includes(code)) return undefined
    const index = code.lastIndexOf('-')
    code = index > 0 ? code.slice(0, index) : ''
  }
  return undefined
}
export function supportedLocale(value: string): Locale { return normalizeLocale(value) ?? 'en' }
export function availableLocales(): readonly Locale[] { return enabled }
function savedDeviceLocale(): Locale | undefined {
  try { return normalizeLocale(localStorage.getItem(deviceKey) ?? '') } catch { return undefined }
}
function effectiveLocale(value: string): Locale {
  const code = normalizeLocale(value)
  return code && enabled.includes(code) ? code : enabled.includes('en') ? 'en' : 'zh'
}
function browserLocale(): Locale {
  const languages = typeof navigator === 'undefined' ? ['en'] : navigator.languages?.length ? navigator.languages : [navigator.language]
  return languages.map(normalizeLocale).find(code => code && enabled.includes(code)) ?? (enabled.includes('en') ? 'en' : 'zh')
}
function updateDocument(language: string) {
  if (typeof document === 'undefined') return
  const row = localeRegistry.find(item => item.code === supportedLocale(language))!
  document.documentElement.lang = row.formatLocale
  document.documentElement.dir = row.direction
}
void i18n.use(initReactI18next).init({
  resources,
  lng: 'zh', fallbackLng, supportedLngs: localized ? [...locales] : ['zh'],
  interpolation: { escapeValue: false }, returnNull: false,
})
i18n.on('languageChanged', updateDocument)
updateDocument(i18n.language)
export default i18n

/** Only explicit device choices persist; account/detection changes never do. */
export async function selectDeviceLocale(locale: Locale): Promise<void> {
  if (!localized || !enabled.includes(locale)) return
  deviceEpoch++; accountEpoch++
  try { localStorage.setItem(deviceKey, locale) } catch { /* Optional storage. */ }
  await i18n.changeLanguage(locale)
}
export async function applyAccountLocale(locale: Locale, expectedRevision?: number): Promise<void> {
  if (expectedRevision !== undefined && expectedRevision !== accountEpoch) return
  accountEpoch++
  await i18n.changeLanguage(effectiveLocale(locale))
}
export async function restoreDeviceLocale(): Promise<void> {
  accountEpoch++
  await i18n.changeLanguage(localized ? effectiveLocale(savedDeviceLocale() ?? detectedLocale) : 'zh')
}

/** Both assets and runtime must agree before offering language writes. */
export async function initializeLocale(): Promise<void> {
  if (!localized) return
  const epoch = deviceEpoch, account = accountEpoch
  try {
    const response = await fetch('/api/app-config', { cache: 'no-store', signal: AbortSignal.timeout(1500) })
    if (!response.ok) return
    const config = await response.json()
    if (config.registryVersion !== registryVersion || config.resourceVersion !== resourceVersion || !Array.isArray(config.languages)) return
    const codes = config.languages.filter((row: { code: string; enabled: boolean }) => row.enabled && locales.includes(row.code as Locale)).map((row: { code: Locale }) => row.code)
    enabled = config.localization && codes.length ? codes : ['zh']
    detectedLocale = browserLocale()
    if (epoch !== deviceEpoch || account !== accountEpoch) return
    await i18n.changeLanguage(effectiveLocale(savedDeviceLocale() ?? detectedLocale))
    if (savedDeviceLocale()) return
    const detection = await fetch('/api/locale', {
      headers: { 'Accept-Language': typeof navigator === 'undefined' ? 'en' : (navigator.languages?.length ? navigator.languages : [navigator.language]).join(',') },
      cache: 'no-store', signal: AbortSignal.timeout(1500),
    })
    if (!detection.ok) return
    const data = await detection.json()
    if (epoch !== deviceEpoch || account !== accountEpoch || savedDeviceLocale()) return
    if (typeof data.language === 'string') {
      detectedLocale = effectiveLocale(data.language)
      await i18n.changeLanguage(detectedLocale)
    }
  } catch { /* Offline/version mismatch prevents new language writes. */ }
}
