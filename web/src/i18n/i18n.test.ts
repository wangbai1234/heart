import { describe, it, expect } from 'vitest'
import en from './locales/en.json'
import ja from './locales/ja.json'
import ko from './locales/ko.json'
import { supportedLocale } from './index'

describe('international locales', () => {
  it('has complete Japanese and Korean catalogues with matching interpolations', () => {
    for (const catalog of [ja, ko]) {
      expect(Object.keys(catalog).sort()).toEqual(Object.keys(en).sort())
      for (const key of Object.keys(en) as Array<keyof typeof en>) {
        expect(catalog[key].trim().length).toBeGreaterThan(0)
        expect(catalog[key].match(/{{[^}]+}}/g) ?? []).toEqual(en[key].match(/{{[^}]+}}/g) ?? [])
      }
    }
  })
  it('normalizes registered locales without inferring a country', () => {
    expect(supportedLocale('zh-CN')).toBe('zh')
    expect(supportedLocale('ja-JP')).toBe('ja')
    expect(supportedLocale('ko-KR')).toBe('ko')
  })
})

it('renders existing controls reactively without changing their stored values', async () => {
  const { vi } = await import('vitest')
  vi.stubEnv('VITE_INTERNATIONAL', 'true')
  vi.stubEnv('VITE_LOCALIZATION', 'true')
  vi.resetModules()
  const { default: i18n } = await import('./index')
  const { uiText, uiLabel } = await import('./text')
  const { renderToStaticMarkup } = await import('react-dom/server')
  const { createElement } = await import('react')
  const { SegmentedControl } = await import('../components/ui/SegmentedControl')
  const props = { options: ['浅色', '深色', '自动'], value: '深色', onChange: () => {} }
  try {
    await i18n.changeLanguage('en')
    expect(uiLabel('公开')).toBe('Public')
    expect(uiText('dynamic12', { v0: 3 })).toBe('3 unread')
    const english = renderToStaticMarkup(createElement(SegmentedControl, props))
    expect(english).toContain('Dark')
    expect(english).not.toContain('深色')
    await i18n.changeLanguage('ko')
    const korean = renderToStaticMarkup(createElement(SegmentedControl, props))
    expect(korean).toContain('다크')
    expect(korean).not.toContain('Dark')
    expect(props.value).toBe('深色')
    expect(uiLabel('Creator-authored custom label')).toBe('Creator-authored custom label')
  } finally {
    await i18n.changeLanguage('en')
    vi.unstubAllEnvs()
    vi.resetModules()
  }
})

it('persists only explicit device choices and refuses registry drift', async () => {
  const { vi } = await import('vitest')
  vi.stubEnv('VITE_LOCALIZATION', 'true'); vi.resetModules()
  const values = new Map<string, string>()
  vi.stubGlobal('localStorage', { getItem: (k: string) => values.get(k) ?? null, setItem: (k: string, v: string) => values.set(k, v) })
  vi.stubGlobal('navigator', { language: 'vi-VN', languages: ['vi-VN', 'en'] })
  const { registryVersion, resourceVersion, locales } = await import('./registry')
  const config = { registryVersion, resourceVersion, localization: true, languages: locales.map(code => ({ code, enabled: true })) }
  const fetchMock = vi.fn().mockImplementation(async (url: string) => ({ ok: true, json: async () => url === '/api/app-config' ? config : { language: 'vi' } }))
  vi.stubGlobal('fetch', fetchMock)
  try {
    const { default: locale, initializeLocale, selectDeviceLocale, applyAccountLocale, restoreDeviceLocale } = await import('./index')
    await initializeLocale()
    expect(locale.language).toBe('vi'); expect(values.size).toBe(0)
    await selectDeviceLocale('bn')
    await applyAccountLocale('en')
    expect(values.get('yuoyuo-explicit-locale')).toBe('bn')
    await restoreDeviceLocale(); expect(locale.language).toBe('bn')
    await initializeLocale()
    expect(fetchMock).toHaveBeenCalledTimes(3)
    vi.resetModules()
    config.resourceVersion = 'stale'
    const drift = await import('./index')
    await drift.initializeLocale()
    expect(drift.availableLocales()).toEqual(['zh'])
    expect(drift.default.language).toBe('zh')
  } finally { vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.resetModules() }
})

it('switches reply language with the interface unless explicitly pinned', async () => {
  const { withInterfaceLanguage } = await import('../components/LanguagePreferences')
  const preferences = { interface_language: 'en' as const, response_language: 'en' as const, action_style: 'fullwidth' as const, response_follows_interface: true }
  expect(withInterfaceLanguage(preferences, 'ja').response_language).toBe('ja')
  expect(withInterfaceLanguage({ ...preferences, response_follows_interface: false }, 'ko').response_language).toBe('en')
})

it('keeps Chinese when localization is paused despite cached language and browser country', async () => {
  const { vi } = await import('vitest')
  vi.stubEnv('VITE_INTERNATIONAL', 'true')
  vi.stubEnv('VITE_LOCALIZATION', 'false')
  vi.resetModules()
  const save = vi.fn()
  vi.stubGlobal('localStorage', { getItem: () => 'ko', setItem: save })
  vi.stubGlobal('navigator', { language: 'ja-JP', languages: ['ja-JP'] })
  const fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
  try {
    const { default: paused, initializeLocale } = await import('./index')
    await initializeLocale()
    expect(paused.resolvedLanguage).toBe('zh')
    await paused.changeLanguage('ko')
    expect(paused.resolvedLanguage).toBe('zh')
    expect(paused.t('continueWithGoogle')).toContain('Google')
    expect(paused.t('sharedMemories')).toBe('共同记忆')
    expect(fetchMock).not.toHaveBeenCalled()
    expect(save).not.toHaveBeenCalled()
  } finally { vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.resetModules() }
})

it('covers new screens in Chinese without missing keys or interpolation arguments', async () => {
  const { default: legacy } = await import('./legacy.json')
  const { default: zh } = await import('./locales/zh.json')
  const catalog: Record<string, string> = { ...legacy, ...zh }
  for (const [key, value] of Object.entries(en)) {
    expect(catalog[key], key).toBeTruthy()
    expect(catalog[key]?.match(/{{[^}]+}}/g) ?? [], key).toEqual(value.match(/{{[^}]+}}/g) ?? [])
  }
})
