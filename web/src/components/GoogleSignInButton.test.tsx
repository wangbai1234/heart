import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { expect, it } from 'vitest'
import { GoogleSignInButton, safeGoogleReturnTo } from './GoogleSignInButton'

it.each(['https://evil.invalid', '//evil.invalid', '/\\evil.invalid', '/auth/google/callback', '/login?next=/chat', '/register'])('rejects unsafe or looping return path %s', path => {
  expect(safeGoogleReturnTo(path)).toBe('/character')
})
it('preserves a local chat return path', () => {
  expect(safeGoogleReturnTo('/chat/abc?source=memory')).toBe('/chat/abc?source=memory')
})
it('renders a Google entry before configuration is loaded without submitting the form', () => {
  const html = renderToStaticMarkup(createElement(GoogleSignInButton, { beforeStart: () => true }))
  expect(html).toContain('Google')
  expect(html).toContain('type="button"')
  expect(html).toContain('disabled')
})
