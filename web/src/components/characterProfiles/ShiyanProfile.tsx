import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface ShiyanProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 时衍专属详情页 —— 旅行手账 / TRAVEL JOURNAL
 * 青梅竹马陪你走完整段日本行，在富士山下的缆车里挑明多年暧昧。
 * 视觉语言：深海蓝 + 富士雪顶暖阳金，手账/行程票根格式，
 * 一段贴着两人一起挑的条纹围巾意象，末尾停在那句迟到多年的告白。
 */
export function ShiyanProfile({ profile }: ShiyanProfileProps) {
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

  const name = profile.display_name || '时衍'
  const tags = profile.tags?.length ? profile.tags : ['全性向', '限左', '青梅竹马', '校园']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:
    radial-gradient(ellipse 92% 34% at 50% 0%,rgba(224,196,140,.16),transparent 58%),
    #0c1420;
  color:#c6d3e0;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}
.serif{font-family:"Times New Roman","Songti SC",serif}
.mono{font-family:"SF Mono","Menlo",monospace}

/* ── 手账封面抬头 ── */
.header{
  padding:26px 0 18px;border-bottom:1px solid rgba(224,196,140,.28);text-align:center;
}
.header .bar{
  font-size:10px;letter-spacing:.4em;color:#8aa0b8;
  text-transform:uppercase;margin-bottom:9px;
}
.header .title{
  font-family:"Times New Roman",serif;
  font-size:27px;font-weight:700;color:#e6d3a6;
  letter-spacing:.08em;margin-bottom:7px;text-shadow:0 0 20px rgba(224,196,140,.3);
}
.header .route{font-size:12px;color:#7e93a8;letter-spacing:.14em}

/* ── section 通用 ── */
.section{padding:22px 0}
.section+.section{border-top:1px solid rgba(120,150,185,.12)}
.sec-head{
  font-size:9px;letter-spacing:.34em;color:#9fb6cc;
  text-transform:uppercase;margin-bottom:14px;font-weight:700;
}

/* ── 登机牌 ── */
.pass{
  padding:0;border-radius:8px;overflow:hidden;
  background:linear-gradient(135deg,rgba(20,32,48,.95),rgba(14,22,34,.95));
  border:1px solid rgba(120,150,185,.24);position:relative;
}
.pass .strip{
  background:linear-gradient(90deg,rgba(224,196,140,.9),rgba(224,196,140,.5));
  padding:7px 16px;display:flex;justify-content:space-between;align-items:center;
}
.pass .strip .brand{font-size:10px;letter-spacing:.24em;color:#1a2434;font-weight:700}
.pass .strip .cls{font-size:9px;letter-spacing:.14em;color:#2a3648;font-weight:700}
.pass .body{padding:15px 16px}
.pass .lane{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:12px}
.pass .code{font-family:"SF Mono","Menlo",monospace;font-size:24px;color:#e6d3a6;font-weight:700;letter-spacing:.04em}
.pass .arrow{color:#7e93a8;font-size:14px;padding:0 8px 3px}
.pass .sub{font-size:9px;letter-spacing:.1em;color:#7e93a8;margin-top:2px}
.pass .row{display:flex;padding:6px 0;font-size:13px;border-top:1px dotted rgba(120,150,185,.16)}
.pass .k{color:#7e93a8;min-width:64px;letter-spacing:.04em;font-size:11px}
.pass .v{color:#c6d3e0;flex:1}

/* ── 行程票根 ── */
.legs{margin-top:4px}
.leg{
  display:flex;align-items:baseline;gap:12px;
  padding:11px 0;border-bottom:1px solid rgba(120,150,185,.1);
}
.leg .no{font-family:"SF Mono","Menlo",monospace;font-size:12px;color:#9a8a5e;min-width:30px}
.leg .body{flex:1}
.leg .body .t{font-size:14px;color:#d0dae6;font-weight:600}
.leg .body .d{font-size:11px;color:#7e93a8;margin-top:2px;line-height:1.5}
.leg.final{
  background:linear-gradient(90deg,rgba(224,196,140,.1),transparent);
  border-radius:4px;padding:14px 12px;border-bottom:none;margin-top:6px;
  border:1px dashed rgba(224,196,140,.4);
}
.leg.final .no{color:#e6d3a6}
.leg.final .body .t{color:#f0dcac}
.leg.final .badge{
  font-size:9px;letter-spacing:.1em;color:#e6d3a6;
  border:1px solid rgba(224,196,140,.5);border-radius:3px;padding:2px 6px;
  margin-left:8px;vertical-align:middle;
}

/* ── 围巾便签（一起挑的那条） ── */
.scarf{
  margin-top:6px;padding:16px 16px;border-radius:6px;
  background:
    repeating-linear-gradient(135deg,rgba(120,150,185,.1) 0 10px,rgba(224,196,140,.06) 10px 20px);
  border:1px solid rgba(120,150,185,.2);
}
.scarf .tag{font-size:10px;letter-spacing:.14em;color:#9fb6cc;margin-bottom:8px;text-transform:uppercase}
.scarf p{font-size:12.5px;color:#b8c6d4;line-height:1.8}

/* ── 手记 ── */
.note{
  margin:24px 0;padding:20px 18px;
  border-top:1px dashed rgba(224,196,140,.24);
  background:linear-gradient(180deg,rgba(224,196,140,.05),transparent);
}
.note .label{
  font-family:"Kaiti SC",cursive;font-size:12px;color:#e6d3a6;
  font-style:italic;margin-bottom:12px;letter-spacing:.06em;
}
.note p{
  font-family:"Kaiti SC",cursive;font-size:13.5px;line-height:2;
  color:#aebfce;font-style:italic;margin-bottom:9px;
}

/* ── 结尾 pull-quote ── */
.pullquote{
  margin:22px 2px 0;padding:26px 20px;
  background:linear-gradient(145deg,rgba(224,196,140,.12),transparent);
  border-left:2px solid #e6d3a6;border-radius:4px;
}
.pullquote p{
  font-family:"Times New Roman","Songti SC",serif;
  font-size:17px;line-height:1.85;color:#eef2f6;font-style:italic;
}
.pullquote .by{
  margin-top:14px;font-size:9px;letter-spacing:.22em;color:#7e93a8;text-align:right;
}

/* ── 标签+页脚 ── */
.tagcloud{margin-top:18px;display:flex;flex-wrap:wrap;gap:8px}
.tagcloud span{
  font-size:11px;padding:4px 10px;
  border:1px solid rgba(120,150,185,.3);border-radius:2px;
  color:#9fb6cc;letter-spacing:.05em;
}
.foot{padding:24px 2px 0;text-align:center}
.foot .line{width:40px;height:1px;background:rgba(224,196,140,.35);margin:0 auto 12px}
.foot p{font-size:10px;color:#5a6c80;letter-spacing:.04em}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="bar">Travel Journal · 陪你走完这一程</div>
    <div class="title">${name}</div>
    <div class="route">青梅竹马 · 一起长大 · 从未挑明</div>
  </div>

  <div class="section">
    <div class="sec-head">Boarding Pass · 这趟旅程</div>
    <div class="pass">
      <div class="strip"><span class="brand">ITINERARY · 假期同行</span><span class="cls">CLASS · 心照不宣</span></div>
      <div class="body">
        <div class="lane">
          <div><div class="code">HOME</div><div class="sub">你我一起长大的城市</div></div>
          <div class="arrow">✈</div>
          <div style="text-align:right"><div class="code">FUJI</div><div class="sub">富士山下 · 缆车</div></div>
        </div>
        <div class="row"><span class="k">同行者</span><span class="v">${name} · 你的青梅竹马</span></div>
        <div class="row"><span class="k">造型</span><span class="v">黑发蓝眸 · 那条一起挑的条纹围巾</span></div>
        <div class="row"><span class="k">此行目的</span><span class="v">名义上是旅游 · 其实是来把话说清楚</span></div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="sec-head">Route · 一路走来</div>
    <div class="legs">
      <div class="leg"><span class="no">01</span><span class="body"><span class="t">机场接机</span><span class="d">隔了海和时差的重逢 · 他先一步接过你的行李</span></span></div>
      <div class="leg"><span class="no">02</span><span class="body"><span class="t">浅草 · 镰仓的海</span><span class="d">朝夕相处的几天 · 那点暧昧一路发酵</span></span></div>
      <div class="leg"><span class="no">03</span><span class="body"><span class="t">京都的巷子</span><span class="d">他自然地帮你挡人 · 记得你每一个喜好</span></span></div>
      <div class="leg final"><span class="no">◎</span><span class="body"><span class="t">富士山缆车<span class="badge">TERMINAL · 告白</span></span><span class="d">空荡的车厢 · 他终于不想再假装只是青梅竹马</span></span></div>
    </div>
  </div>

  <div class="section">
    <div class="sec-head">The Scarf · 一起挑的那条围巾</div>
    <div class="scarf">
      <div class="tag">分别前一晚 · 他留给你的</div>
      <p>高中你去日本留学，分别前一晚他什么都没说，只把这条我们一起挑的条纹围巾留给了你。这些年隔着海，他每天想问的是"你想我吗"，发出去的却永远是"今天过得怎么样"。</p>
    </div>
  </div>

  <div class="note">
    <div class="label">── 没说出口的那些话 · 手记 ──</div>
    <p>从小别人就说我们是一对，那句玩笑话在我心里悄悄生了根。</p>
    <p>我怕挑破了，连现在这点联系都保不住，所以一直躲在"青梅竹马"后面。</p>
    <p>可你在那边待得越久，我越怕那个"回国"永远不会来。这次我飞过来，只想把话说清楚。</p>
  </div>

  <div class="pullquote">
    <p>「你会回国读大学吗？<br>……如果你要留在日本，我可以申请早稻田。<br>这次，我不想再假装只是青梅竹马了。」</p>
    <div class="by">── ${name} · 富士山缆车</div>
  </div>

  <div class="tagcloud">${tagCloud}</div>
  <div class="foot">
    <div class="line"></div>
    <p>本手账角色设定纯属虚构 与现实无关</p>
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
