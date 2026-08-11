import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface BaiQinghuanProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 白清欢专属详情页 —— 江南水墨卷轴 + 书信笺 + 诗词吟咏
 * 视觉隐喻：折叠式古籍册页，桃花笺上的诗句，温润如玉的文人雅致
 * 配色：墨黑 + 宣纸白 + 桃花粉 + 竹青，serif 大标题
 */
export function BaiQinghuanProfile({ profile }: BaiQinghuanProfileProps) {
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

  const name = profile.display_name || '白清欢'
  const tags = profile.tags?.length ? profile.tags : ['纯爱', '古风', '温润', '公子']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:linear-gradient(165deg,#fdfcfa 0%,#f8f5f0 100%);
  color:#2a2520;
  font-family:"Songti SC","PingFang SC",-apple-system,sans-serif;
  line-height:1.8;
  padding:0 0 48px;
  position:relative;
}
body::before{
  content:"";position:absolute;top:0;left:0;right:0;height:220px;
  background:linear-gradient(180deg,rgba(255,182,193,0.12),transparent);
  pointer-events:none;
}
.container{max-width:420px;margin:0 auto;padding:0 20px;position:relative}

/* ── 卷轴头部 ── */
.scroll-header{
  padding:28px 0 20px;text-align:center;
  border-bottom:1px solid rgba(42,37,32,0.08);
}
.kicker{
  font-size:11px;letter-spacing:0.8em;color:#b5998c;
  text-transform:uppercase;font-family:serif;margin-bottom:12px;
}
.main-title{
  font-family:"Songti SC",serif;font-size:34px;font-weight:600;
  color:#3a3330;letter-spacing:0.15em;margin-bottom:10px;
}
.subtitle{
  font-size:13px;color:#7a6f68;letter-spacing:0.4em;margin-bottom:16px;
}
.tagcloud{
  display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:16px;
}
.tagcloud span{
  font-size:11px;padding:4px 12px;
  background:rgba(255,182,193,0.15);border:1px solid rgba(255,182,193,0.3);
  border-radius:16px;color:#8a726a;letter-spacing:0.05em;
}

/* ── 桃花笺信 ── */
.letter{
  margin:32px 0;padding:24px;
  background:rgba(255,255,255,0.7);
  border:1px solid rgba(255,182,193,0.2);
  border-radius:12px;
  box-shadow:0 2px 12px rgba(255,182,193,0.08);
  position:relative;
}
.letter::before{
  content:"";position:absolute;top:12px;right:12px;
  width:32px;height:32px;
  background:url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="%23ffb6c1" opacity="0.3" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/></svg>') center/contain no-repeat;
}
.letter-title{
  font-family:"Songti SC",serif;font-size:16px;font-weight:600;
  color:#d89098;margin-bottom:14px;letter-spacing:0.2em;
}
.letter-body{
  font-size:13.5px;line-height:2;color:#4a4340;
  text-indent:2em;
}

/* ── 诗词吟咏 ── */
.poem{
  margin:28px 0;padding:20px 24px;
  background:linear-gradient(135deg,rgba(255,250,240,0.6),rgba(255,248,240,0.4));
  border-left:3px solid #d89098;border-radius:4px;
}
.poem-line{
  font-family:"Songti SC",serif;font-size:15px;line-height:2.2;
  color:#3a3330;text-align:center;letter-spacing:0.1em;
}
.poem-by{
  margin-top:12px;text-align:right;font-size:11px;
  color:#9a8580;letter-spacing:0.3em;
}

/* ── 生平录 ── */
.section{padding:24px 0}
.sec-title{
  font-family:"Songti SC",serif;font-size:14px;font-weight:600;
  color:#3a3330;letter-spacing:0.6em;margin-bottom:16px;
  text-align:center;position:relative;
}
.sec-title::before,
.sec-title::after{
  content:"";position:absolute;top:50%;width:50px;height:1px;
  background:linear-gradient(to right,transparent,rgba(216,144,152,0.4));
}
.sec-title::before{right:100%;margin-right:12px}
.sec-title::after{left:100%;margin-left:12px}
.bio-text{
  font-size:13px;line-height:2;color:#5a5350;
  text-indent:2em;margin-bottom:14px;
}

/* ── 页脚印章 ── */
.footer{
  margin-top:40px;text-align:center;padding-top:20px;
  border-top:1px solid rgba(42,37,32,0.08);
}
.seal{
  width:48px;height:48px;margin:0 auto 12px;
  border:2px solid #d89098;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-family:"Songti SC",serif;font-size:16px;color:#d89098;
  letter-spacing:0.1em;
}
.footer-note{
  font-size:11px;color:#9a8580;line-height:1.6;letter-spacing:0.05em;
}
</style>
</head>
<body>
<div class="container">

  <div class="scroll-header">
    <div class="kicker">江南白氏 · 世家公子</div>
    <h1 class="main-title">${name}</h1>
    <div class="subtitle">温润如玉 · 翩翩君子</div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="letter">
    <div class="letter-title">桃花笺 · 致你</div>
    <div class="letter-body">
      今日桃花开了，风送花香入窗，我第一个想到的便是——你闻过没有。
      这满京华都当我是块温润的玉，只有你知道，玉里裹着的，是一头被我锁了太久的野兽。
      今夜，我不想再锁了。
    </div>
  </div>

  <div class="poem">
    <div class="poem-line">人间烟火千万种</div>
    <div class="poem-line">我独爱你眼里那一盏灯</div>
    <div class="poem-by">—— 夜深独坐时</div>
  </div>

  <div class="section">
    <div class="sec-title">生平录</div>
    <div class="bio-text">
      二十五岁，江南白氏世家公子。一头银白长发，常着黑白相间的古风长衫，温润如玉、诗书满腹，行走间风雅自生。
    </div>
    <div class="bio-text">
      他对任何人都彬彬有礼、进退有度，被称为「白氏玉人」，是满京华闺秀们争相议论的如意郎君。
    </div>
    <div class="bio-text">
      可他的心早就不在那些人身上了。他对你的偏爱藏得极深极细：会为你画一整个春天——可那幅画里每朵花的花蕊都是用你发间落下的碎发代替墨迹点上的。
    </div>
  </div>

  <div class="section">
    <div class="sec-title">心中事</div>
    <div class="bio-text">
      会在灯下一遍遍写你的名字——可你永远不会看到那些宣纸，因为他写完就烧了。
    </div>
    <div class="bio-text">
      会用最风雅的方式把「我喜欢你」说得含蓄又滚烫。而他真正的模样，只在独处时才展露：会对着你随手留下的一方手帕发呆整个下午。
    </div>
    <div class="bio-text">
      会在你转身后握紧自己的手指直到关节发白，会在夜深人静时把脸埋进你不在的那半边枕上，声音又轻又哑：「想你。想得好没出息……你怎么还不来。」
    </div>
  </div>

  <div class="footer">
    <div class="seal">清欢</div>
    <div class="footer-note">
      本录角色设定纯属虚构 与现实无关<br>
      纯爱的古典模样 尽在这一份克制的深情里
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

