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
  it('does not offer Chinese or infer a region from a locale', () => {
    expect(supportedLocale('zh-CN')).toBe('en')
    expect(supportedLocale('ja-JP')).toBe('ja')
    expect(supportedLocale('ko-KR')).toBe('ko')
  })
})

it('renders existing controls reactively without changing their stored values', async () => {
  const { vi } = await import('vitest')
  vi.stubEnv('VITE_INTERNATIONAL', 'true')
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

it('uses IP detection once and preserves saved choices and browser fallback', async () => {
  const { vi } = await import('vitest')
  vi.stubEnv('VITE_INTERNATIONAL', 'true')
  vi.resetModules()
  const values = new Map<string, string>()
  vi.stubGlobal('localStorage', { getItem: (k: string) => values.get(k) ?? null, setItem: (k: string, v: string) => values.set(k, v) })
  vi.stubGlobal('navigator', { language: 'ko-KR', languages: ['ko-KR', 'en'] })
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ language: 'ja' }) })
  vi.stubGlobal('fetch', fetchMock)
  const { default: detected, initializeLocale } = await import('./index')
  try {
    await initializeLocale()
    expect(detected.language).toBe('ja')
    expect(fetchMock).toHaveBeenCalledOnce()
    await detected.changeLanguage('en')
    await initializeLocale()
    expect(detected.language).toBe('en')
    expect(fetchMock).toHaveBeenCalledOnce()
    values.clear()
    await detected.changeLanguage('ko')
    values.clear()
    fetchMock.mockRejectedValueOnce(new Error('offline'))
    await initializeLocale()
    expect(detected.language).toBe('ko')
  } finally {
    vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.resetModules()
  }
})

it('switches reply language with the interface unless explicitly pinned', async () => {
  const { withInterfaceLanguage } = await import('../components/LanguagePreferences')
  const preferences = { interface_language: 'en' as const, response_language: 'en' as const, action_style: 'fullwidth' as const, response_follows_interface: true }
  expect(withInterfaceLanguage(preferences, 'ja').response_language).toBe('ja')
  expect(withInterfaceLanguage({ ...preferences, response_follows_interface: false }, 'ko').response_language).toBe('en')
})
