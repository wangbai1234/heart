import { useEffect, useRef, useState } from 'react'
import DOMPurify from 'dompurify'
import type { ChromePalette } from '../../pages/CharacterProfilePage'

/**
 * 高级 HTML 渲染（UGC 创建重构批 6 · 分层第二层）
 *
 * 安全模型：
 * - dompurify 净化：移除 <script>、on* 事件属性、外链资源脚本
 * - iframe sandbox 不给 allow-scripts —— 即使净化被绕过也无脚本执行
 * - 保留 allow-same-origin 仅用于父页读取 scrollHeight 做高度自适应；
 *   无 allow-scripts 时该组合无 XSS 面（脚本永不执行）
 * - 从 ui_chrome 注入 CSS 变量，让用户 HTML 吃到配色
 */
export function CustomHtmlRenderer({
  html,
  chrome,
  trustedEmbeddedStyles = false,
}: {
  html: string
  chrome: ChromePalette
  /** First-party seeded profiles may bundle scoped CSS; UGC never may. */
  trustedEmbeddedStyles?: boolean
}) {
  const ref = useRef<HTMLIFrameElement>(null)
  const [height, setHeight] = useState(200)

  const styleBlocks = trustedEmbeddedStyles
    ? Array.from(html.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/gi), (match) => match[1]).join('\n')
    : ''
  // Even first-party CSS stays self-contained: no imports, remote URLs or
  // legacy executable CSS constructs can cross the iframe boundary.
  const embeddedCss = /@import|url\s*\(|expression\s*\(|javascript\s*:|behavior\s*:|-moz-binding/i.test(styleBlocks)
    ? ''
    : styleBlocks
  const htmlWithoutStyles = html.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')

  const clean = DOMPurify.sanitize(htmlWithoutStyles, {
    FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'link', 'base'],
    FORBID_ATTR: ['srcset'],
    ALLOW_DATA_ATTR: false,
  })

  const srcDoc = `<!doctype html><html><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<style>
:root{
  --theme-accent:${chrome.taglineColor};
  --theme-bg:${chrome.bg};
  --theme-name:${chrome.nameColor};
  --theme-muted:${chrome.ageColor};
}
*{box-sizing:border-box;margin:0;padding:0;max-width:100%}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  color:var(--theme-name);background:transparent;font-size:15px;line-height:1.7;
  word-break:break-word;overflow-wrap:break-word}
img{max-width:100%;height:auto;border-radius:12px}
a{color:var(--theme-accent);pointer-events:none}
${embeddedCss}
</style></head><body>${clean}</body></html>`

  useEffect(() => {
    const iframe = ref.current
    if (!iframe) return
    const measure = () => {
      const body = iframe.contentDocument?.body
      if (body) setHeight(body.scrollHeight + 8)
    }
    iframe.addEventListener('load', measure)
    const t = setTimeout(measure, 120)
    return () => {
      iframe.removeEventListener('load', measure)
      clearTimeout(t)
    }
  }, [srcDoc])

  return (
    <iframe
      ref={ref}
      title="custom-profile"
      srcDoc={srcDoc}
      sandbox="allow-same-origin"
      className="w-full border-0 block"
      style={{ height }}
    />
  )
}
