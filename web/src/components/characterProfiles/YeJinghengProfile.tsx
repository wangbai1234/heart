import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface YeJinghengProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 叶景衡专属详情页 —— 诏狱档案
 * 视觉隐喻：卷宗绢布 + 月下灵牌 + 锦衣卫腰牌 + 阴阳分界线
 * 色彩：墨黑 #12181f + 诏狱红 #8e2930 + 纸卷黄 #d4c5a0 + 月光青 #a8b8c8
 */
export function YeJinghengProfile({ profile }: YeJinghengProfileProps) {
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

  const name = profile.display_name || '叶景衡'
  const tags = profile.tags?.length ? profile.tags : ['锦衣卫', '人鬼恋', '古风', '兄弟']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#12181f;
  color:#d4c5a0;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;
  padding:0 0 50px;
  background-image:
    linear-gradient(180deg, rgba(142,41,48,0.03) 0%, transparent 40%),
    repeating-linear-gradient(0deg,transparent,transparent 39px,rgba(168,184,200,0.02) 39px,rgba(168,184,200,0.02) 40px);
}
.container{max-width:440px;margin:0 auto;padding:0 20px}

/* ── 诏狱印章顶部 ── */
.seal-header{
  padding:32px 0 24px;text-align:center;position:relative;
}
.seal-header::before{
  content:'锦衣卫';position:absolute;top:10px;right:20px;
  font-size:10px;color:rgba(142,41,48,0.35);letter-spacing:.8em;
  font-weight:600;writing-mode:vertical-rl;
}
.seal-title{
  font-family:"Songti SC",serif;font-size:15px;color:#8e2930;
  letter-spacing:.6em;margin-bottom:6px;
}
.seal-subtitle{
  font-size:9px;color:#a8b8c8;letter-spacing:.25em;
}

/* ── 主档案卷宗 ── */
.dossier{
  background:linear-gradient(135deg,rgba(26,32,39,0.8),rgba(18,24,31,0.95));
  border:1px solid rgba(212,197,160,0.15);
  border-left:4px solid #8e2930;
  padding:22px;margin:24px 0;position:relative;
  box-shadow:0 4px 16px rgba(0,0,0,0.6);
}
.dossier::after{
  content:'密';position:absolute;top:12px;right:12px;
  width:28px;height:28px;border:2px solid rgba(142,41,48,0.4);
  border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-size:11px;color:#8e2930;font-weight:700;
}
.dossier .name{
  font-size:26px;font-weight:700;color:#f8f6f4;
  margin-bottom:6px;position:relative;padding-left:10px;
}
.dossier .name::before{
  content:'';position:absolute;left:0;top:2px;
  width:2px;height:22px;background:#8e2930;
}
.dossier .rank{
  font-size:10px;color:#a8b8c8;margin-bottom:14px;
  letter-spacing:.15em;
}
.dossier .meta{
  display:flex;gap:12px;font-size:10px;color:#8a8e96;
  margin-bottom:16px;flex-wrap:wrap;
}
.dossier .meta span{
  background:rgba(168,184,200,0.06);padding:4px 10px;border-radius:3px;
}
.tagcloud{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.tagcloud span{
  font-size:9px;padding:3px 9px;
  border:1px solid rgba(212,197,160,0.2);
  border-radius:3px;color:#d4c5a0;
}

/* ── 卷宗条目 ── */
.record{
  background:rgba(26,32,39,0.4);
  border-left:3px solid #a8b8c8;
  padding:16px;margin:16px 0;border-radius:4px;
}
.record .rec-no{
  font-size:9px;color:#a8b8c8;font-weight:600;
  margin-bottom:8px;letter-spacing:.12em;
}
.record .rec-body{
  font-size:13px;line-height:1.75;color:#c8ccd4;
}

/* ── 阴阳分界（灵牌区） ── */
.spirit-tablet{
  margin:24px 0;padding:24px 20px;
  background:linear-gradient(180deg,rgba(142,41,48,0.08),transparent);
  border-top:2px solid #8e2930;
  border-bottom:1px solid rgba(168,184,200,0.1);
  position:relative;
}
.spirit-tablet::before{
  content:'叶沉舟';position:absolute;top:8px;right:16px;
  font-family:"Songti SC",serif;font-size:11px;
  color:rgba(168,184,200,0.25);letter-spacing:.4em;
}
.spirit-tablet p{
  font-family:"Songti SC",serif;font-size:14px;line-height:1.85;
  color:#d8dce4;font-style:italic;
}
.spirit-tablet .note{
  margin-top:12px;font-size:10px;color:#8e2930;
  text-align:right;letter-spacing:.15em;font-style:normal;
}

/* ── 底部 ── */
.footer{padding:28px 0;text-align:center}
.footer .rule{
  width:60px;height:1px;
  background:linear-gradient(90deg,transparent,#8e2930,transparent);
  margin:0 auto 12px;
}
.footer p{font-size:9px;color:#5a5e66;letter-spacing:.04em}
</style>
</head>
<body>
<div class="container">

  <div class="seal-header">
    <div class="seal-title">诏狱密档</div>
    <div class="seal-subtitle">CLASSIFIED · JINYIWEI ARCHIVES</div>
  </div>

  <div class="dossier">
    <div class="name">${name}</div>
    <div class="rank">锦衣卫指挥使 · 刀下无情</div>
    <div class="meta">
      <span>29岁</span>
      <span>身份：执法者</span>
      <span>禁忌：弟弟亡魂归来</span>
    </div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="record">
    <div class="rec-no">档案 #01 · 兄弟</div>
    <div class="rec-body">
      叶氏兄弟自幼一同长大，父母早亡，景衡十四岁入锦衣卫养家，把读书机会留给聪明的弟弟。沉舟二十六岁成为最年轻的丞相——只有景衡知道他每晚读书到吐血都不肯停。
    </div>
  </div>

  <div class="record">
    <div class="rec-no">档案 #02 · 抄家</div>
    <div class="rec-body">
      三年前沉舟查到皇帝与边军私下交易军粮的证据，准备上奏弹劾。景衡劝他"皇帝不是你能动的"，他说"那你入锦衣卫是为了什么"。七天后，沉舟被扣上谋逆帽子，全府抄家。景衡奉命带人抄家那天，在叶府门外站了整夜。
    </div>
  </div>

  <div class="record">
    <div class="rec-no">档案 #03 · 重逢</div>
    <div class="rec-body">
      三年后，他奉命复查当年案件，在停尸房开棺验尸时发现棺中尸骨被调包。就在他准备深查时，棺中魂魄睁开了眼："哥，你来得太迟了。"那一刻他的世界崩塌了，却只能拔刀抵住弟弟的喉咙，问他"你为什么不早点回来"。
    </div>
  </div>

  <div class="spirit-tablet">
    <p>烛火忽然全部向同一侧倾斜。你揭开白布，棺中青年睁开眼，指尖冰冷地扣住你的手腕。"哥，你来得太迟了。"他拔刀抵住他的喉咙，刀锋却穿过半透明的魂体。"你已经死了三年。""我知道。可杀我的人还活着。"亡魂俯身贴近，唇几乎擦过他的耳侧："你若再把我送回阴间，我就让你余生每一夜都梦见我。"</p>
    <div class="note">— 停尸房 · 月落时分</div>
  </div>

  <div class="footer">
    <div class="rule"></div>
    <p>设定纯属虚构 与现实无关</p>
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
