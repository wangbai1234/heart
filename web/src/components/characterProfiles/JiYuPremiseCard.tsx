import { useState, useRef, useEffect } from 'react'

/** JiYu chat premise card (clinical iframe banner above messages).
 * Framed conflict hook + doctor-patient taboo tone. */
export function JiYuPremiseCard() {
  const [height, setHeight] = useState(0)
  const ref = useRef<HTMLIFrameElement>(null)

  useEffect(() => {
    const iframe = ref.current
    if (!iframe) return
    const measure = () => {
      try {
        const doc = iframe.contentDocument
        if (doc) {
          const h = doc.body.scrollHeight
          setHeight(h + 8)
        }
      } catch {}
    }
    iframe.addEventListener('load', measure)
    measure()
    return () => iframe.removeEventListener('load', measure)
  }, [])

  const srcDoc = `
<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{
--accent:#7A8C9B;--accent-glow:rgba(122,140,155,.3);--accent-soft:#A1B3C4;
--ink:#E8ECF0;--ink-2:#C4CACC;--tx-mute:#8F9BA4;
--surface:#1A1E22;--surface-2:#21252A;--hair:rgba(122,140,155,.12);--hair-2:rgba(122,140,155,.06);
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,\"Segoe UI\",Helvetica,Arial,sans-serif;
background:transparent;color:var(--ink);-webkit-font-smoothing:antialiased}
.container{margin:14px 4px 0;border-radius:18px;overflow:hidden;
background:linear-gradient(155deg,rgba(30,34,39,.65),rgba(24,28,32,.72));
backdrop-filter:blur(16px);border:1px solid var(--hair);
box-shadow:0 4px 20px rgba(0,0,0,.15)}
.inner{padding:17px 18px 14px}
.tag{display:inline-block;font-size:11px;color:var(--accent-soft);
background:rgba(122,140,155,.08);border-radius:10px;padding:3px 10px;margin-bottom:10px}
.para{font-size:14px;line-height:1.75;color:var(--ink-2);margin-bottom:12px}
.para:last-child{margin:0}
.para em{color:var(--accent-soft);font-style:normal}
</style>
<div class="container">
<div class="inner">
<span class="tag">前情提要</span>
<p class="para">
你是他的心理医生。他是你那位把<em>所有依赖</em>都投注在你身上的病人——偏执、破碎、危险,
可面对你时又小心翼翼得近乎可怜。
</p>
<p class="para">
他清楚这份情感越界,你也清楚。可你们都没能停下。因为在他眼里,
你是唯一愿意接住他沉默的人;而你知道,<em>你正走在职业伦理最危险的边缘</em>。
</p>
</div>
</div>
`

  return (
    <iframe
      ref={ref}
      srcDoc={srcDoc}
      sandbox="allow-same-origin"
      style={{
        width: '100%',
        height: height ? `${height}px` : 'auto',
        border: 'none',
        display: 'block',
        overflow: 'hidden',
      }}
      title="ji_yu premise"
    />
  )
}
