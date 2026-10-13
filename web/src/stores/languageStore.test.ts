import { afterEach, expect, it, vi } from 'vitest'
const api = vi.hoisted(() => ({ getLanguagePreferences: vi.fn(), saveLanguagePreferences: vi.fn() }))
vi.mock('../services/api', () => api)
import { useAuthStore } from './authStore'
import { useLanguageStore } from './languageStore'
import type { AuthUser, LanguagePreferences } from '../services/api'

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(done => { resolve = done })
  return { promise, resolve }
}
const initial: LanguagePreferences = { interface_language: 'en', response_language: 'bn', response_mode: 'fixed', response_follows_interface: false, action_style: 'fullwidth' }
function login(id: string) { useAuthStore.setState({ user: { id } as AuthUser }) }
afterEach(() => { login(''); useAuthStore.setState({ user: null }); vi.resetAllMocks() })

it('ignores a late GET after switching accounts, including back to the same id', async () => {
  login('a'); const old = deferred<LanguagePreferences>(); api.getLanguagePreferences.mockReturnValueOnce(old.promise)
  const first = useLanguageStore.getState().load()
  login('b'); login('a')
  api.getLanguagePreferences.mockResolvedValueOnce({ ...initial, interface_language: 'vi' })
  await useLanguageStore.getState().load()
  old.resolve(initial); await first
  expect(useLanguageStore.getState().preferences?.interface_language).toBe('vi')
})

it('shares GET and save locks and keeps fixed replies when the header changes', async () => {
  login('a'); api.getLanguagePreferences.mockResolvedValue(initial)
  await Promise.all([useLanguageStore.getState().load(), useLanguageStore.getState().load()])
  expect(api.getLanguagePreferences).toHaveBeenCalledTimes(1)
  const saved = deferred<LanguagePreferences>(); api.saveLanguagePreferences.mockReturnValueOnce(saved.promise)
  const first = useLanguageStore.getState().save({ interface_language: 'vi' })
  await useLanguageStore.getState().save({ response_language: 'en' })
  expect(api.saveLanguagePreferences).toHaveBeenCalledTimes(1)
  expect(api.saveLanguagePreferences).toHaveBeenCalledWith({ ...initial, interface_language: 'vi' })
  login('b'); saved.resolve({ ...initial, interface_language: 'vi' }); await first
  expect(useLanguageStore.getState().preferences).toBeNull()
})

it('does not apply a pending save to a different login after its initial load', async () => {
  login('a')
  const old = deferred<LanguagePreferences>()
  api.getLanguagePreferences.mockReturnValueOnce(old.promise)
  const save = useLanguageStore.getState().save({ interface_language: 'vi' })
  login('b')
  api.getLanguagePreferences.mockResolvedValueOnce(initial)
  await useLanguageStore.getState().load()
  old.resolve(initial)
  await save
  expect(api.saveLanguagePreferences).not.toHaveBeenCalled()
  expect(useLanguageStore.getState().preferences).toEqual(initial)
})
