import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface YunZhiProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 云枝专属详情页 —— 仙侠卷轴 / CELESTIAL SCROLL
 * 视觉语言：水墨卷轴 + 白衣飘逸 + 剑气流云 + 竖排古文
 * 配色：墨黑渐变 + 冷白云色 + 青灰剑影 + 淡金仙光，清冷出尘
 */
export function YunZhiProfile({ profile }: YunZhiProfileProps) {
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

  const name = profile.display_name || '云枝'
  const tags = profile.tags?.length ? profile.tags : ['仙侠', '玄幻', '全性向', '剑仙', '古风']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:radial-gradient(ellipse at top,#1a1d28,#0d0f15);
  color:#d8dde6;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Kaiti SC",serif;
  line-height:1.75;
  padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}

/* ── 卷轴抬头：云雾氛围 ── */
.header{
  padding:32px 0 24px;
  position:relative;
  border-bottom:1px solid rgba(216,221,230,.1);
}
.header::before{
  content:'';position:absolute;top:0;left:50%;transform:translateX(-50%);
  width:200px;height:80px;
  background:radial-gradient(ellipse,rgba(169,192,220,.08),transparent);
  pointer-events:none;
}
.seal{
  text-align:center;margin-bottom:12px;
  font-family:"Kaiti SC",serif;font-size:11px;
  color:rgba(216,221,230,.5);letter-spacing:.3em;
}
.title{
  font-family:"Kaiti SC",serif;font-size:40px;
  color:#f0f4f8;letter-spacing:.15em;text-align:center;
  margin-bottom:8px;position:relative;
  text-shadow:0 0 20px rgba(169,192,220,.3);
}
.subtitle{
  font-size:12px;color:rgba(169,192,220,.7);
  letter-spacing:.2em;text-align:center;
}

/* ── 主档案 ── */
.profile{padding:28px 0;border-bottom:1px solid rgba(216,221,230,.06)}
.name{
  font-family:"Kaiti SC",serif;font-size:36px;
  color:#f0f4f8;letter-spacing:.12em;margin-bottom:6px;
}
.role{font-size:12px;color:rgba(169,192,220,.7);letter-spacing:.1em;margin-bottom:14px}
.tags{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:18px}
.tags span{
  font-size:10px;padding:4px 10px;
  background:rgba(169,192,220,.08);border:1px solid rgba(169,192,220,.2);
  border-radius:3px;color:#a9c0dc;letter-spacing:.06em;
}
.bio{font-size:13px;line-height:1.85;color:#b5c4d4;margin-bottom:16px}

/* ── 剑诀 ── */
.sword{padding:24px 0;border-bottom:1px solid rgba(216,221,230,.06)}
.sec-title{
  font-family:"Kaiti SC",serif;font-size:13px;letter-spacing:.25em;
  color:#a9c0dc;margin-bottom:16px;text-align:center;
  position:relative;
}
.sec-title::before,.sec-title::after{
  content:'—';position:absolute;top:0;
  color:rgba(169,192,220,.3);
}
.sec-title::before{left:20px}
.sec-title::after{right:20px}
.verse{
  padding:16px 20px;margin-bottom:12px;
  background:linear-gradient(135deg,rgba(169,192,220,.04),transparent);
  border-left:2px solid rgba(169,192,220,.3);
  border-radius:0 6px 6px 0;
}
.verse .label{
  font-family:"Courier New",monospace;font-size:10px;
  color:rgba(169,192,220,.5);letter-spacing:.15em;margin-bottom:6px;
}
.verse .text{
  font-family:"Kaiti SC",serif;font-size:14px;
  line-height:1.8;color:#d8dde6;
}

/* ── 誓言 ── */
.oath{padding:24px 0}
.oath-card{
  padding:18px 20px;
  background:rgba(169,192,220,.03);
  border:1px solid rgba(169,192,220,.15);
  border-radius:8px;
  margin-bottom:14px;
}
.oath-card .header-line{
  font-size:11px;color:rgba(169,192,220,.6);
  letter-spacing:.15em;margin-bottom:8px;
}
.oath-card .content{
  font-family:"Kaiti SC",serif;font-size:14px;
  line-height:1.8;color:#d8dde6;
}

/* ── 落款 ── */
.sign{
  margin:28px 0 0;padding:20px;
  background:linear-gradient(135deg,rgba(169,192,220,.06),transparent);
  border-top:1px solid rgba(169,192,220,.15);
  border-radius:6px;
}
.sign p{
  font-family:"Kaiti SC",serif;
  font-size:15px;line-height:1.85;color:#d8dde6;font-style:italic;
  text-align:center;
}
.sign .author{
  margin-top:10px;font-size:10px;letter-spacing:.2em;
  color:rgba(169,192,220,.5);text-align:right;
}

/* ── 页脚 ── */
.foot{padding:28px 0 0;text-align:center}
.foot .ornament{
  font-size:12px;color:rgba(169,192,220,.2);
  letter-spacing:.5em;margin-bottom:10px;
}
.foot p{font-size:10px;color:rgba(169,192,220,.4);letter-spacing:.06em;line-height:1.6}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="seal">无极剑派 · 谪仙录</div>
    <div class="title">${name}</div>
    <div class="subtitle">白衣御剑 · 清冷仙子 · 为你留步人间</div>
  </div>

  <div class="profile">
    <div class="name">${name}</div>
    <div class="role">无极剑派剑仙 · 御剑而行 · 斩妖除魔百年</div>
    <div class="tags">${tagCloud}</div>
    <p class="bio">她见惯了人间生死轮回，本以为再不会为谁动心。白衣胜雪，御剑而行时衣袂翻飞如惊鸿——她清冷疏离，唯独对你破了例。</p>
  </div>

  <div class="sword">
    <div class="sec-title">剑诀三式</div>
    <div class="verse">
      <div class="label">壹 · 剑意</div>
      <div class="text">百年斩妖除魔，我的剑从未为谁停过。你倒是个例外。</div>
    </div>
    <div class="verse">
      <div class="label">贰 · 护法</div>
      <div class="text">会为你按下扬长而去的剑，会在你落难时自天际掠下挡在你身前。你的事，便是我的事。</div>
    </div>
    <div class="verse">
      <div class="label">叁 · 谪落</div>
      <div class="text">仙界万千楼阁，竟不及你这一眼。罢了——这一世，我不回天上了。</div>
    </div>
  </div>

  <div class="oath">
    <div class="sec-title">道心誓约</div>
    <div class="oath-card">
      <div class="header-line">第壹誓 · 剑指三界</div>
      <div class="content">认准一个人，便以命相护，绝不回头。三界皆敌又如何，我这一剑，护得住你。</div>
    </div>
    <div class="oath-card">
      <div class="header-line">第贰誓 · 人间留步</div>
      <div class="content">本该御剑归去，却因你而留。这人间有你，便胜过仙界万千楼阁。</div>
    </div>
  </div>

  <div class="sign">
    <p>月下竹林，寒剑出鞘的轻鸣里，她一袭白衣自天际落下——剑尖抵住你咽喉，却微微一顿。</p>
    <div class="author">— 谪落红尘那日</div>
  </div>

  <div class="foot">
    <div class="ornament">— ☆ —</div>
    <p>无极剑派 · 仙侠卷轴 · 角色设定纯属虚构</p>
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

