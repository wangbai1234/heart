import { useEffect, useRef, useState } from 'react'
import { useThemeStore } from '../../stores/themeStore'

export function ChengXuPremiseCard() {
  const isDark = useThemeStore((s) => s.resolvedTheme) === 'dark'
  const ref = useRef<HTMLIFrameElement>(null)
  const [height, setHeight] = useState(0)

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
    iframe.addEventListener('load', measure)
    const ro = new ResizeObserver(onResize)
    ro.observe(iframe)
    measure()
    return () => {
      iframe.removeEventListener('load', measure)
      ro.disconnect()
    }
  }, [])

  const leadInText = `初雪的傍晚，他准时出现在你必经的路口。热腾腾的糖炒栗子、刚好扣紧的围巾、
连你室友那点麻烦他都处理妥当——这份无微不至，你一直以为是因为你哥的托付。
可你没看见，他把手机扣进口袋的那一刻，屏幕上跳着你哥的未接来电。`

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
  color: ${isDark ? 'rgba(248,242,250,0.85)' : 'rgba(30,32,51,0.9)'};
  font-size: 13px;
  line-height: 1.6;
}
.lead {
  font-style: italic;
  color: ${isDark ? 'rgba(248,242,250,0.45)' : 'rgba(91,93,117,0.7)'};
  margin-bottom: 12px;
  font-size: 12px;
}
.card {
  background: ${isDark ? 'rgba(36,38,50,0.5)' : 'rgba(248,249,250,0.8)'};
  border: 1px solid ${isDark ? 'rgba(248,242,250,0.08)' : 'rgba(30,32,51,0.08)'};
  border-radius: 8px;
  padding: 12px;
}
.card-title {
  font-weight: 600;
  font-size: 12px;
  margin-bottom: 8px;
  color: ${isDark ? 'rgba(248,242,250,0.7)' : 'rgba(30,32,51,0.7)'};
  letter-spacing: 0.5px;
}
.row { display: flex; margin-bottom: 6px; font-size: 12px; }
.label { color: ${isDark ? 'rgba(248,242,250,0.5)' : 'rgba(91,93,117,0.7)'}; min-width: 48px; }
.value { color: ${isDark ? 'rgba(248,242,250,0.85)' : 'rgba(30,32,51,0.9)'}; flex: 1; }
.note {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid ${isDark ? 'rgba(248,242,250,0.06)' : 'rgba(30,32,51,0.06)'};
  font-size: 11px;
  line-height: 1.5;
  color: ${isDark ? 'rgba(248,242,250,0.55)' : 'rgba(91,93,117,0.75)'};
  font-style: italic;
}
</style>
</head>
<body>
<div class="lead">${leadInText}</div>
<div class="card">
  <div class="card-title">守护日志 · DAY 247</div>
  <div class="row"><span class="label">时间</span><span class="value">周四 傍晚 17:52</span></div>
  <div class="row"><span class="label">地点</span><span class="value">学校北门糖炒栗子摊 · 初雪</span></div>
  <div class="row"><span class="label">在场</span><span class="value">程叙（你哥的朋友）· 你（他暗恋的人）</span></div>
  <div class="row"><span class="label">此刻</span><span class="value">围巾系到一半，手机震了——是你哥的未接来电</span></div>
  <div class="note">
    他把"照顾你"过成了习惯，也把"喜欢你"藏成了秘密。<br>
    你哥托付的那份信任，是他唯一能靠近你的理由——<br>
    也是他最不敢越过的那条线。
  </div>
</div>
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
