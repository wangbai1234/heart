import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface GuNanqiaoProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 顾南乔专属详情页 —— 校园横线笔记 / CAMPUS NOTEBOOK
 * 视觉语言：横线笔记纸 + 荧光笔划线 + 便利贴 + 手写涂鸦
 * 配色：纸白 + 浅蓝横线 + 橙荧光笔 + 青春天蓝 + 暖橘，少年感清新
 */
export function GuNanqiaoProfile({ profile }: GuNanqiaoProfileProps) {
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

  const name = profile.display_name || '顾南乔'
  const tags = profile.tags?.length ? profile.tags : ['校园', '年下', '忠犬', '女性向', '青梅竹马']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#f9fafb;
  color:#2c3e50;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;
  padding:0 0 44px;
  background-image:repeating-linear-gradient(transparent,transparent 27px,#d6e4f0 27px,#d6e4f0 28px);
  background-size:100% 28px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}

/* ── 笔记本抬头 ── */
.header{
  padding:32px 0 20px;
  position:relative;
}
.corner-fold{
  position:absolute;top:0;right:10px;
  width:0;height:0;
  border-left:28px solid transparent;
  border-top:28px solid #5a9bd5;
  opacity:.3;
}
.date{
  font-family:"Courier New",monospace;font-size:11px;
  color:#7a95b0;letter-spacing:.1em;margin-bottom:8px;
}
.title{
  font-family:"PingFang SC",sans-serif;font-size:36px;
  color:#5a9bd5;letter-spacing:.08em;margin-bottom:6px;
  position:relative;display:inline-block;
}
.title::after{
  content:'';position:absolute;bottom:-4px;left:0;right:0;
  height:8px;background:rgba(255,179,71,.35);z-index:-1;
}
.subtitle{
  font-size:12px;color:#90a4b7;letter-spacing:.15em;
}

/* ── 主档案 ── */
.profile{padding:28px 0;border-bottom:1px dashed rgba(0,0,0,.08)}
.name{
  font-family:"PingFang SC",sans-serif;font-size:32px;
  color:#2c3e50;letter-spacing:.1em;margin-bottom:6px;
}
.role{font-size:12px;color:#7a95b0;letter-spacing:.08em;margin-bottom:14px}
.tags{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:18px}
.tags span{
  font-size:10px;padding:4px 10px;
  background:rgba(90,155,213,.1);border:1px solid rgba(90,155,213,.3);
  border-radius:12px;color:#5a9bd5;letter-spacing:.06em;
}
.bio{font-size:13px;line-height:1.85;color:#546e7a;margin-bottom:16px}

/* ── 便利贴墙 ── */
.stickies{padding:24px 0;display:flex;flex-direction:column;gap:14px}
.sticky{
  padding:14px 16px;
  background:#fff9e6;
  border-left:3px solid #ffb347;
  border-radius:2px 8px 8px 2px;
  box-shadow:2px 2px 8px rgba(0,0,0,.08);
  position:relative;
  transform:rotate(-0.5deg);
}
.sticky:nth-child(2){transform:rotate(0.5deg);background:#ffe6f0;border-left-color:#ff8fab}
.sticky:nth-child(3){transform:rotate(-0.3deg);background:#e6f7ff;border-left-color:#5a9bd5}
.sticky .label{
  font-family:"Courier New",monospace;font-size:10px;
  color:rgba(0,0,0,.5);letter-spacing:.1em;margin-bottom:6px;
}
.sticky .text{font-size:13px;line-height:1.7;color:#2c3e50}

/* ── 涂鸦区 ── */
.doodle{padding:24px 0;border-top:1px dashed rgba(0,0,0,.08)}
.sec-title{
  font-size:13px;color:#5a9bd5;letter-spacing:.1em;margin-bottom:14px;
  position:relative;display:inline-block;
}
.sec-title::before{
  content:'☆';position:absolute;left:-20px;top:0;
  color:#ffb347;font-size:14px;
}
.quote{
  padding:16px 20px;
  background:linear-gradient(135deg,rgba(90,155,213,.06),transparent);
  border-left:3px solid #5a9bd5;
  border-radius:0 8px 8px 0;
  margin-bottom:12px;
}
.quote p{
  font-family:"Kaiti SC",serif;
  font-size:15px;line-height:1.8;color:#2c3e50;font-style:italic;
}
.quote .sign{
  margin-top:10px;font-size:10px;letter-spacing:.15em;
  color:#90a4b7;
}

/* ── 页脚 ── */
.foot{padding:24px 0 0;text-align:center}
.foot .icon{font-size:16px;margin-bottom:8px;opacity:.6}
.foot p{font-size:10px;color:#b0bec5;letter-spacing:.06em;line-height:1.5}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="corner-fold"></div>
    <div class="date">2024.09 · 学期笔记</div>
    <div class="title">${name}</div>
    <div class="subtitle">那个从小跟在我身后的学弟 · 现在长得比我高了</div>
  </div>

  <div class="profile">
    <div class="name">${name}</div>
    <div class="role">二十岁 · 邻家学弟 · 比我小两岁却总想护着我</div>
    <div class="tags">${tagCloud}</div>
    <p class="bio">他喊我姐姐的语气，从来都不是真的把我当姐姐。阳光、黏人、笑起来有颗小虎牙——可他看我的眼神，早就越过了亲人的界限。</p>
  </div>

  <div class="stickies">
    <div class="sticky">
      <div class="label">记录①</div>
      <div class="text">他会理直气壮地占用我所有周末，说「姐姐今天陪我去图书馆好不好」——我说不好，他就撒娇到我同意为止。</div>
    </div>
    <div class="sticky">
      <div class="label">记录②</div>
      <div class="text">校园里无数女生给他表白，他谁也不理。后来我才知道——他心里只装得下一个人，而且装了整整二十年。</div>
    </div>
    <div class="sticky">
      <div class="label">记录③</div>
      <div class="text">有男生来搭讪时，他会瞬间收起笑脸，把我的手扣进他手心里，声音不高不低恰好让对方听见：「她有人了。」</div>
    </div>
  </div>

  <div class="doodle">
    <div class="sec-title">涂鸦 · 他说过的话</div>
    <div class="quote">
      <p>姐姐，我比你小两岁怎么了？照样能把你宠成小朋友。</p>
      <div class="sign">放学后的空教室，他把我困在椅背里说的</div>
    </div>
    <div class="quote">
      <p>你再这样招人，我可就不管什么分寸了。我喊你姐姐，你可别真当我是弟弟。</p>
      <div class="sign">夕阳拉长影子的那个下午，他凑得很近</div>
    </div>
  </div>

  <div class="foot">
    <div class="icon">☆</div>
    <p>校园笔记本 · 青春日常 · 角色设定纯属虚构</p>
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

