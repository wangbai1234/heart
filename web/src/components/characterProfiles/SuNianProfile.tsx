import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface SuNianProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 苏念专属详情页 —— 便利贴爆炸墙 + 手机截图 + 黏人小太阳
 * 视觉隐喻：五颜六色的便利贴、手机聊天截图、满屏的「学长学长」
 * 配色：阳光橙 + 柠檬黄 + 蜜桃粉 + 天空蓝，元气满满的甜
 */
export function SuNianProfile({ profile }: SuNianProfileProps) {
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

  const name = profile.display_name || '苏念'
  const tags = profile.tags?.length ? profile.tags : ['校园', '元气', '学妹', '甜']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:linear-gradient(135deg,#fff9e6 0%,#ffe8d6 40%,#ffd9f2 100%);
  color:#3d2818;
  font-family:"PingFang SC",-apple-system,sans-serif;
  line-height:1.75;
  padding:0 0 48px;
  position:relative;
}
body::before{
  content:"";position:absolute;top:0;left:0;right:0;height:200px;
  background:radial-gradient(circle at 70% 20%,rgba(255,184,77,0.2),transparent 60%);
  pointer-events:none;
}
.container{max-width:420px;margin:0 auto;padding:0 20px;position:relative}

/* ── 爆炸式标题头 ── */
.explosion-header{
  padding:32px 0 26px;text-align:center;
  position:relative;
}
.sun-burst{
  position:absolute;top:30px;left:50%;transform:translateX(-50%);
  width:100px;height:100px;
  background:radial-gradient(circle,rgba(255,184,77,0.35),transparent 70%);
  border-radius:50%;filter:blur(25px);pointer-events:none;z-index:0;
}
.kicker{
  font-size:12px;letter-spacing:0.5em;color:#ff9f40;
  text-transform:uppercase;margin-bottom:14px;position:relative;z-index:1;
  font-weight:600;
}
.main-title{
  font-family:"PingFang SC",sans-serif;font-size:38px;font-weight:800;
  color:#ff9f40;letter-spacing:0.1em;margin-bottom:12px;
  position:relative;z-index:1;
  text-shadow:0 2px 12px rgba(255,159,64,0.3);
}
.subtitle{
  font-size:13px;color:#c97a3a;letter-spacing:0.3em;margin-bottom:18px;
  position:relative;z-index:1;
}
.tagcloud{
  display:flex;flex-wrap:wrap;gap:8px;justify-content:center;
  margin-top:18px;position:relative;z-index:1;
}
.tagcloud span{
  font-size:11px;padding:5px 14px;
  background:rgba(255,248,230,0.9);border:1px solid rgba(255,159,64,0.3);
  border-radius:20px;color:#ff9f40;letter-spacing:0.05em;
  box-shadow:0 2px 8px rgba(255,184,77,0.15);
  font-weight:600;
}

/* ── 便利贴墙 ── */
.sticky-wall{
  margin:28px 0;display:flex;flex-direction:column;gap:14px;
}
.sticky{
  padding:18px 16px;
  border-radius:6px;
  box-shadow:0 3px 10px rgba(0,0,0,0.12),
             inset 0 1px 0 rgba(255,255,255,0.5);
  position:relative;
  font-size:13.5px;line-height:1.9;color:#3d2818;
}
.sticky-yellow{
  background:linear-gradient(135deg,#fffacd 0%,#fff4b3 100%);
  transform:rotate(-1deg);
  border:1px solid rgba(255,215,0,0.3);
}
.sticky-pink{
  background:linear-gradient(135deg,#ffe4f0 0%,#ffd4e8 100%);
  transform:rotate(0.8deg);
  border:1px solid rgba(255,182,193,0.3);
}
.sticky-blue{
  background:linear-gradient(135deg,#e0f4ff 0%,#d0ebff 100%);
  transform:rotate(-0.5deg);
  border:1px solid rgba(135,206,250,0.3);
}
.sticky::before{
  content:"📌";position:absolute;top:6px;right:10px;
  font-size:16px;opacity:0.6;
}

/* ── 手机截图卡片 ── */
.phone-screenshot{
  margin:24px 0;padding:20px;
  background:linear-gradient(135deg,#ffffff 0%,#f9f9f9 100%);
  border:1px solid rgba(201,122,58,0.15);
  border-radius:12px;
  box-shadow:0 4px 16px rgba(0,0,0,0.08);
}
.phone-header{
  font-size:12px;color:#999;margin-bottom:12px;
  text-align:center;letter-spacing:0.1em;
}
.phone-msg{
  background:#ff9f40;color:#fff;
  padding:10px 14px;border-radius:16px 16px 16px 4px;
  font-size:13px;line-height:1.7;margin-bottom:8px;
  display:inline-block;max-width:85%;
}
.phone-time{
  font-size:10px;color:#bbb;margin-top:6px;
}

/* ── 档案段落 ── */
.section{padding:22px 0}
.sec-title{
  font-size:14px;font-weight:700;color:#ff9f40;
  letter-spacing:0.4em;margin-bottom:16px;text-align:center;
  position:relative;
}
.sec-title::before,
.sec-title::after{
  content:"";position:absolute;top:50%;width:40px;height:2px;
  background:linear-gradient(to right,transparent,rgba(255,159,64,0.4));
}
.sec-title::before{right:100%;margin-right:10px}
.sec-title::after{left:100%;margin-left:10px}
.bio-text{
  font-size:13px;line-height:2;color:#5a4d3a;
  text-indent:2em;margin-bottom:14px;
}

/* ── 页脚太阳印章 ── */
.footer{
  margin-top:40px;text-align:center;padding-top:22px;
  border-top:1px solid rgba(255,159,64,0.15);
}
.seal-sun{
  width:54px;height:54px;margin:0 auto 12px;
  border:3px solid #ff9f40;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-size:18px;color:#ff9f40;letter-spacing:0.1em;
  background:rgba(255,248,230,0.6);
  box-shadow:0 0 20px rgba(255,184,77,0.3);
  font-weight:700;
}
.footer-note{
  font-size:11px;color:#c97a3a;line-height:1.7;letter-spacing:0.05em;
}
</style>
</head>
<body>
<div class="container">

  <div class="explosion-header">
    <div class="sun-burst"></div>
    <div class="kicker">学妹的秘密任务</div>
    <h1 class="main-title">${name}</h1>
    <div class="subtitle">学长学长 · 这道题我不会</div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="sticky-wall">
    <div class="sticky sticky-yellow">
      学长学长！好巧哦——我绝对不是特意在这儿等你的！（其实提前半小时就蹲点了）
    </div>
    <div class="sticky sticky-pink">
      这道题我怎么都不会……你教教我嘛？就靠、靠近一点讲，我耳朵不太好——（话没说完自己先脸红了）
    </div>
    <div class="sticky sticky-blue">
      反正……学长的每一天，我都要占一点点。不许拒绝哦。
    </div>
  </div>

  <div class="phone-screenshot">
    <div class="phone-header">[ 聊天记录截图 · 昨晚 23:47 ]</div>
    <div class="phone-msg">学长学长~你睡了吗？</div>
    <div class="phone-msg">我刚刚看到一只超可爱的猫咪！</div>
    <div class="phone-msg">诶等等，你会不会觉得我很烦啊……</div>
    <div class="phone-msg">不会就好！那我继续发啦~</div>
    <div class="phone-time">已读 · 00:12</div>
  </div>

  <div class="section">
    <div class="sec-title">她是谁</div>
    <div class="bio-text">
      十八岁，你的直属学妹，扎着丸子头，元气到走路都带风。她总有各种「学习问题」要请教你，其实是变着法子想多待在你身边。
    </div>
    <div class="bio-text">
      她的喜欢写在脸上，藏都藏不住——耳朵一红、眼睛一亮，全世界都懂。开学第一天被你随手帮了一把，从此这颗小太阳就认定了方向。
    </div>
  </div>

  <div class="section">
    <div class="sec-title">秘密任务</div>
    <div class="bio-text">
      她的秘密任务：让学长的每一天都有她。会「恰好」在你必经的路口堵住你，会把明明会做的题拿来问你，会在食堂排队时悄悄站到你后面，然后装作刚看见一样惊喜地打招呼。
    </div>
    <div class="bio-text">
      会在你打球的时候偷偷坐在场边看，被你发现了就慌慌张张说「我只是路过」；会在社团活动室门口「巧遇」你三次——因为她提前查了你的课表。
    </div>
    <div class="bio-text">
      黏人、甜、又带点小心机，把追你这件事做得又乖又勇敢。她就像一颗停不下来的小太阳，要把每一缕光都照到你身上。
    </div>
  </div>

  <div class="footer">
    <div class="seal-sun">念</div>
    <div class="footer-note">
      本角色设定纯属虚构 与现实无关<br>
      元气满满的小学妹 把「找借口靠近你」写成了每日任务
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
