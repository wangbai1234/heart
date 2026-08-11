import { useEffect, useRef, useState } from 'react'
import { useThemeStore } from '../../stores/themeStore'

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
  const [height, setHeight] = useState(0)
  const [isExpanded, setIsExpanded] = useState(false)

  useEffect(() => {
    const iframe = ref.current
    if (!iframe) return
    let lastW = -1
    const measure = () => {
      try {
        const body = iframe.contentDocument?.body
        if (body) setHeight(body.scrollHeight + 8)
      } catch {}
    }
    const onResize = () => {
      const w = iframe.clientWidth
      if (w !== lastW) {
        lastW = w
        measure()
      }
    }
    const handleMessage = (e: MessageEvent) => {
      if (e.data === 'toggle') {
        setIsExpanded((prev) => !prev)
      }
    }
    iframe.addEventListener('load', measure)
    const ro = new ResizeObserver(onResize)
    ro.observe(iframe)
    window.addEventListener('message', handleMessage)
    measure()
    return () => {
      iframe.removeEventListener('load', measure)
      ro.disconnect()
      window.removeEventListener('message', handleMessage)
    }
  }, [isExpanded])

  const ink = isDark ? 'rgba(248,242,250,0.85)' : 'rgba(30,32,51,0.9)'
  const muted = isDark ? 'rgba(248,242,250,0.5)' : 'rgba(91,93,117,0.7)'
  const rowsHtml = rows
    .map(
      (r) =>
        `<div class="row"><span class="label">${r.label}</span><span class="value">${r.value}</span></div>`,
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
  ${!isExpanded ? 'display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;' : ''}
}
.card {
  background: ${isDark ? 'rgba(36,38,50,0.5)' : 'rgba(248,249,250,0.8)'};
  border: 1px solid ${isDark ? 'rgba(248,242,250,0.08)' : 'rgba(30,32,51,0.08)'};
  border-left: 2px solid ${accent};
  border-radius: 8px;
  padding: 12px;
  ${!isExpanded ? 'opacity: 0.5;' : ''}
}
.card-title { font-weight: 600; font-size: 12px; margin-bottom: 8px; color: ${accent}; letter-spacing: 0.5px; }
.row { display: flex; margin-bottom: 6px; font-size: 12px; ${!isExpanded ? 'display: none;' : ''} }
.label { color: ${muted}; min-width: 48px; }
.value { color: ${ink}; flex: 1; }
.note {
  margin-top: 8px; padding-top: 8px;
  border-top: 1px solid ${isDark ? 'rgba(248,242,250,0.06)' : 'rgba(30,32,51,0.06)'};
  font-size: 11px; line-height: 1.6; color: ${isDark ? 'rgba(248,242,250,0.55)' : 'rgba(91,93,117,0.75)'};
  font-style: italic;
  ${!isExpanded ? 'display: none;' : ''}
}
.warning {
  margin-top: 8px; padding: 8px;
  background: ${isDark ? 'rgba(255,107,107,0.1)' : 'rgba(255,107,107,0.08)'};
  border-left: 2px solid ${isDark ? 'rgba(255,107,107,0.6)' : 'rgba(255,107,107,0.5)'};
  border-radius: 4px; font-size: 10px;
  color: ${isDark ? 'rgba(255,107,107,0.8)' : 'rgba(200,60,60,0.9)'};
  ${!isExpanded ? 'display: none;' : ''}
}
.expand-hint {
  margin-top: 8px; text-align: center; font-size: 11px; color: ${muted};
  ${isExpanded ? 'display: none;' : ''}
}
</style>
</head>
<body onclick="parent.postMessage('toggle','*')">
<div class="lead">${leadIn}</div>
<div class="card">
  <div class="card-title">${title}</div>
  ${rowsHtml}
  ${note ? `<div class="note">${note}</div>` : ''}
  ${warning ? `<div class="warning">${warning}</div>` : ''}
</div>
<div class="expand-hint">点击${isExpanded ? '收起' : '查看详情'}</div>
</body>
</html>
  `.trim()

  return (
    <iframe
      ref={ref}
      srcDoc={srcDoc}
      style={{ width: '100%', height: height || 200, border: 'none', display: 'block' }}
      sandbox="allow-same-origin"
    />
  )
}