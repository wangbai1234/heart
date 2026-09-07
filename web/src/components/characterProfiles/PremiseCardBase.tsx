import { useEffect, useRef, useState } from 'react'
import { useThemeStore } from '../../stores/themeStore'
import { escapeHtml, escapeHtmlAllowBr } from '../../utils/escapeHtml'

export interface PremiseRow {
  label: string
  value: string
}

export interface PremiseCardData {
  /** 强调色（hex），呼应角色详情页色系 */
  accent: string
  /** 冲突前情（斜体引导文，点明冲突起点+情境） */
  leadIn: string
  /** 元信息卡标题（上帝视角，如「囚禁日志 · HOUR 03」） */
  title: string
  /** 时/地/在场/此刻 结构化行 */
  rows: PremiseRow[]
  /** 卡片底部旁白（支持 <br>） */
  note?: string
  /** 18+ / 分级提示（可选） */
  warning?: string
}

/**
 * 聊天页角色专属「前情提要卡」通用外壳。
 * 参考 lumeow 结构化元信息卡(时辰/地界/在场/风闻) + nimoo 开场引导文。
 * 各角色只提供数据(accent/leadIn/rows/...)，版式与主题适配在此统一。
 */
export function PremiseCardBase({ accent, leadIn, title, rows, note, warning }: PremiseCardData) {
  const isDark = useThemeStore((s) => s.resolvedTheme) === 'dark'
  const ref = useRef<HTMLIFrameElement>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const [height, setHeight] = useState(320)

  useEffect(() => {
    const iframe = ref.current
    if (!iframe) return
    let lastW = -1
    const measure = () => {
      try {
        const body = iframe.contentDocument?.body
        if (body) setHeight(Math.max(220, body.scrollHeight + 8))
      } catch {}
    }
    const onResize = () => {
      const w = iframe.clientWidth
      if (w !== lastW) {
        lastW = w
        measure()
      }
    }
    const handleMessage = () => {
      // Legacy cards used a collapsed iframe and a postMessage toggle. Cards
      // are now always fully readable on first paint; keep accepting the old
      // message as a no-op so stale embeds cannot re-collapse the content.
    }
    iframe.addEventListener('load', measure)
    const observeBody = () => {
      measure()
      const body = iframe.contentDocument?.body
      if (!body) return
      const bodyObserver = new ResizeObserver(measure)
      bodyObserver.observe(body)
      ;(iframe as HTMLIFrameElement & { __premiseObserver?: ResizeObserver }).__premiseObserver = bodyObserver
    }
    iframe.addEventListener('load', observeBody)
    const ro = new ResizeObserver(onResize)
    ro.observe(iframe)
    window.addEventListener('message', handleMessage)

    // isExpanded 变化后强制重新测量高度（srcdoc 变化不触发 load）
    const timer = setTimeout(measure, 16)

    return () => {
      iframe.removeEventListener('load', measure)
      iframe.removeEventListener('load', observeBody)
      ;(iframe as HTMLIFrameElement & { __premiseObserver?: ResizeObserver }).__premiseObserver?.disconnect()
      ro.disconnect()
      window.removeEventListener('message', handleMessage)
      clearTimeout(timer)
    }
  }, [])

  const ink = isDark ? 'rgba(248,242,250,0.85)' : 'rgba(30,32,51,0.9)'
  const muted = isDark ? 'rgba(248,242,250,0.5)' : 'rgba(91,93,117,0.7)'
  const rowsHtml = rows
    .map(
      (r) =>
        `<div class="row"><span class="label">${escapeHtml(r.label)}</span><span class="value">${escapeHtml(r.value)}</span></div>`,
    )
    .join('')

  const srcDoc = `
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif;
  padding: 16px;
  background: ${isDark ? 'rgba(23,25,34,0.6)' : 'rgba(255,255,255,0.6)'};
  color: ${ink};
  font-size: 13px;
  line-height: 1.6;
  cursor: pointer;
  user-select: none;
}
.lead {
  font-style: italic; color: ${muted}; margin-bottom: 12px; font-size: 12px; line-height: 1.7;
}
.card {
  background: ${isDark ? 'rgba(36,38,50,0.5)' : 'rgba(248,249,250,0.8)'};
  border: 1px solid ${isDark ? 'rgba(248,242,250,0.08)' : 'rgba(30,32,51,0.08)'};
  border-left: 2px solid ${accent};
  border-radius: 8px;
  padding: 12px;
}
.card-title { font-weight: 600; font-size: 12px; margin-bottom: 8px; color: ${accent}; letter-spacing: 0.5px; }
  .row { display: flex; margin-bottom: 6px; font-size: 12px; }
.label { color: ${muted}; min-width: 48px; }
.value { color: ${ink}; flex: 1; }
.note {
  margin-top: 8px; padding-top: 8px;
  border-top: 1px solid ${isDark ? 'rgba(248,242,250,0.06)' : 'rgba(30,32,51,0.06)'};
  font-size: 11px; line-height: 1.6; color: ${isDark ? 'rgba(248,242,250,0.55)' : 'rgba(91,93,117,0.75)'};
  font-style: italic;
}
.warning {
  margin-top: 8px; padding: 8px;
  background: ${isDark ? 'rgba(255,107,107,0.1)' : 'rgba(255,107,107,0.08)'};
  border-left: 2px solid ${isDark ? 'rgba(255,107,107,0.6)' : 'rgba(255,107,107,0.5)'};
  border-radius: 4px; font-size: 10px;
  color: ${isDark ? 'rgba(255,107,107,0.8)' : 'rgba(200,60,60,0.9)'};
}
.expand-hint { display: none; }
</style>
</head>
<body>
<div class="lead">${escapeHtml(leadIn)}</div>
<div class="card">
  <div class="card-title">${escapeHtml(title)}</div>
  ${rowsHtml}
  ${note ? `<div class="note">${escapeHtmlAllowBr(note)}</div>` : ''}
  ${warning ? `<div class="warning">${escapeHtml(warning)}</div>` : ''}
</div>
</body>
</html>
  `.trim()

  return (
    <div ref={wrapperRef}>
      <iframe
        ref={ref}
        srcDoc={srcDoc}
        style={{ width: '100%', height: height || 200, border: 'none', display: 'block' }}
        sandbox="allow-same-origin allow-scripts"
      />
    </div>
  )
}
