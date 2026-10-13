import { expect, it, vi } from 'vitest'

it('translates labels while keeping canonical filtering keys and unknown tags', async () => {
  vi.stubEnv('VITE_LOCALIZATION', 'true'); vi.resetModules()
  const { characterTagLabel } = await import('./characterTags')
  const tags = ['校园', '女性向', '<custom>']
  expect(tags.map(tag => characterTagLabel(tag, 'en'))).toEqual(['Campus', 'For women', '<custom>'])
  expect(characterTagLabel('校园', 'vi')).toBe('Học đường')
  expect(characterTagLabel('校园', 'bn')).toBe('ক্যাম্পাস')
  expect(characterTagLabel('校园', 'zh')).toBe('校园')
  expect(tags.includes('校园')).toBe(true)
  expect(tags.includes('Campus')).toBe(false)
  vi.unstubAllEnvs(); vi.resetModules()
})

it('shows only registered labels in launch locales without changing stored tags', async () => {
  vi.stubEnv('VITE_LOCALIZATION', 'true'); vi.resetModules()
  const { visibleCharacterTags } = await import('./characterTags')
  const tags = ['专属中文标签', '校园', 'BL', '女性向']
  for (const locale of ['en', 'vi', 'bn']) {
    expect(visibleCharacterTags(tags, locale)).toEqual(['校园', '女性向'])
    expect(visibleCharacterTags(['专属中文标签'], locale)).toEqual([])
  }
  expect(visibleCharacterTags(tags, 'zh')).toEqual(tags)
  expect(tags).toEqual(['专属中文标签', '校园', 'BL', '女性向'])
  vi.unstubAllEnvs(); vi.resetModules()
})
