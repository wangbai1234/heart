import { afterEach, expect, it, vi } from 'vitest'
const api = vi.hoisted(() => ({ getCharacterProfile: vi.fn(), getCharacters: vi.fn() }))
vi.mock('../services/api', () => api)
import { useCharactersStore } from './charactersStore'
import type { CharacterProfileDTO } from '../services/api'

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(done => { resolve = done })
  return { promise, resolve }
}
afterEach(() => { useCharactersStore.getState().resetCatalog(); vi.resetAllMocks() })

it('discards an old-language profile without clobbering the new request', async () => {
  const old = deferred<CharacterProfileDTO>(), current = deferred<CharacterProfileDTO>()
  api.getCharacterProfile.mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise)
  const first = useCharactersStore.getState().loadProfile('a')
  useCharactersStore.getState().resetCatalog()
  const second = useCharactersStore.getState().loadProfile('a')
  old.resolve({ display_name: 'Old' } as CharacterProfileDTO)
  expect(await first).toBeNull()
  expect(useCharactersStore.getState().profileById.a).toBeUndefined()
  const shared = useCharactersStore.getState().loadProfile('a')
  expect(api.getCharacterProfile).toHaveBeenCalledTimes(2)
  current.resolve({ display_name: 'Current' } as CharacterProfileDTO)
  await Promise.all([second, shared])
  expect(useCharactersStore.getState().profileById.a.display_name).toBe('Current')
})

it('starts a new catalog request after reset and ignores the stale account result', async () => {
  const old = deferred<{ characters: never[] }>(), current = deferred<{ characters: never[] }>()
  api.getCharacters.mockReturnValueOnce(old.promise).mockReturnValueOnce(current.promise)
  const first = useCharactersStore.getState().load(true)
  useCharactersStore.getState().resetCatalog()
  const second = useCharactersStore.getState().load(true)
  old.resolve({ characters: [] }); await first
  expect(useCharactersStore.getState().loaded).toBe(false)
  expect(useCharactersStore.getState().loading).toBe(true)
  current.resolve({ characters: [] }); await second
  expect(useCharactersStore.getState().loaded).toBe(true)
})
