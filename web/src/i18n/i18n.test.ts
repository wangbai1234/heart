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
