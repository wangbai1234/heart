import { afterEach, describe, expect, it, vi } from 'vitest'

import { promptAuthentication, setNavigate } from './navigation'
import { useAuthPromptStore } from '../stores/authPromptStore'

afterEach(() => {
  setNavigate(null)
  useAuthPromptStore.setState({ open: false, returnTo: '/character' })
})

describe('promptAuthentication', () => {
  it('opens the auth modal over the catalog and preserves the protected route', () => {
    const navigate = vi.fn()
    setNavigate(navigate)

    promptAuthentication('/settings/profile?source=expired')

    expect(useAuthPromptStore.getState()).toMatchObject({
      open: true,
      returnTo: '/settings/profile?source=expired',
    })
    expect(navigate).toHaveBeenCalledWith('/character', { replace: true })
  })

  it('never returns an expired session to the standalone login route', () => {
    const navigate = vi.fn()
    setNavigate(navigate)

    promptAuthentication('/login')

    expect(useAuthPromptStore.getState()).toMatchObject({
      open: true,
      returnTo: '/character',
    })
  })
})
