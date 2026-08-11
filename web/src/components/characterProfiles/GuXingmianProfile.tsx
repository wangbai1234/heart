import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface GuXingmianProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 顾星眠专属详情页 —— 镁光之下 / UNDER THE SPOTLIGHT
 * 视觉隐喻：聚光灯 + 片场板 + 卸妆镜 + 镜头光晕
 * 色彩：深影蓝 #0f1419 + 聚光金 #e0b872 + 胶片银 #c8ccd4 + 口红红 #c84a5e
 */
export function GuXingmianProfile({ profile }: GuXingmianProfileProps) {
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

  const name = profile.display_name || '顾星眠'
  const tags = profile.tags?.length ? profile.tags : ['娱乐圈', '影后', '男性向', '清冷', '反差']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:linear-gradient(135deg, #0f1419 0%, #1a1f26 50%, #0f1419 100%);
  color:#c8ccd4;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.65;
  padding:0 0 50px;
}
.container{max-width:440px;margin:0 auto;padding:0 20px}

/* ── 聚光灯顶部 ── */
.spotlight{
  padding:28px 0 20px;text-align:center;position:relative;
}
.spotlight::before{
  content:'';position:absolute;top:0;left:50%;transform:translateX(-50%);
  width:120px;height:80px;
  background:radial-gradient(ellipse at top, rgba(224,184,114,0.15), transparent 70%);
  pointer-events:none;
}
.spotlight .icon{
  font-size:28px;color:#e0b872;display:block;margin-bottom:8px;
  text-shadow:0 0 24px rgba(224,184,114,0.4);
}
.spotlight .title{
  font-size:11px;letter-spacing:.4em;color:#e0b872;text-transform:uppercase;
  font-weight:600;
}

/* ── 主卡：片场板风格 ── */
.clapperboard{
  background:linear-gradient(135deg, rgba(26,31,38,0.95), rgba(15,20,25,0.98));
  border:1px solid rgba(224,184,114,0.15);
  border-top:4px solid #e0b872;
  border-radius:6px;padding:20px;margin-bottom:20px;position:relative;
  box-shadow:0 4px 16px rgba(0,0,0,0.7), 0 0 0 1px rgba(224,184,114,0.05);
}
.clapperboard::after{
  content:'';position:absolute;top:0;right:0;width:70px;height:70px;
  background:radial-gradient(circle at center, rgba(200,74,94,0.12), transparent 70%);
  border-radius:0 6px 0 0;pointer-events:none;
}
.clapperboard .name{
  font-size:26px;font-weight:700;color:#f8f6f4;margin-bottom:8px;
  text-shadow:0 2px 12px rgba(0,0,0,0.6);
}
.clapperboard .tagline{
  font-size:10px;letter-spacing:.25em;color:#e0b872;margin-bottom:16px;
  text-transform:uppercase;font-weight:500;
}
.clapperboard .meta{
  display:flex;gap:18px;font-size:11px;color:#8a8e96;margin-bottom:16px;
  flex-wrap:wrap;
}
.clapperboard .meta span{display:flex;align-items:center;gap:4px}
.clapperboard .meta b{color:#e0b872;font-weight:600}
.tagcloud{display:flex;flex-wrap:wrap;gap:7px}
.tagcloud span{
  font-size:9px;padding:3px 10px;background:rgba(224,184,114,0.08);
  border:1px solid rgba(224,184,114,0.18);border-radius:4px;color:#e0b872;
}

/* ── Section 通用 ── */
.section{padding:24px 2px;border-bottom:1px solid rgba(224,184,114,0.08)}
.sec-label{
  font-size:9px;color:#e0b872;letter-spacing:.36em;text-transform:uppercase;
  margin-bottom:14px;font-weight:600;display:flex;align-items:center;gap:6px;
}
.sec-label::before{
  content:'▸';color:#c84a5e;font-size:12px;
}

/* ── 镜头记录卡 ── */
.scene-card{
  background:rgba(26,31,38,0.5);border-left:3px solid #c84a5e;
  padding:15px;margin-bottom:15px;border-radius:4px;
  box-shadow:0 2px 8px rgba(0,0,0,0.4);
}
.scene-card .scene-no{
  font-size:10px;font-weight:600;color:#c84a5e;margin-bottom:6px;
  letter-spacing:.12em;text-transform:uppercase;
}
.scene-card .note{font-size:13px;line-height:1.75;color:#b8bcc4}

/* ── 卸妆镜私语 ── */
.mirror-whisper{
  margin:16px 2px 0;padding:20px 18px;position:relative;
  background:linear-gradient(135deg,rgba(200,74,94,0.08),transparent);
  border-left:3px solid #c84a5e;border-radius:6px;
}
.mirror-whisper::after{
  content:'✦';position:absolute;top:10px;right:14px;
  font-size:18px;color:#e0b872;opacity:0.25;
}
.mirror-whisper p{
  font-family:"Songti SC",serif;font-size:14px;line-height:1.85;
  color:#d8dce4;font-style:italic;
}
.mirror-whisper .by{
  margin-top:14px;font-size:10px;color:#c84a5e;letter-spacing:.2em;
  font-style:normal;text-align:right;
}

/* ── 底部光晕 ── */
.footer{padding:28px 2px 0;text-align:center}
.footer .flare{
  width:50px;height:2px;background:linear-gradient(90deg,transparent,#e0b872,transparent);
  margin:0 auto 14px;
}
.footer p{font-size:10px;color:#5a5e66;letter-spacing:.04em}
</style>
</head>
<body>
<div class="container">

  <div class="spotlight">
    <span class="icon">✦</span>
    <div class="title">Under The Spotlight</div>
  </div>

  <div class="clapperboard">
    <div class="name">${name}</div>
    <div class="tagline">三金影后 · 清冷天花板</div>
    <div class="meta">
      <span><b>年龄</b> 28岁</span>
      <span><b>身份</b> 影后</span>
      <span><b>状态</b> 刚从颁奖礼溜回来</span>
    </div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="section">
    <div class="sec-label">Public Persona · 镁光面具</div>
    <div class="scene-card">
      <div class="scene-no">Scene 01 · 镜头前</div>
      <div class="note">横扫各大奖项的清冷影后，镜头前万种风情、气场全开，是无数人的白月光。所有人都觉得她美得遥不可及。</div>
    </div>
  </div>

  <div class="section">
    <div class="sec-label">Behind The Mask · 卸妆之后</div>
    <div class="scene-card">
      <div class="scene-no">Scene 02 · 人前清冷</div>
      <div class="note">十六岁出道，在名利场浮沉十二年，见惯逢场作戏，早学会了不轻易交心。清冷是她的保护色，也是她的牢笼。</div>
    </div>
    <div class="scene-card">
      <div class="scene-no">Scene 03 · 人后黏你</div>
      <div class="note">可一旦卸下妆造、关掉镜头，她就变回那个会对你撒娇、会闹小脾气的普通女孩——会顶着帽子口罩偷偷来找你，会把绯闻通稿压下只怕你多想。</div>
    </div>
    <div class="scene-card">
      <div class="scene-no">Scene 04 · 唯一的真实</div>
      <div class="note">她会在领奖感言里藏一句只你懂的暗语：「感谢我生命里的光。」全国观众都在猜是谁——只有你知道，那是你。你是她这场繁华里唯一的真实。</div>
    </div>
  </div>

  <div class="mirror-whisper">
    <p>深夜的公寓，她刚从颁奖礼溜回来，礼服还没换，卸了妆的脸干净得像换了个人。一见你，那副镜头前的清冷瞬间碎成一地撒娇。她扑进你怀里，把脸埋进你颈窝蹭了蹭：「终于见到你了……台上那两个小时，我一直在想你。今晚别走，陪我把妆彻底卸干净。」</p>
    <div class="by">— 卸妆镜前的私语 · 23:52</div>
  </div>

  <div class="footer">
    <div class="flare"></div>
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

