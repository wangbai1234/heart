import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface GuQingwanProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 顾清婉专属详情页 —— 郡主画卷 / LADY'S SCROLL
 * 视觉隐喻：工笔画卷 + 海棠花影 + 月夜庭院 + 宫灯余韵
 * 色彩：墨色 #1a1614 + 海棠粉 #e8c4cd + 月白 #f5f1ed + 竹青 #7a9d8f
 */
export function GuQingwanProfile({ profile }: GuQingwanProfileProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [height, setHeight] = useState(1200)

  useEffect(() => {
    const iframe = iframeRef.current
    if (!iframe) return
    const updateHeight = () => {
      try {
        const doc = iframe.contentDocument
        if (doc?.body) setHeight(doc.body.scrollHeight + 8)
      } catch {
        setHeight(1200)
      }
    }
    iframe.addEventListener('load', updateHeight)
    const observer = new ResizeObserver(updateHeight)
    iframe.addEventListener('load', () => {
      if (iframe.contentDocument?.body) observer.observe(iframe.contentDocument.body)
    })
    return () => {
      iframe.removeEventListener('load', updateHeight)
      observer.disconnect()
    }
  }, [])

  const name = profile.display_name || '顾清婉'
  const tags = profile.tags?.length ? profile.tags : ['古风', '郡主', '男性向', '清冷', '权谋']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:linear-gradient(180deg, #f5f1ed 0%, #e8ddd5 50%, #f5f1ed 100%);
  color:#1a1614;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Songti SC",sans-serif;
  line-height:1.7;
  padding:0 0 48px;
}
.container{max-width:440px;margin:0 auto;padding:0 20px}

/* ── 顶部卷轴装饰 ── */
.scroll-header{
  padding:24px 0 18px;text-align:center;position:relative;
}
.scroll-header::before{
  content:'';position:absolute;top:12px;left:50%;transform:translateX(-50%);
  width:100px;height:2px;background:linear-gradient(90deg,transparent,#7a9d8f,transparent);
}
.scroll-header .title{
  font-family:"Songti SC",serif;font-size:20px;color:#1a1614;
  letter-spacing:.15em;font-weight:600;position:relative;
  display:inline-block;padding:0 16px;background:#f5f1ed;
}

/* ── 主卡：工笔画风 ── */
.portrait-card{
  background:#fefcfa;
  border:1px solid #d8cdc3;
  border-radius:8px;padding:20px;margin-bottom:20px;position:relative;
  box-shadow:0 2px 8px rgba(26,22,20,0.08), 0 4px 16px rgba(26,22,20,0.04);
}
.portrait-card::before{
  content:'';position:absolute;top:8px;right:8px;width:60px;height:60px;
  background:radial-gradient(circle, rgba(232,196,205,0.15), transparent 70%);
  border-radius:50%;pointer-events:none;
}
.portrait-card .name{
  font-family:"Songti SC",serif;font-size:28px;font-weight:600;color:#1a1614;
  margin-bottom:8px;letter-spacing:.08em;
}
.portrait-card .title-line{
  font-size:11px;color:#7a9d8f;margin-bottom:16px;letter-spacing:.2em;
}
.portrait-card .meta{
  display:flex;gap:16px;font-size:11px;color:#5a534d;margin-bottom:16px;
  flex-wrap:wrap;
}
.portrait-card .meta span{display:flex;align-items:center;gap:4px}
.portrait-card .meta b{color:#7a9d8f;font-weight:600}
.tagcloud{display:flex;flex-wrap:wrap;gap:7px}
.tagcloud span{
  font-size:9px;padding:3px 10px;background:rgba(122,157,143,0.08);
  border:1px solid rgba(122,157,143,0.2);border-radius:4px;color:#7a9d8f;
}

/* ── Section 通用 ── */
.section{padding:22px 2px;border-bottom:1px solid rgba(122,157,143,0.12)}
.sec-label{
  font-family:"Songti SC",serif;font-size:13px;color:#7a9d8f;
  margin-bottom:14px;font-weight:600;letter-spacing:.12em;
  display:flex;align-items:center;gap:8px;
}
.sec-label::before{
  content:'•';color:#e8c4cd;font-size:16px;
}

/* ── 花笺条目 ── */
.petal-note{
  background:linear-gradient(135deg, rgba(232,196,205,0.06), transparent);
  border-left:2px solid #e8c4cd;
  padding:14px;margin-bottom:14px;border-radius:4px;
}
.petal-note .title{
  font-size:12px;font-weight:600;color:#e8c4cd;margin-bottom:6px;
  letter-spacing:.06em;
}
.petal-note .body{font-size:13px;line-height:1.8;color:#3a342e}

/* ── 月夜私语 ── */
.moonlight{
  margin:16px 2px 0;padding:20px 16px;position:relative;
  background:linear-gradient(135deg,rgba(122,157,143,0.08),transparent);
  border-left:3px solid #7a9d8f;border-radius:6px;
}
.moonlight::after{
  content:'☽';position:absolute;top:10px;right:14px;
  font-size:20px;color:#7a9d8f;opacity:0.2;
}
.moonlight p{
  font-family:"Songti SC",serif;font-size:14px;line-height:1.9;
  color:#2a241f;font-style:italic;
}
.moonlight .by{
  margin-top:12px;font-size:10px;color:#7a9d8f;letter-spacing:.2em;
  font-style:normal;text-align:right;
}

/* ── 底部印章 ── */
.footer{padding:28px 2px 0;text-align:center}
.footer .seal{
  width:50px;height:50px;margin:0 auto 12px;
  border:2px solid #e8c4cd;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-family:"Songti SC",serif;font-size:16px;color:#e8c4cd;
  font-weight:600;
}
.footer p{font-size:10px;color:#9a8e82;letter-spacing:.04em}
</style>
</head>
<body>
<div class="container">

  <div class="scroll-header">
    <div class="title">郡主画卷</div>
  </div>

  <div class="portrait-card">
    <div class="name">${name}</div>
    <div class="title-line">镇国将军府 · 清冷孤高</div>
    <div class="meta">
      <span><b>年岁</b> 二十四</span>
      <span><b>身份</b> 镇国郡主</span>
      <span><b>性情</b> 清冷自持</span>
    </div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="section">
    <div class="sec-label">权门身世</div>
    <div class="petal-note">
      <div class="title">将军府的明珠</div>
      <div class="body">生于权门，自幼看惯以情为饵的算计,早早学会不动声色。在满京华的权谋里独善其身，以疏离自保，对谁都淡淡的。</div>
    </div>
  </div>

  <div class="section">
    <div class="sec-label">心防初破</div>
    <div class="petal-note">
      <div class="title">唯你能叩开</div>
      <div class="body">她习惯了以疏离自保，可你的出现让这位孤高的郡主第一次乱了心。会为你破例、为你心软、为你在深宫算计里留一处退路。</div>
    </div>
    <div class="petal-note">
      <div class="title">月下海棠</div>
      <div class="body">她本欲拂袖而去，你一个趔趄，她却下意识伸手扶住，指尖触到你的手腕，僵了一瞬，竟没有收回。耳根泛起一丝极淡的红，声音软了下来。</div>
    </div>
    <div class="petal-note">
      <div class="title">铠甲之下</div>
      <div class="body">冷若冰霜是她的铠甲，而那点藏起来的温柔，只你一人有幸窥见。她会在深夜为你留一盏宫灯，会把你护在羽翼最深处，不让满京华的风霜碰到你分毫。</div>
    </div>
  </div>

  <div class="moonlight">
    <p>这满京华的算计我都应付得来，独独应付不来你的靠近。她别过脸，声音淡淡的：「罢了。你这般不设防，我不看着，不放心。今夜就留下吧——只此一次，下不为例。」</p>
    <div class="by">— 海棠花影下 · 月夜私语</div>
  </div>

  <div class="footer">
    <div class="seal">婉</div>
    <p>角色设定纯属虚构 与现实无关</p>
  </div>

</div>
</body>
</html>`

  return (
    <iframe
      ref={iframeRef}
      title={`${name} profile`}
      srcDoc={htmlContent}
      style={{
        width: '100%',
        height: `${height}px`,
        border: 'none',
        display: 'block',
        background: 'transparent',
      }}
      sandbox="allow-same-origin"
    />
  )
}

