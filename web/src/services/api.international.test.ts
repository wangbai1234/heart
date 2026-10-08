import { afterEach, expect, it, vi } from 'vitest'
import type { CharacterDraftDTO } from './api'

const draft: CharacterDraftDTO = {
  display_name: { zh: 'Edited name' }, persona: 'An adult writer with a thoughtful personality.',
  greeting_style: 'warm', visibility: 'private',
  sliders: { warmth: 50, talkativeness: 50, directness: 50, humor: 50, playfulness: 50, steadiness: 50 },
}

afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.resetModules() })

it('creates in the chosen language with a matching request header', async () => {
  vi.stubEnv('VITE_INTERNATIONAL', 'true')
  vi.resetModules()
  const { default: i18n } = await import('../i18n')
  await i18n.changeLanguage('ko')
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 'new' }) })
  vi.stubGlobal('fetch', fetchMock)
  const { createCharacter } = await import('./api')
  await createCharacter(draft)
  const [url, options] = fetchMock.mock.calls[0]
  expect(url).toBe('/api/characters')
  expect(options.headers['Accept-Language']).toBe('ko')
  expect(JSON.parse(options.body)).toMatchObject({ locale: 'ko', display_name: { ko: 'Edited name' }, visibility: 'private' })
})

it.each(['zh-CN', 'ja'])('preserves authored locale %s and translations when editing in English', async (locale) => {
  vi.stubEnv('VITE_INTERNATIONAL', 'true')
  vi.resetModules()
  const { default: i18n } = await import('../i18n')
  await i18n.changeLanguage('en')
  const key = locale === 'zh-CN' ? 'zh' : 'ja'
  const original = { ...draft, locale, display_name: { [key]: 'Original', ko: '보존된 이름' } }
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => original })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ id: 'existing' }) })
  vi.stubGlobal('fetch', fetchMock)
  const { updateCharacter } = await import('./api')
  await updateCharacter('existing', draft)
  expect(fetchMock.mock.calls[0][0]).toBe('/api/characters/existing/draft')
  const [url, options] = fetchMock.mock.calls[1]
  expect(url).toBe('/api/characters/existing')
  expect(JSON.parse(options.body)).toMatchObject({
    locale, display_name: { [key]: 'Edited name', ko: '보존된 이름' }, visibility: 'private',
  })
})
