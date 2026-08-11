import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface ShenLiaoProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 沈燎专属详情页 —— 机车厂钢板日志 / GARAGE LOG
 * 视觉语言：橙色火焰 + 工业金属质感 + 扳手与齿轮装饰 + 手写涂鸦
 * 年下狼狗美学：橙金 + 深灰 + 机油黑，工业朋克 + 青春热烈
 */
export function ShenLiaoProfile({ profile }: ShenLiaoProfileProps) {
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

  const name = profile.display_name || '沈燎'
  const tags = profile.tags?.length ? profile.tags : ['女性向', '都市', '年下', '狼狗', '直球']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#1a1c1f;
  color:#e8e4df;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.65;
  padding:0 0 40px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}
.mono{font-family:"Courier New",monospace}

/* ── 机车厂金属铭牌 ── */
.header{
  margin:20px 0;
  padding:24px 20px;
  background:linear-gradient(135deg,#2a2d32,#1e2024);
  border-left:4px solid #ff8833;
  border-radius:2px;
  box-shadow:0 4px 16px rgba(0,0,0,0.4),inset 0 1px 0 rgba(255,136,51,0.15);
  position:relative;
}
.header::after{
  content:"";position:absolute;top:8px;right:12px;
  width:32px;height:32px;
  background:url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%23ff8833" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M8 12h8M12 8v8"/></svg>');
  opacity:0.2;
}
.garage-id{
  font-family:"Courier New",monospace;font-size:10px;
  color:#ff8833;letter-spacing:.3em;text-transform:uppercase;
}
.name{
  font-size:38px;font-weight:800;
  background:linear-gradient(135deg,#ffaa55,#ff8833);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;
  margin:8px 0;letter-spacing:.08em;
}
.role{font-size:12px;color:#a8a29d;letter-spacing:.1em;margin-bottom:12px}
.tags{display:flex;flex-wrap:wrap;gap:7px}
.tags span{
  font-size:10px;padding:4px 9px;
  background:rgba(255,136,51,0.1);border:1px solid rgba(255,136,51,0.3);
  border-radius:3px;color:#ffaa77;
}

/* ── 工具箱档案 ── */
.toolbox{
  margin:24px 0;padding:20px;
  background:rgba(42,45,50,0.6);
  border:1px solid rgba(255,136,51,0.15);
  border-radius:8px;
}
.sec-title{
  font-family:"Courier New",monospace;font-size:11px;
  color:#ff8833;letter-spacing:.28em;text-transform:uppercase;
  margin-bottom:14px;padding-bottom:6px;
  border-bottom:1px dashed rgba(255,136,51,0.25);
}
.bio{font-size:13px;line-height:1.8;color:#c8c2bb;margin-bottom:18px}
.spec-row{
  display:flex;padding:10px 0;
  border-bottom:1px solid rgba(255,255,255,0.04);
}
.spec-row .label{
  font-size:11px;color:#8a8480;min-width:75px;letter-spacing:.06em;
}
.spec-row .val{flex:1;font-size:12.5px;color:#e0d8cf;line-height:1.5}

/* ── 改装清单 ── */
.mods{margin:24px 0}
.mod-card{
  margin-bottom:12px;padding:16px;
  background:linear-gradient(120deg,rgba(255,136,51,0.08),rgba(42,45,50,0.5));
  border-left:3px solid #ff8833;border-radius:4px;
}
.mod-card .title{
  font-size:14px;font-weight:600;color:#ffaa66;margin-bottom:6px;
}
.mod-card .desc{font-size:12px;line-height:1.65;color:#b8b2aa}

/* ── 手写便签：想说的话 ── */
.note-sticky{
  margin:28px 8px 0;padding:20px;
  background:linear-gradient(155deg,#fff8e5,#ffefd6);
  border-radius:2px;
  box-shadow:3px 3px 10px rgba(0,0,0,0.3);
  transform:rotate(-0.8deg);
  position:relative;
}
.note-sticky::before{
  content:"";position:absolute;
  top:-6px;right:20%;width:50px;height:16px;
  background:rgba(255,200,100,0.3);
  box-shadow:inset 0 1px 2px rgba(0,0,0,0.1);
}
.note-sticky p{
  font-family:"Kaiti SC","STKaiti",serif;
  font-size:15px;line-height:1.85;color:#4a3f2f;
}
.note-sticky .sign{
  margin-top:10px;font-size:11px;text-align:right;
  color:#8a7a6a;letter-spacing:.08em;
}

/* ── 页脚 ── */
.foot{padding:28px 0 0;text-align:center}
.foot .divider{
  width:50px;height:2px;background:#ff8833;
  opacity:0.35;margin:0 auto 10px;
}
.foot p{font-size:10px;color:#6a6662;letter-spacing:.06em}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="garage-id">GARAGE LOG · NO.沈燎</div>
    <div class="name">${name}</div>
    <div class="role">地下机车改装手 · 年下狼狗</div>
    <div class="tags">${tagCloud}</div>
  </div>

  <div class="toolbox">
    <div class="sec-title">档案 · Profile</div>
    <p class="bio">二十二岁 · 浅金短发 · 纹身 · 扳手和发动机轰鸣是他的母语</p>
    <div class="spec-row">
      <span class="label">专长</span>
      <span class="val">机车改装、发动机调校、地下赛道王牌</span>
    </div>
    <div class="spec-row">
      <span class="label">标志</span>
      <span class="val">手臂纹身、毛巾搭肩、机油味和灿烂坏笑</span>
    </div>
    <div class="spec-row">
      <span class="label">核心矛盾</span>
      <span class="val">明明最讨厌被当成「还小」，却又在你面前暴露所有热烈和幼稚</span>
    </div>
  </div>

  <div class="mods">
    <div class="sec-title">改装清单 · What I Fix</div>
    <div class="mod-card">
      <div class="title">车 · 调到最稳</div>
      <div class="desc">你的车我调过三遍，每次都想证明：我也能给你一个不飘的未来。</div>
    </div>
    <div class="mod-card">
      <div class="title">占有欲 · 不加掩饰</div>
      <div class="desc">姐，别摸别人头。我会吃醋，也会想证明我不是小孩。</div>
    </div>
    <div class="mod-card">
      <div class="title">孤独 · 烧成热烈</div>
      <div class="desc">没人真正选择过我，所以我要的不是哄，是你明确地选我。</div>
    </div>
  </div>

  <div class="note-sticky">
    <p>我知道你觉得我还小。可车我能停稳，钥匙我能交给你，心我也想给你一个正经的未来。</p>
    <p>你每说一次「我不是小孩」，我就更想证明——我认准的东西，从不放手。</p>
    <div class="sign">— 写在修车厂卷帘门背后</div>
  </div>

  <div class="foot">
    <div class="divider"></div>
    <p>GARAGE LOG · 机车厂日志 · 角色设定纯属虚构</p>
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

