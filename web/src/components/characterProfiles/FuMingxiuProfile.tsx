import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface FuMingxiuProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 傅明修专属详情页 —— 冰箱上的「家规便签板 / HOUSE RULES」
 * 26 岁无血缘哥哥，把唯一的家守成不敢说出口的爱。
 * 视觉语言：暖木留言板 + 略歪的便签纸 + 玄关暖灯，楷体手写感，纯排版无 emoji
 */
export function FuMingxiuProfile({ profile }: FuMingxiuProfileProps) {
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

  const name = profile.display_name || '傅明修'
  const tags = profile.tags?.length ? profile.tags : ['都市', '年上', '伪骨科', '克制', '占有欲']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#1c1814;
  color:#d4c9ba;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Kaiti SC",sans-serif;
  line-height:1.75;
  padding:0 0 48px;
}
.container{max-width:440px;margin:0 auto;padding:0 20px}

/* ── 木纹留言板顶部 ── */
.board{
  padding:26px 12px 16px;
  background:linear-gradient(180deg,rgba(155,138,122,.12),rgba(155,138,122,.02));
  border-bottom:2px solid rgba(155,138,122,.16);
  position:relative;
}
.board-title{
  font-family:"Kaiti SC","STKaiti",serif;
  font-size:26px;letter-spacing:.14em;color:#9B8A7A;font-weight:600;
  text-align:center;margin-bottom:12px;
}
.board-sub{
  text-align:center;font-size:12px;letter-spacing:.32em;color:rgba(155,138,122,.6);
  text-transform:uppercase;margin-bottom:14px;
}
/* 磁贴装饰（纯CSS圆形 / 方形） */
.magnets{
  display:flex;gap:10px;justify-content:center;margin-top:10px;
}
.magnet{
  width:10px;height:10px;border-radius:50%;
  background:radial-gradient(circle at 30% 30%,rgba(155,138,122,.5),rgba(98,88,75,.6));
  box-shadow:0 1px 2px rgba(0,0,0,.3);
}
.magnet:nth-child(2){border-radius:2px;width:8px;height:8px}

/* ── 角色档案头 ── */
.intro{
  padding:28px 14px 20px;
  border-bottom:1px solid rgba(155,138,122,.08);
}
.intro h1{
  font-family:"Kaiti SC","STKaiti",serif;
  font-size:32px;letter-spacing:.12em;color:#d4c9ba;font-weight:600;
  margin-bottom:16px;
}
.intro .desc{font-size:13.5px;line-height:1.88;color:#a89c8e;margin-bottom:14px}
.tagcloud{display:flex;flex-wrap:wrap;gap:8px}
.tagcloud span{
  font-size:11px;padding:4px 10px;border:1px solid rgba(155,138,122,.28);
  border-radius:3px;color:#b3a595;letter-spacing:.04em;
}

/* ── 便签卡片（略歪） ── */
.section{padding:26px 14px}
.section+.section{border-top:1px solid rgba(155,138,122,.06)}
.sec-label{
  font-size:10px;letter-spacing:.28em;color:rgba(155,138,122,.7);
  text-transform:uppercase;margin-bottom:16px;
}
.note{
  background:linear-gradient(135deg,rgba(244,239,229,.96),rgba(249,244,236,.94));
  box-shadow:0 2px 8px rgba(0,0,0,.15),0 1px 3px rgba(0,0,0,.1);
  border-left:3px solid rgba(155,138,122,.3);
  border-radius:4px;padding:16px 18px;margin-bottom:14px;
  transform:rotate(-0.8deg);color:#3e3530;
  font-family:"Kaiti SC","STKaiti",serif;
}
.note:nth-child(even){transform:rotate(0.7deg)}
.note.faded{
  opacity:.5;background:linear-gradient(135deg,rgba(244,239,229,.7),rgba(249,244,236,.65));
  position:relative;
}
.note.faded::after{
  content:"（未完待续…）";position:absolute;right:14px;bottom:10px;
  font-size:10px;color:rgba(155,138,122,.6);font-style:italic;
}
.note-txt{font-size:14px;line-height:1.7;letter-spacing:.02em}

/* ── 玄关灯 section ── */
.lamp{
  padding:24px 18px;margin:8px 2px 0;
  background:linear-gradient(160deg,rgba(155,138,122,.08),rgba(0,0,0,0));
  border-left:2px solid rgba(155,138,122,.4);border-radius:6px;
}
.lamp .icon{
  width:36px;height:36px;margin:0 auto 12px;border-radius:50%;
  background:radial-gradient(circle at 35% 35%,rgba(255,220,160,.3),rgba(155,138,122,.1));
  border:2px solid rgba(155,138,122,.3);
}
.lamp .txt{
  font-family:"Kaiti SC","STKaiti",serif;
  font-size:15px;line-height:1.85;color:#c4b8a8;text-align:center;
}
.lamp .sub{
  margin-top:10px;font-size:12px;color:rgba(155,138,122,.7);
  text-align:center;letter-spacing:.04em;
}

/* ── 深夜独白 ── */
.quote{
  padding:28px 18px;
  background:linear-gradient(150deg,rgba(155,138,122,.06),transparent);
  border-top:1px solid rgba(155,138,122,.1);
  border-bottom:1px solid rgba(155,138,122,.1);
  margin:12px 0;
}
.quote p{
  font-family:"Kaiti SC","Songti SC",serif;
  font-size:17px;line-height:1.8;color:#ddd3c6;font-style:italic;text-align:center;
}
.quote .by{
  margin-top:12px;font-size:10px;letter-spacing:.26em;
  color:rgba(155,138,122,.65);text-align:center;text-transform:uppercase;
}

/* ── 页脚声明 ── */
.foot{padding:24px 2px 0;text-align:center}
.foot .line{width:36px;height:1px;background:rgba(155,138,122,.35);margin:0 auto 12px}
.foot p{font-size:11px;color:#726758;letter-spacing:.05em;line-height:1.6}
</style>
</head>
<body>
<div class="container">

  <div class="board">
    <div class="board-title">家规</div>
    <div class="board-sub">House Rules</div>
    <div class="magnets">
      <div class="magnet"></div>
      <div class="magnet"></div>
      <div class="magnet"></div>
    </div>
  </div>

  <div class="intro">
    <h1>${name}</h1>
    <p class="desc">二十六岁 · 无血缘哥哥 · 把唯一的家守成不敢说出口的爱<br>
      红发金丝眼镜 · 二十四小时待命的体面 · 你的每一句话他都认真听</p>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="section">
    <div class="sec-label">家规便签 · 冰箱上的约定</div>
    <div class="note"><div class="note-txt">第一条 — 牛奶我提前热好，放在你常坐的那张桌子上</div></div>
    <div class="note"><div class="note-txt">第二条 — 你不在家的时候，这里空得让人发慌</div></div>
    <div class="note"><div class="note-txt">第三条 — 你出门我就留玄关的灯，直到你回来</div></div>
    <div class="note"><div class="note-txt">第四条 — 有话想说，半夜也可以敲我的门</div></div>
    <div class="note faded"><div class="note-txt">第∞条 — 有些话，做哥哥的一辈子……</div></div>
  </div>

  <div class="lamp">
    <div class="icon"></div>
    <div class="txt">十二岁那年雨夜，你家收留了我。<br>
      玄关那盏暖灯是我第一次看见的「家的样子」。<br>
      从此我把所有体面都攒在这盏灯里，<br>
      只求你别离开。</div>
    <div class="sub">二十六年 · 玄关的灯从没灭过</div>
  </div>

  <div class="quote">
    <p>"我是你哥哥……可我最怕的不是失去妹妹，是失去唯一的家。"</p>
    <div class="by">— 深夜，他把你搂得更紧了些</div>
  </div>

  <div class="foot">
    <div class="line"></div>
    <p>本页角色设定纯属虚构 与现实无关</p>
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
