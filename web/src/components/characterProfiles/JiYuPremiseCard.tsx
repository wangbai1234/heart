import { useState, useRef, useEffect } from 'react'

/** JiYu chat premise (clinical iframe banner above the opening message).
 * Two layers, mirroring nimoo/lumeow's chat opening:
 *  1) 灰色前情提要引导文本（点明冲突起点）
 *  2) 上帝视角状态卡 —— 这里做成"咨询记录/病历"头（贴合医患设定） */
export function JiYuPremiseCard() {
  const [height, setHeight] = useState(280) // 初始估算，避免锁死早测的偏小值
  const ref = useRef<HTMLIFrameElement>(null)

  useEffect(() => {
    const iframe = ref.current
    if (!iframe) return
    // 内层内容高度只取决于当前宽度；宽度一变就重测，避免早期在过宽布局下测到
    // 偏小值后被锁死（导致卡片被裁）。观察"外层 iframe 元素"的尺寸变化，
    // 父级同源可读，不受 sandbox 限制；仅在宽度变化时重测，防止改高触发的回环。
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

  const srcDoc = `
<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{
--accent:#7A8C9B;--accent-soft:#A1B3C4;--accent-glow:rgba(122,140,155,.28);
--ink:#E8ECF0;--ink-2:#C4CACC;--tx-mute:#8A96A0;
--serif:"Songti SC","Noto Serif SC",serif;
--hair:rgba(122,140,155,.14);--hair-2:rgba(122,140,155,.08);
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
background:transparent;color:var(--ink);-webkit-font-smoothing:antialiased}
/* 1) 灰色前情提要引导 */
.lead{margin:12px 6px 0;font-size:13px;line-height:1.85;color:var(--tx-mute);font-style:italic}
.lead em{color:var(--accent-soft);font-style:normal}
/* 2) 咨询记录 状态卡 */
.rec{margin:12px 4px 0;border-radius:16px;overflow:hidden;
background:linear-gradient(158deg,rgba(30,34,39,.72),rgba(22,26,30,.8));
backdrop-filter:blur(18px);border:1px solid var(--hair);
box-shadow:0 6px 24px rgba(0,0,0,.2)}
.rec .bar{display:flex;align-items:center;justify-content:space-between;
padding:11px 16px;border-bottom:1px solid var(--hair-2);
background:rgba(122,140,155,.05)}
.rec .bar .t{font-family:var(--serif);font-size:13px;letter-spacing:.14em;color:var(--accent-soft)}
.rec .bar .no{font-size:10px;letter-spacing:.1em;color:var(--tx-mute)}
.rec .grid{padding:13px 16px 6px;display:grid;grid-template-columns:auto 1fr;gap:8px 14px}
.rec .k{font-size:11px;color:var(--tx-mute);white-space:nowrap;padding-top:1px}
.rec .v{font-size:13px;line-height:1.55;color:var(--ink-2)}
.rec .note{margin:2px 16px 14px;padding-top:11px;border-top:1px solid var(--hair-2);
font-family:var(--serif);font-size:12.5px;line-height:1.7;color:var(--tx-mute);font-style:italic}
.rec .note b{color:var(--accent-soft);font-weight:normal}
</style>
<p class="lead">
连续第七周的黄昏，你如约推开那扇咨询室的门。<em>他今天，等了你很久。</em>
</p>
<div class="rec">
<div class="bar"><span class="t">咨询记录</span><span class="no">CASE&nbsp;NO.&nbsp;0037</span></div>
<div class="grid">
<span class="k">时间</span><span class="v">周四 傍晚 18:07（迟到七分钟）</span>
<span class="k">地点</span><span class="v">私人心理咨询室 · 只剩一盏落地灯</span>
<span class="k">在场</span><span class="v">季屿（个案）· 你（主治医生）</span>
<span class="k">状态</span><span class="v">高度戒备 · 对你却近乎依赖</span>
</div>
<p class="note">
个案对外缄默、对你敞开。<b>医患界线正在他这里悄悄失效</b>——而你清楚，越界的代价由你承担。
</p>
</div>
`

  return (
    <iframe
      ref={ref}
      srcDoc={srcDoc}
      sandbox="allow-same-origin"
      style={{
        width: '100%',
        height: `${height}px`,
        border: 'none',
        display: 'block',
        overflow: 'hidden',
      }}
      title="ji_yu premise"
    />
  )
}
