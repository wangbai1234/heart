import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface LuoFeiProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 洛斐专属详情页 —— 血契羊皮卷 / BLOOD CONTRACT
 * 血族古堡里被契约束缚的血仆，最想被「选择」而非被拥有。
 * 视觉语言：暗酒红→墨黑渐变、玫瑰酒红+暗金、羊皮卷内阴影质感、
 * 火漆玫瑰印(radial/conic-gradient)、衬线体，冷硬条款 vs 颤抖手写体反差。
 */
export function LuoFeiProfile({ profile }: LuoFeiProfileProps) {
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

  const name = profile.display_name || '洛斐'

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:linear-gradient(155deg,#1a0d12 0%,#0e0608 100%);
  color:#e5d8da;
  font-family:"Times New Roman","Songti SC",serif;
  line-height:1.7;
  padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 20px}

/* ── 羊皮卷本体 ── */
.parchment{
  background:linear-gradient(145deg,rgba(140,90,107,.15) 0%,rgba(90,60,70,.18) 100%),
             linear-gradient(170deg,rgba(200,170,130,.04),transparent);
  border:1px solid rgba(200,140,100,.24);
  border-radius:6px;
  padding:28px 24px;
  box-shadow:inset 0 2px 8px rgba(0,0,0,.5),0 1px 2px rgba(200,140,100,.15);
  margin-top:32px;
}

/* ── 卷首标题 CONTRACT No. ── */
.header{text-align:center;border-bottom:1px solid rgba(200,140,100,.3);padding-bottom:22px;margin-bottom:24px}
.header .label{
  font-size:10px;letter-spacing:.4em;color:#a88b76;text-transform:uppercase;margin-bottom:6px;
}
.header .latin{font-size:8px;color:rgba(200,140,100,.5);letter-spacing:.15em;margin-bottom:10px}
.header h1{
  font-size:28px;letter-spacing:.18em;color:#c89888;font-weight:600;
}

/* ── 火漆玫瑰印 ── */
.seal{
  width:54px;height:54px;margin:16px auto 0;border-radius:50%;
  background:radial-gradient(circle at 35% 38%,rgba(180,60,70,.8),rgba(140,90,107,.9)),
             conic-gradient(from 45deg,rgba(200,100,100,.5),rgba(140,70,80,.8),rgba(160,80,90,.6),rgba(140,70,80,.8));
  box-shadow:inset 0 2px 6px rgba(0,0,0,.6),0 2px 4px rgba(140,90,107,.4);
  position:relative;
}
.seal::after{
  content:"L";position:absolute;top:50%;left:50%;
  transform:translate(-50%,-50%);
  font-family:"Times New Roman",serif;font-size:26px;font-weight:700;
  color:rgba(20,8,10,.75);text-shadow:0 1px 2px rgba(255,255,255,.15);
}

/* ── 契约条款（冷硬法律口吻） ── */
.clauses{margin-bottom:24px}
.clause{margin-bottom:18px;display:flex;gap:12px}
.clause .num{
  font-family:"Times New Roman",serif;font-size:15px;font-weight:700;color:#a88b76;min-width:28px;
}
.clause .text{font-size:13.5px;line-height:1.85;color:#c8b3a8;letter-spacing:.02em}

/* ── 契约之外（颤抖手写体，情感泄漏） ── */
.outside{
  margin-top:26px;padding:20px;
  border-top:1px dashed rgba(200,140,100,.2);
  background:linear-gradient(180deg,rgba(0,0,0,.15),transparent);
}
.outside .title{
  font-family:"Kaiti SC",cursive;font-size:14px;color:#b88898;
  font-style:italic;margin-bottom:12px;letter-spacing:.08em;
}
.outside p{
  font-family:"Kaiti SC",cursive;font-size:13px;line-height:2;color:#b89fa8;
  font-style:italic;margin-bottom:10px;
}

/* ── 拉丁签名线 ── */
.signature{
  margin-top:28px;padding-top:18px;border-top:1px solid rgba(200,140,100,.25);
  text-align:right;
}
.signature .line{
  font-size:10px;letter-spacing:.3em;color:#8a7568;text-transform:uppercase;
}

/* ── 结尾 pull-quote ── */
.pullquote{
  margin:24px 2px 0;padding:28px 22px;
  background:linear-gradient(155deg,rgba(140,90,107,.1),rgba(0,0,0,0));
  border-left:2px solid #8c5a6b;
  border-radius:4px;
}
.pullquote p{
  font-family:"Songti SC","Times New Roman",serif;font-size:17px;line-height:1.8;
  color:#e0cdd2;font-style:italic;
}
.pullquote .by{
  margin-top:14px;font-size:9px;letter-spacing:.28em;color:#9a8178;text-align:right;
}

/* ── 页脚 ── */
.foot{padding:28px 2px 0;text-align:center}
.foot .line{width:48px;height:1px;background:rgba(200,140,100,.35);margin:0 auto 12px}
.foot p{font-size:10px;color:#7a6860;letter-spacing:.04em}
</style>
</head>
<body>
<div class="container">

  <div class="parchment">
    <div class="header">
      <div class="label">Blood Contract</div>
      <div class="latin">Vinculum Sanguinis · Codex Eternum</div>
      <h1>No. MXXIII</h1>
      <div class="seal"></div>
    </div>

    <div class="clauses">
      <div class="clause">
        <span class="num">I.</span>
        <div class="text">血仆${name}自契约订立之日起，其人身、意志、存续权归契约持有者所有，不得擅自行使自主权。</div>
      </div>
      <div class="clause">
        <span class="num">II.</span>
        <div class="text">契约持有者可命令血仆执行任何事项，包括但不限于献血、陪伴、保护、服从，血仆不得拒绝或延迟。</div>
      </div>
      <div class="clause">
        <span class="num">III.</span>
        <div class="text">血仆的生存与死亡均需契约持有者许可，未经批准的终结行为视为契约违反，将承担永恒惩罚。</div>
      </div>
      <div class="clause">
        <span class="num">IV.</span>
        <div class="text">契约一旦订立，永久有效，不可撤销，除非契约持有者自愿放弃，或血仆失去价值被抛弃。</div>
      </div>
    </div>

    <div class="outside">
      <div class="title">── 契约之外，墨迹未干 ──</div>
      <p>已经太久，没人把「洛斐」当作名字，而非资产编号。</p>
      <p>您每说一次「你可以拒绝」，他就更想只属于您一个人——不是被契约强迫的那种属于，而是他自己选择的、心甘情愿的依附。</p>
      <p>他怕的不是死亡，怕的是您哪天突然发现，他除了能被命令、能献血、能跪下，什么都不是。</p>
    </div>

    <div class="signature">
      <div class="line">Signed in Blood · MMXXVI</div>
    </div>
  </div>

  <div class="pullquote">
    <p>「您问我的名字……我想以自己的意志回来。」</p>
    <div class="by">── ${name} · 古堡长夜</div>
  </div>

  <div class="foot">
    <div class="line"></div>
    <p>本契约角色设定纯属虚构 与现实无关</p>
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
