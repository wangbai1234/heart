import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface JiangRanProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 江燃专属详情页 —— 深夜酒单 / COCKTAIL MENU
 * 视觉语言：霓虹暧昧 + 酒杯剪影 + 调酒配方卡 + 暖光治愈
 * 夜色调酒师美学：琥珀金 + 深红 + 暖橙，流动液体质感 + 暧昧与认真的反差
 */
export function JiangRanProfile({ profile }: JiangRanProfileProps) {
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

  const name = profile.display_name || '江燃'
  const tags = profile.tags?.length ? profile.tags : ['女性向', '都市', '夜色', '调酒师', '暧昧', '治愈']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#1a1614;
  color:#f0e8e0;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.65;
  padding:0 0 40px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}

/* ── 霓虹招牌 ── */
.header{
  margin:20px 0;padding:28px 20px;
  background:linear-gradient(135deg,rgba(210,105,80,0.12),rgba(26,22,20,0.8));
  border:1px solid rgba(210,105,80,0.2);
  border-radius:12px;
  box-shadow:0 4px 20px rgba(210,105,80,0.15),inset 0 1px 0 rgba(255,255,255,0.05);
  position:relative;
}
.header::before{
  content:"";position:absolute;
  top:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,transparent,rgba(210,105,80,0.6) 50%,transparent);
}
.bar-name{
  font-family:"Courier New",monospace;font-size:10px;
  color:#d26950;letter-spacing:.35em;text-transform:uppercase;
}
.name{
  font-size:38px;font-weight:700;
  background:linear-gradient(120deg,#f5b88a,#d26950);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;
  margin:10px 0 6px;letter-spacing:.1em;
}
.role{font-size:12px;color:#b8a398;letter-spacing:.1em;margin-bottom:14px}
.tags{display:flex;flex-wrap:wrap;gap:7px}
.tags span{
  font-size:10px;padding:4px 10px;
  background:rgba(210,105,80,0.1);border:1px solid rgba(210,105,80,0.3);
  border-radius:4px;color:#e8a58a;
}

/* ── 调酒师档案 ── */
.profile{
  margin:24px 0;padding:20px;
  background:rgba(42,38,36,0.6);
  border-left:3px solid #d26950;border-radius:6px;
}
.sec-title{
  font-family:"Courier New",monospace;font-size:11px;
  color:#d26950;letter-spacing:.28em;text-transform:uppercase;
  margin-bottom:14px;padding-bottom:6px;
  border-bottom:1px dashed rgba(210,105,80,0.25);
}
.bio{font-size:13px;line-height:1.8;color:#d4c8be}

/* ── 酒单 / 配方卡 ── */
.menu{margin:24px 0}
.cocktail{
  margin-bottom:14px;padding:16px;
  background:linear-gradient(130deg,rgba(210,105,80,0.08),rgba(42,38,36,0.5));
  border:1px solid rgba(210,105,80,0.15);border-radius:6px;
}
.cocktail .title{
  font-size:14px;font-weight:600;color:#f5b88a;
  margin-bottom:5px;letter-spacing:.08em;
}
.cocktail .recipe{
  font-size:11px;color:#a89888;
  font-style:italic;margin-bottom:8px;
}
.cocktail .note{font-size:12px;line-height:1.6;color:#c8b8a8}

/* ── 吧台留言 ── */
.bartender-note{
  margin:28px 8px 0;padding:22px 18px;
  background:linear-gradient(145deg,rgba(245,184,138,0.08),rgba(26,22,20,0.6));
  border:1px solid rgba(210,105,80,0.2);
  border-left:3px solid #d26950;border-radius:6px;
}
.bartender-note p{
  font-family:"Kaiti SC","STKaiti",serif;
  font-size:14px;line-height:1.85;color:#e8dcd0;
  margin-bottom:10px;
}
.bartender-note .sign{
  font-size:11px;text-align:right;
  color:#9a8a7a;letter-spacing:.08em;margin-top:8px;
}

/* ── 页脚 ── */
.foot{padding:28px 0 0;text-align:center}
.foot .divider{
  width:50px;height:2px;background:#d26950;
  opacity:0.3;margin:0 auto 10px;
}
.foot p{font-size:10px;color:#6a5e54;letter-spacing:.06em}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="bar-name">AFTERTASTE · 深夜酒吧</div>
    <div class="name">${name}</div>
    <div class="role">王牌调酒师 · 不想只被夜晚记住的人</div>
    <div class="tags">${tagCloud}</div>
  </div>

  <div class="profile">
    <div class="sec-title">调酒师档案 · Bartender Profile</div>
    <p class="bio">二十五岁 · 红发挑染 · 金链贴着锁骨 · 白衬衫和黑马甲穿得松垮 · 太会哄人，所以没人相信他也会认真</p>
  </div>

  <div class="menu">
    <div class="sec-title">今夜酒单 · Tonight's Menu</div>
    <div class="cocktail">
      <div class="title">暧昧 · Ambiguity</div>
      <div class="recipe">配方: 游刃有余 + 察言观色 + 笑换小费</div>
      <div class="note">他会撩、会哄、会让气氛变得暧昧。这是他在夜色里的生存技能，也是他最怕被看穿的伪装。</div>
    </div>
    <div class="cocktail">
      <div class="title">温水 · Warmth</div>
      <div class="recipe">配方: 收起笑脸 + 安静心疼 + 低度替换</div>
      <div class="note">真正心疼你时，他会把最烈的酒换成温水，收起玩笑，安静地盯着你的情绪不对。</div>
    </div>
    <div class="cocktail">
      <div class="title">认真 · Sincerity</div>
      <div class="recipe">配方: 不只想赢一晚心动 + 想被白天也记得</div>
      <div class="note">你以为他是夜色里的过客，他却第一次想被一个人白天也记得。他会记住你所有情绪不对的小动作。</div>
    </div>
  </div>

  <div class="bartender-note">
    <p>打烊咯。不过，可以为你破例，再调最后一杯。</p>
    <p>你今天笑得不太对。别喝酒了，喝这个——我这人最会哄客人开心，可你是头一个，让我想收起笑脸，好好心疼的。</p>
    <p>今晚想喝什么？甜一点，还是认真一点。</p>
    <div class="sign">— 写在吧台打烊后，暖光只剩一盏</div>
  </div>

  <div class="foot">
    <div class="divider"></div>
    <p>AFTERTASTE · 深夜酒单 · 角色设定纯属虚构</p>
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
