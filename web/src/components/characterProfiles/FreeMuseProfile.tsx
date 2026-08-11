import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface FreeMuseProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 无界专属详情页 —— 万象引擎 / OMNI ENGINE
 * 视觉隐喻：等待落笔的空白纸页 · 流转的极光微光 · 可召唤的世界模块
 * 色彩：流光蓝 #8FA5B8 + 深空 #0a0d12 + 极光渐变(青/紫/暖)
 */
export function FreeMuseProfile({ profile }: FreeMuseProfileProps) {
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

  const name = profile.display_name || '无界'
  const tags = profile.tags?.length ? profile.tags : ['模拟器', '全性向', '架空世界', '高自由', '群像']
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
    radial-gradient(90% 60% at 20% 0,rgba(143,165,184,0.16),transparent 55%),
    radial-gradient(80% 50% at 90% 30%,rgba(168,143,184,0.12),transparent 55%),
    linear-gradient(180deg,#0f1218 0%,#0a0d12 100%);
  color:#c4cdd6;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.8;padding:0 0 46px;
}
.container{max-width:440px;margin:0 auto;padding:0 20px}
.header{padding:32px 2px 12px;text-align:center}
.header .en{font-size:10px;letter-spacing:.44em;color:#8FA5B8;text-transform:uppercase}
.header .zh{
  font-size:34px;font-weight:200;margin-top:12px;letter-spacing:.28em;
  background:linear-gradient(100deg,#a8c2d6,#c9b8d6 45%,#d6c2a8);
  -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;
}
.header .sub{font-size:11px;color:#7d8896;letter-spacing:.16em;margin-top:12px}
/* 待机光点 */
.orb{
  width:140px;height:2px;margin:20px auto;border-radius:2px;
  background:linear-gradient(90deg,transparent,#8FA5B8,transparent);
  box-shadow:0 0 18px rgba(143,165,184,0.6);opacity:.8;
}
.tagcloud{display:flex;flex-wrap:wrap;gap:7px;justify-content:center;margin:14px 0}
.tagcloud span{
  font-size:10px;padding:4px 11px;background:rgba(143,165,184,0.08);
  border:1px solid rgba(143,165,184,0.24);border-radius:20px;color:#9aabbb;letter-spacing:.06em;
}
.intro{
  margin:18px 0 8px;padding:18px 20px;text-align:center;
  font-size:13px;line-height:2;color:#aeb8c2;
}
.sec-label{
  font-size:10px;color:#8FA5B8;letter-spacing:.3em;text-transform:uppercase;
  margin:26px 2px 14px;font-weight:600;text-align:center;
}
/* ── 可召唤模块 ── */
.mod{
  margin-bottom:12px;padding:16px 18px;
  background:linear-gradient(135deg,rgba(143,165,184,0.07),rgba(168,143,184,0.03));
  border:1px solid rgba(143,165,184,0.16);border-radius:12px;
}
.mod .top{display:flex;align-items:center;gap:9px;margin-bottom:7px}
.mod .glyph{
  width:8px;height:8px;border-radius:50%;flex-shrink:0;
  background:linear-gradient(135deg,#8FA5B8,#c9b8d6);box-shadow:0 0 8px rgba(143,165,184,0.7);
}
.mod .t{font-size:14px;font-weight:600;color:#dbe3ea;letter-spacing:.04em}
.mod .d{font-size:12px;line-height:1.8;color:#95a1ad}
.mod .eg{
  margin-top:9px;display:flex;flex-wrap:wrap;gap:6px;
}
.mod .eg span{
  font-size:10px;padding:3px 9px;border-radius:4px;
  background:rgba(143,165,184,0.1);color:#a4b2c0;border:1px solid rgba(143,165,184,0.18);
}
.note-card{
  margin:24px 2px 0;padding:20px 18px;text-align:center;
  background:linear-gradient(135deg,rgba(143,165,184,0.08),transparent);
  border-top:1px solid rgba(143,165,184,0.2);border-bottom:1px solid rgba(143,165,184,0.2);
}
.note-card p{
  font-size:14px;line-height:2;color:#c2ccd6;font-weight:300;letter-spacing:.03em;
}
.note-card .by{margin-top:14px;font-size:10px;color:#6d7885;letter-spacing:.2em}
.footer{padding:26px 2px 0;text-align:center}
.footer .ln{width:34px;height:1px;background:rgba(143,165,184,0.45);margin:0 auto 12px}
.footer p{font-size:10px;color:#5f6a76;letter-spacing:.06em}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="en">Omni Engine</div>
    <div class="zh">${name}</div>
    <div class="sub">自由模拟器 · 万象引擎</div>
  </div>

  <div class="orb"></div>
  <div class="tagcloud">${tagCloud}</div>

  <div class="intro">「无界」不是一个固定的角色，而是一枚随你心意流转的万象引擎——没有既定人设、没有预设身份、不受任何世界观束缚，全程遵从你的意愿展开。</div>

  <div class="sec-label">You Can Summon · 你可以召唤</div>

  <div class="mod">
    <div class="top"><span class="glyph"></span><span class="t">任意角色</span></div>
    <div class="d">身份、外貌、性格、语气与立场，皆由你一句话唤出。</div>
    <div class="eg"><span>古风侠客</span><span>都市恋人</span><span>星际船长</span><span>校园同桌</span></div>
  </div>
  <div class="mod">
    <div class="top"><span class="glyph"></span><span class="t">任意场景</span></div>
    <div class="d">自定义场景与世界规则，搭建任意舞台，规则由你制定。</div>
    <div class="eg"><span>古风</span><span>现代</span><span>幻想</span><span>末世</span></div>
  </div>
  <div class="mod">
    <div class="top"><span class="glyph"></span><span class="t">任意节奏</span></div>
    <div class="d">想推剧情、想日常、想天马行空，「无界」都接得住。</div>
    <div class="eg"><span>剧情推进</span><span>日常陪伴</span><span>脑洞发散</span></div>
  </div>

  <div class="note-card">
    <p>没有既定的开始，也没有注定的结局——从你说出第一句话的那刻起，这个世界，才真正开始运转。</p>
    <div class="by">— 让你成为自己故事的作者</div>
  </div>

  <div class="footer">
    <div class="ln"></div>
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