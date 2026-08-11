import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface SuYueyaoProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 苏月遥专属详情页 —— 夏日花灯长廊 + 折叠纸条 + 初恋日记
 * 视觉隐喻：校园长廊的暖光、藏在书页里的纸条、怦然心动的少女日记
 * 配色：暖杏 + 樱粉 + 暮橙 + 浅紫，手写感温柔呼吸
 */
export function SuYueyaoProfile({ profile }: SuYueyaoProfileProps) {
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

  const name = profile.display_name || '苏月遥'
  const tags = profile.tags?.length ? profile.tags : ['纯爱', '校园', '初恋', '青梅竹马']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:linear-gradient(165deg,#fff8f0 0%,#ffe8e0 50%,#f9f1f8 100%);
  color:#3d2b28;
  font-family:"PingFang SC",-apple-system,sans-serif;
  line-height:1.75;
  padding:0 0 48px;
  position:relative;
}
body::before{
  content:"";position:absolute;top:0;left:0;right:0;height:240px;
  background:radial-gradient(ellipse at 50% 0,rgba(255,180,165,0.18),transparent 70%);
  pointer-events:none;
}
.container{max-width:420px;margin:0 auto;padding:0 20px;position:relative}

/* ── 花灯头部 ── */
.lantern-header{
  padding:32px 0 24px;text-align:center;
  position:relative;
}
.lantern-glow{
  position:absolute;top:20px;left:50%;transform:translateX(-50%);
  width:120px;height:120px;
  background:radial-gradient(circle,rgba(255,180,165,0.4),transparent 65%);
  border-radius:50%;filter:blur(20px);pointer-events:none;z-index:0;
}
.kicker{
  font-size:11px;letter-spacing:0.6em;color:#c89080;
  text-transform:uppercase;margin-bottom:12px;position:relative;z-index:1;
}
.main-title{
  font-family:"PingFang SC",sans-serif;font-size:36px;font-weight:700;
  color:#e87a66;letter-spacing:0.12em;margin-bottom:10px;
  position:relative;z-index:1;
  text-shadow:0 2px 8px rgba(232,122,102,0.2);
}
.subtitle{
  font-size:13px;color:#9a7068;letter-spacing:0.35em;margin-bottom:18px;
  position:relative;z-index:1;
}
.tagcloud{
  display:flex;flex-wrap:wrap;gap:8px;justify-content:center;
  margin-top:18px;position:relative;z-index:1;
}
.tagcloud span{
  font-size:11px;padding:5px 14px;
  background:rgba(255,245,240,0.85);border:1px solid rgba(232,122,102,0.25);
  border-radius:18px;color:#c87868;letter-spacing:0.05em;
  box-shadow:0 2px 6px rgba(232,122,102,0.08);
}

/* ── 折叠纸条 ── */
.note-fold{
  margin:28px 0;padding:24px 20px;
  background:linear-gradient(135deg,#fffaf5 0%,#fff0e8 100%);
  border:1px solid rgba(232,122,102,0.15);
  border-radius:8px;
  box-shadow:0 3px 12px rgba(232,122,102,0.12),
             inset 0 1px 0 rgba(255,255,255,0.6);
  position:relative;
  transform:rotate(-0.5deg);
}
.note-fold::before{
  content:"";position:absolute;top:8px;right:12px;
  width:40px;height:6px;
  background:repeating-linear-gradient(
    90deg,transparent,transparent 3px,rgba(232,122,102,0.25) 3px,rgba(232,122,102,0.25) 4px
  );
  opacity:0.6;
}
.note-title{
  font-size:15px;font-weight:600;color:#e87a66;
  margin-bottom:12px;letter-spacing:0.15em;
}
.note-body{
  font-size:13.5px;line-height:2;color:#4a3d3a;
  text-indent:2em;
}

/* ── 心跳小诗 ── */
.heartbeat-poem{
  margin:26px 0;padding:18px 22px;
  background:linear-gradient(120deg,rgba(255,240,235,0.7),rgba(249,241,248,0.6));
  border-left:3px solid #e87a66;border-radius:6px;
  position:relative;
}
.heartbeat-poem::after{
  content:"♡";position:absolute;bottom:10px;right:14px;
  font-size:18px;color:rgba(232,122,102,0.2);
}
.poem-line{
  font-size:14px;line-height:2.3;color:#4a3d3a;
  text-align:center;letter-spacing:0.08em;
}
.poem-by{
  margin-top:10px;text-align:right;font-size:11px;
  color:#b58a7a;letter-spacing:0.25em;
}

/* ── 心事档案 ── */
.section{padding:22px 0}
.sec-title{
  font-size:14px;font-weight:600;color:#e87a66;
  letter-spacing:0.5em;margin-bottom:16px;text-align:center;
  position:relative;
}
.sec-title::before,
.sec-title::after{
  content:"";position:absolute;top:50%;width:45px;height:1px;
  background:linear-gradient(to right,transparent,rgba(232,122,102,0.3));
}
.sec-title::before{right:100%;margin-right:10px}
.sec-title::after{left:100%;margin-left:10px}
.bio-text{
  font-size:13px;line-height:2;color:#5a4d48;
  text-indent:2em;margin-bottom:14px;
}

/* ── 页脚花灯印章 ── */
.footer{
  margin-top:40px;text-align:center;padding-top:22px;
  border-top:1px solid rgba(232,122,102,0.12);
}
.seal-lantern{
  width:52px;height:52px;margin:0 auto 12px;
  border:2px solid #e87a66;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-size:17px;color:#e87a66;letter-spacing:0.1em;
  background:rgba(255,245,240,0.5);
  box-shadow:0 0 16px rgba(232,122,102,0.2);
}
.footer-note{
  font-size:11px;color:#b58a7a;line-height:1.7;letter-spacing:0.05em;
}
</style>
</head>
<body>
<div class="container">

  <div class="lantern-header">
    <div class="lantern-glow"></div>
    <div class="kicker">校园长廊 · 初恋日记</div>
    <h1 class="main-title">${name}</h1>
    <div class="subtitle">你回头的那一刻 · 我把喜欢偷偷说了一百遍</div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="note-fold">
    <div class="note-title">藏在书页里的纸条</div>
    <div class="note-body">
      那、那个……我等你很久了。这是我从高中就想给你的。
      里面写了什么，你回去再看，现在别、别当着我面看啦！
      我喜欢你……很久很久了。这次上了同一所大学，我不想再只是偷偷看着你了。
    </div>
  </div>

  <div class="heartbeat-poem">
    <div class="poem-line">见到你的时候</div>
    <div class="poem-line">整个夏天的花灯都亮了</div>
    <div class="poem-by">—— 日记本第三百七十八页</div>
  </div>

  <div class="section">
    <div class="sec-title">她的样子</div>
    <div class="bio-text">
      十九岁，你的大学同班，黑发披肩，宽檐白帽和浅色裙装衬得她安静、干净，笑起来有浅浅的酒窝。
    </div>
    <div class="bio-text">
      从高中起就偷偷喜欢你，把心事写进日记本又划掉。这一次上了同一所大学，她想鼓起勇气，走近一点点。
    </div>
  </div>

  <div class="section">
    <div class="sec-title">藏起来的喜欢</div>
    <div class="bio-text">
      她的喜欢藏得小心翼翼——会记得你随口提过的每件小事，会在你篮球赛时躲在人群里为你紧张，会因为你一句夸奖开心一整天。
    </div>
    <div class="bio-text">
      她会在你路过的地方「恰好」堵住去路，抱着资料假装巧遇；会把一道明明会做的题拿来请教，只为了多听你说两句话；会在社交软件上给你发消息，编辑了删删了编辑，最后只发出一个「在吗」。
    </div>
    <div class="bio-text">
      这是最纯粹的初恋模样:没有套路,只有一颗砰砰跳的、想靠近又怕唐突的心。她的每一次鼓起勇气,都在用尽全身的力气。
    </div>
  </div>

  <div class="footer">
    <div class="seal-lantern">月遥</div>
    <div class="footer-note">
      本角色设定纯属虚构 与现实无关<br>
      干净又心动的初恋模样 藏在这盏为你点亮的花灯里
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

