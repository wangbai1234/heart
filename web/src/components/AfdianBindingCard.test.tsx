import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { AfdianBindingCard } from './AfdianBindingCard'

describe('AfdianBindingCard', () => {
  it('uses the sponsor page safely when auto-bind copy is forced without a checkout URL', () => {
    const html = renderToStaticMarkup(
      <AfdianBindingCard
        bindingCode="TEST-CODE"
        afdianUrl="https://ifdian.net/a/yuoyuo"
        forceAutoBindCopy
      />,
    )

    expect(html).toContain('无需填写备注')
    expect(html).toContain('href="https://ifdian.net/a/yuoyuo"')
  })
})
