import { describe, expect, it } from 'vitest'

import { splitCustomHtmlStyles } from './customHtmlStyles'

describe('splitCustomHtmlStyles', () => {
  it('preserves class CSS for user-created advanced HTML', () => {
    const result = splitCustomHtmlStyles(
      '<style>.profile-card{display:grid;gap:12px}</style><section class="profile-card">content</section>',
    )

    expect(result.embeddedCss).toContain('.profile-card{display:grid;gap:12px}')
    expect(result.htmlWithoutStyles).toBe('<section class="profile-card">content</section>')
  })

  it('preserves HTTPS assets while removing external stylesheet imports', () => {
    const result = splitCustomHtmlStyles(
      '<style>@import "https://example.com/theme.css";.hero{background:url(https://example.com/hero.webp)}</style><div class="hero"></div>',
    )

    expect(result.embeddedCss).not.toContain('@import')
    expect(result.embeddedCss).toContain('url(https://example.com/hero.webp)')
  })

  it('rejects legacy executable CSS without removing the HTML content', () => {
    const result = splitCustomHtmlStyles(
      '<style>.card{width:expression(alert(1))}</style><div class="card">safe content</div>',
    )

    expect(result.embeddedCss).toBe('')
    expect(result.htmlWithoutStyles).toContain('safe content')
  })
})
