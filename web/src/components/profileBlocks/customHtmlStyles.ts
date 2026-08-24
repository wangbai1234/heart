const STYLE_BLOCK_RE = /<style[^>]*>([\s\S]*?)<\/style>/gi
const CSS_IMPORT_RE = /@import[^;]*;/gi
const EXECUTABLE_CSS_RE = /expression\s*\(|javascript\s*:|behavior\s*:|-moz-binding/i

export function splitCustomHtmlStyles(html: string): {
  htmlWithoutStyles: string
  embeddedCss: string
} {
  const styleBlocks: string[] = []
  const htmlWithoutStyles = html.replace(STYLE_BLOCK_RE, (_block, css: string) => {
    styleBlocks.push(css)
    return ''
  })
  const embeddedCss = styleBlocks.join('\n').replace(CSS_IMPORT_RE, '')

  return {
    htmlWithoutStyles,
    embeddedCss: EXECUTABLE_CSS_RE.test(embeddedCss) ? '' : embeddedCss,
  }
}
