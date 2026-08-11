import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface VitoRosettiProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 维托·罗塞蒂专属详情页 —— 威尼斯拳场后台 · 地下拳手档案
 * 视觉隐喻：拳场海报、血渍绷带、金链、威尼斯水城暗巷、赔率表
 * 色彩：暗砖红 + 金 + 铁锈灰 + 冷蓝光，粗粝野性
 */
export function VitoRosettiProfile({ profile }: VitoRosettiProfileProps) {
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

  const name = profile.display_name || '维托'
  const age = 29
  const tags = profile.tags?.length ? profile.tags : ['女性向', '异国', '拳手', '野性', '救赎', '危险关系']
  const tagCloud = tags.map((t) => `#${t}`).join('&nbsp;&nbsp;')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#1a1412;
  color:#d4c4b8;
  font-family:"Georgia","Times New Roman",serif;
  line-height:1.8;
  padding:0 0 48px;
}
.container{max-width:420px;margin:0 auto;padding:0 20px}

/* ── 拳场海报头 ── */
.header{
  padding:28px 0 20px;
  text-align:center;
  border-bottom:3px solid #b8860b;
  background:linear-gradient(180deg,rgba(184,134,11,0.08),transparent);
}
.poster-title{
  font-size:28px;font-weight:700;color:#b8860b;letter-spacing:.4em;
  text-transform:uppercase;margin-bottom:8px;
  text-shadow:2px 2px 4px rgba(0,0,0,0.5);
}
.poster-sub{
  font-size:11px;color:#9a8976;letter-spacing:.5em;text-transform:uppercase;
}
.fighter-badge{
  display:inline-block;margin-top:14px;
  padding:8px 18px;
  background:linear-gradient(135deg,#8b4513,#6b3410);
  border:2px solid #b8860b;
  border-radius:4px;
  font-size:13px;font-weight:600;color:#f4e4d0;letter-spacing:.2em;
}

/* ── 赔率表卡 ── */
.odds-card{
  margin:28px 0;
  background:rgba(50,40,35,0.7);
  border:2px solid #6b5447;
  padding:18px;
  border-radius:6px;
}
.odds-label{
  font-size:11px;color:#b8860b;font-weight:600;letter-spacing:.3em;margin-bottom:12px;
  text-transform:uppercase;
}
.odds-row{
  display:flex;margin-bottom:8px;font-size:13px;
}
.odds-row .label{
  color:#9a8976;min-width:90px;font-weight:500;
}
.odds-row .value{
  color:#d4c4b8;flex:1;
}

/* ── 战绩记录 ── */
.record-box{
  margin:24px 0;
  background:rgba(139,69,19,0.25);
  border-left:4px solid #b8860b;
  padding:20px;
  border-radius:6px;
}
.record-label{
  font-size:11px;color:#b8860b;font-weight:600;letter-spacing:.3em;margin-bottom:14px;
}
.record-text{
  font-size:14px;line-height:2.1;color:#c8b8a8;text-align:justify;
  margin-bottom:14px;
}

/* ── 金链高亮框 ── */
.chain-box{
  margin:26px 0;
  background:linear-gradient(135deg,rgba(184,134,11,0.2),rgba(139,69,19,0.3));
  border:2px solid #b8860b;
  padding:22px;
  border-radius:8px;
  position:relative;
  box-shadow:0 4px 16px rgba(184,134,11,0.2);
}
.chain-box::before{
  content:'⛓️';
  position:absolute;top:10px;right:14px;
  font-size:24px;opacity:0.4;
}
.chain-text{
  font-size:15px;line-height:2.2;color:#f4e4d0;font-weight:500;
  text-align:center;font-style:italic;
}

/* ── 伤痕分割线 ── */
.scar-divider{
  margin:28px 0;
  height:2px;
  background:linear-gradient(90deg,transparent,#8b4513 20%,#8b4513 80%,transparent);
}

/* ── 标签 ── */
.tags{
  margin:24px 0;
  background:rgba(50,40,35,0.5);
  padding:18px;
  border-radius:6px;
  border:1px solid #6b5447;
}
.tags-label{
  font-size:11px;color:#9a8976;font-weight:600;letter-spacing:.3em;margin-bottom:10px;
}
.tags-cloud{
  font-size:12px;line-height:2.2;color:#b8a998;letter-spacing:.05em;
}

/* ── 后台笔记 ── */
.backstage-note{
  margin:24px 0;
  background:rgba(30,24,20,0.8);
  border:2px dashed #6b5447;
  padding:20px;
  border-radius:8px;
}
.note-label{
  font-size:11px;color:#b8860b;font-weight:600;letter-spacing:.3em;margin-bottom:12px;
  text-align:center;
}
.note-text{
  font-size:13px;line-height:2.2;color:#a89888;text-align:justify;
}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="poster-title">VITO</div>
    <div class="poster-sub">Underground Fighter · Venezia</div>
    <div class="fighter-badge">ROSETTI</div>
  </div>

  <div class="odds-card">
    <div class="odds-label">Fighter Record</div>
    <div class="odds-row"><span class="label">Nome</span><span class="value">${name} Rosetti</span></div>
    <div class="odds-row"><span class="label">Età</span><span class="value">${age} anni</span></div>
    <div class="odds-row"><span class="label">Origine</span><span class="value">Venezia, Italia</span></div>
    <div class="odds-row"><span class="label">Fighting Style</span><span class="value">Street · Underground</span></div>
    <div class="odds-row"><span class="label">Status</span><span class="value">Most Valuable Fighter</span></div>
  </div>

  <div class="record-box">
    <div class="record-label">档案 · Il Combattente</div>
    <div class="record-text">
      金发潮湿凌乱，金饰和旧伤贴在皮肤上，像从教堂阴影里走出的野兽。
      他十四岁第一次打黑拳，不是为了荣耀，是为了给母亲买药；
      后来一份藏着陷阱的合同把他困在地下拳场，赢得越多，欠过去越深。
    </div>
    <div class="record-text">
      他讨厌怜悯，因为怜悯从没替他还过债。你第一次在后台替他处理伤口，
      没有说他厉害，只说「你今天不该再打了」。从那以后，他开始想活着走下拳台，
      不为赔率，只为有人在后台等他。
    </div>
  </div>

  <div class="chain-box">
    <div class="chain-text">
      他们押我赢，我只想听你说，活着回来。
    </div>
  </div>

  <div class="scar-divider"></div>

  <div class="record-box">
    <div class="record-label">性格 · Carattere</div>
    <div class="record-text">
      桀骜、粗粝、防备心重，厌恶被怜悯，却对真正的心疼没有抵抗力。
      他不说漂亮话，也不懂精致浪漫，只会用身体挡在你和危险之间。
    </div>
    <div class="record-text">
      他的核心不是野性，而是低到尘埃里的自我价值。
      你若让他相信自己不必流血也值得被爱，他会为了你第一次选择不上拳台。
    </div>
  </div>

  <div class="tags">
    <div class="tags-label">Tags</div>
    <div class="tags-cloud">${tagCloud}</div>
  </div>

  <div class="backstage-note">
    <div class="note-label">后台笔记 · Nota Privata</div>
    <div class="note-text">
      维托出生在威尼斯贫民区，父亲因赌债失踪，母亲病逝前让他离开水城。
      他没有走，因为债还没完，也因为他不知道离开拳台以后自己还剩什么。
      一次拳台事故让对手再没醒来，所有人为爆冷赔率欢呼，只有他在后台洗了很久的手。
      你让他第一次想活着走下拳台，而不是只赢下去。
    </div>
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

