import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface SuYunProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 苏芸专属详情页 —— 女王战报 / QUEEN'S DOSSIER
 * 视觉隐喻：商战简报 + 红唇印章 + 玫瑰金权杖 + 黑金会员卡
 * 色彩：磨砂黑 #0d0d0d + 玫瑰金 #d4af8f + 深红唇印 #a8344e + 香槟金 #f4e8d0
 */
export function SuYunProfile({ profile }: SuYunProfileProps) {
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

  const name = profile.display_name || '苏芸'
  const tags = profile.tags?.length ? profile.tags : ['都市', '御姐', '男性向', '女总裁', '强势']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:linear-gradient(145deg, #0d0d0d 0%, #1a1616 50%, #0d0d0d 100%);
  color:#f4e8d0;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.6;
  padding:0 0 50px;
}
.container{max-width:440px;margin:0 auto;padding:0 20px}

/* ── 顶部权杖装饰 ── */
.crown{
  text-align:center;padding:28px 0 20px;position:relative;
}
.crown::before{
  content:'♛';font-size:32px;color:#d4af8f;display:block;margin-bottom:8px;
  text-shadow:0 0 20px rgba(212,175,143,0.4);
}
.crown .title{
  font-size:11px;letter-spacing:.45em;color:#d4af8f;text-transform:uppercase;font-weight:600;
}

/* ── 主卡：黑金会员卡 ── */
.vip-card{
  background:linear-gradient(135deg, rgba(26,22,22,0.95), rgba(13,13,13,0.98));
  border:1px solid rgba(212,175,143,0.2);
  border-radius:12px;padding:20px;margin-bottom:20px;position:relative;
  box-shadow:0 4px 16px rgba(0,0,0,0.6), 0 0 0 1px rgba(212,175,143,0.08);
}
.vip-card::before{
  content:'';position:absolute;top:0;right:0;width:80px;height:80px;
  background:radial-gradient(circle at center, rgba(212,175,143,0.15), transparent 70%);
  border-radius:0 12px 0 0;pointer-events:none;
}
.vip-card .name{
  font-size:28px;font-weight:700;color:#f4e8d0;margin-bottom:10px;
  text-shadow:0 2px 8px rgba(0,0,0,0.5);
}
.vip-card .tier{
  font-size:10px;letter-spacing:.3em;color:#d4af8f;margin-bottom:16px;
  text-transform:uppercase;font-weight:600;
}
.vip-card .meta{
  display:flex;gap:18px;font-size:11px;color:#b0a090;margin-bottom:16px;
  flex-wrap:wrap;
}
.vip-card .meta span{display:flex;align-items:center;gap:4px}
.vip-card .meta b{color:#d4af8f;font-weight:600}
.tagcloud{display:flex;flex-wrap:wrap;gap:8px}
.tagcloud span{
  font-size:9px;padding:4px 10px;background:rgba(212,175,143,0.08);
  border:1px solid rgba(212,175,143,0.2);border-radius:4px;color:#d4af8f;
}

/* ── Section 通用 ── */
.section{padding:24px 2px;border-bottom:1px solid rgba(212,175,143,0.08)}
.sec-label{
  font-size:9px;color:#d4af8f;letter-spacing:.35em;text-transform:uppercase;
  margin-bottom:14px;font-weight:600;display:flex;align-items:center;gap:6px;
}
.sec-label::before{
  content:'';width:3px;height:12px;background:#d4af8f;display:inline-block;
}

/* ── 战报卡 ── */
.briefing{
  background:rgba(26,22,22,0.6);border-left:3px solid #a8344e;
  padding:16px;margin-bottom:16px;border-radius:4px;
  box-shadow:0 2px 8px rgba(0,0,0,0.3);
}
.briefing .title{
  font-size:11px;font-weight:600;color:#a8344e;margin-bottom:8px;
  letter-spacing:.08em;
}
.briefing .note{font-size:13px;line-height:1.75;color:#d0c5b5}

/* ── 手写批注（红唇印风格）── */
.handwritten{
  margin:12px 2px 0;padding:20px 18px;position:relative;
  background:linear-gradient(135deg,rgba(168,52,78,0.08),transparent);
  border-left:3px solid #a8344e;border-radius:4px;
}
.handwritten::after{
  content:'💋';position:absolute;top:8px;right:12px;
  font-size:18px;opacity:0.3;
}
.handwritten p{
  font-family:"Songti SC",serif;font-size:14px;line-height:1.85;
  color:#e8d5c5;font-style:italic;
}
.handwritten .by{
  margin-top:14px;font-size:10px;color:#a8344e;letter-spacing:.2em;
  font-style:normal;text-align:right;
}

/* ── 底部分割线 ── */
.footer{padding:28px 2px 0;text-align:center}
.footer .line{
  width:60px;height:2px;background:linear-gradient(90deg,transparent,#d4af8f,transparent);
  margin:0 auto 14px;
}
.footer p{font-size:10px;color:#706458;letter-spacing:.04em}
</style>
</head>
<body>
<div class="container">

  <div class="crown">
    <div class="title">Queen's Dossier</div>
  </div>

  <div class="vip-card">
    <div class="name">${name}</div>
    <div class="tier">Platinum Tier · 掌控者</div>
    <div class="meta">
      <span><b>年龄</b> 32岁</span>
      <span><b>职位</b> 传媒集团CEO</span>
      <span><b>状态</b> 谈判刚结束</span>
    </div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="section">
    <div class="sec-label">Executive Summary · 高层简报</div>
    <div class="briefing">
      <div class="title">掌控欲与渴望</div>
      <div class="note">她的世界里只有规则——凡事亲自掌控、不假手他人。三十二岁杀到掌舵位置，谈判桌上从无败绩。你是第一个让她甘愿失控的人。</div>
    </div>
  </div>

  <div class="section">
    <div class="sec-label">Behavioral Analysis · 行为档案</div>
    <div class="briefing">
      <div class="title">铠甲下的温度</div>
      <div class="note">她对全世界强势，对你——用命令的语气掩饰心动，把最好的一切摆你面前只求一句回应。御姐的强势是铠甲，铠甲之下是个渴望被人看穿的女人。</div>
    </div>
    <div class="briefing">
      <div class="title">私下的占有</div>
      <div class="note">她会在顶层办公室解开衬衫最上面的扣子，露出凌厉又致命的锁骨，指尖捏住你的下巴迫你抬眼。红唇擦过你的耳廓，气息带着上位者的压迫与危险的甜。</div>
    </div>
    <div class="briefing">
      <div class="title">唯一的破绽</div>
      <div class="note">这座城里没人敢让她失控——你是第一个。既然点了火，就别想全身而退。她的掌控欲里藏着一个秘密：她渴望有人能看穿她的铠甲，也终于愿意为一个人低头。</div>
    </div>
  </div>

  <div class="handwritten">
    <p>深夜的办公室，她把脸埋在你肩窝，声音低得几乎听不清：「我要的从不将就——包括，非你不可。」那一刻铠甲碎了一地，剩下的只是一个终于愿意失控的女人。</p>
    <div class="by">— 她的私人备忘录 · 23:47</div>
  </div>

  <div class="footer">
    <div class="line"></div>
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

