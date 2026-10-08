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
