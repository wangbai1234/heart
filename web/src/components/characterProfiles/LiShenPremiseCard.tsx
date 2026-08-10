import { useEffect, useRef, useState } from 'react'
import { useThemeStore } from '../../stores/themeStore'

export function LiShenPremiseCard() {
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

  const leadInText = `你是唯一不为厉家姓氏而靠近他的人。所有人眼里他是完美继承人，只有你看见
他深夜买醉的样子、在宴会假笑的疲惫、害怕被抛弃的偏执。可你说要去国外进修
那天，他崩了。江景别墅的门从外面反锁，你手腕上是他颤抖着扣上的银色手铐——
他说，对不起，但我只能这样留住你。`

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
.warning {
  margin-top: 8px;
  padding: 8px;
  background: ${isDark ? 'rgba(255,107,107,0.1)' : 'rgba(255,107,107,0.08)'};
  border-left: 2px solid ${isDark ? 'rgba(255,107,107,0.6)' : 'rgba(255,107,107,0.5)'};
  border-radius: 4px;
  font-size: 10px;
  color: ${isDark ? 'rgba(255,107,107,0.8)' : 'rgba(200,60,60,0.9)'};
}
</style>
</head>
<body>
<div class="lead">${leadInText}</div>
<div class="card">
  <div class="card-title">囚禁日志 · HOUR 03</div>
  <div class="row"><span class="label">时间</span><span class="value">凌晨 02:47</span></div>
  <div class="row"><span class="label">地点</span><span class="value">厉家江景别墅 · 主卧</span></div>
  <div class="row"><span class="label">在场</span><span class="value">厉深（豪门独子，占有欲失控）· 你（被锁住的唯一真心）</span></div>
  <div class="row"><span class="label">此刻</span><span class="value">手铐冰凉扣在腕上，他坐在床边，手还在发抖</span></div>
  <div class="note">
    他从小到大得到的一切，都能用钱买、用权换。<br>
    唯独你的温柔——那种看着他眼睛、而不是看他姓氏的目光——<br>
    他买不起分给别人的那一份，也承受不了失去。<br>
    所以他用了最病的方式，把你锁进了他唯一会卸下防备的地方。
  </div>
  <div class="warning">内容分级提示：本剧情包含病娇占有题材（物理囚禁场景），18+ 向，不适应此类内容请谨慎继续</div>
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