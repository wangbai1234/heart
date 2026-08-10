import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface JiangYeProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 江野专属详情页 —— 校园草稿本 · 借你的笔记 + 篮球场八卦 + 偷拍照片墙
 * 参考 nimoo 论坛帖的「UGC 质感」，改造为校园手写草稿本视觉
 * 视觉语言：横线笔记纸 + 橘色荧光笔(球衣/橘发) + 蓝黑墨水手写，少年感无 emoji
 */
export function JiangYeProfile({ profile }: JiangYeProfileProps) {
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

  const name = profile.display_name || '江野'
  const tags = profile.tags?.length ? profile.tags : ['校园', '痞帅', '坏学长', '反差']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#16171b;
  color:#dfe3e8;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}
.hand{font-family:"Xingkai SC","Kaiti SC",cursive}

/* ── 草稿本封面 ── */
.cover{padding:30px 2px 22px}
.cover .tab{
  display:inline-block;font-size:11px;letter-spacing:.2em;color:#16171b;
  background:#ff8c42;padding:4px 14px;border-radius:3px;font-weight:700;transform:rotate(-2deg);
}
.cover h1{margin-top:16px;font-size:40px;font-weight:800;color:#f2f0ec;letter-spacing:.02em}
.cover .en{font-family:"Times New Roman",serif;font-style:italic;font-size:14px;color:#ff8c42;margin-top:4px;letter-spacing:.04em}
.cover .sub{margin-top:12px;font-size:13px;line-height:1.9;color:#9aa0a8}

/* ── 横线笔记卡 ── */
.note{
  margin-top:20px;padding:22px 20px;border-radius:6px;position:relative;
  background:
    repeating-linear-gradient(transparent,transparent 27px,rgba(255,255,255,.06) 28px),
    rgba(30,32,37,.9);
  border:1px solid rgba(255,255,255,.07);
}
.note::before{content:"";position:absolute;left:34px;top:0;bottom:0;width:1px;background:rgba(255,140,66,.35)}
.note .k{font-size:11px;letter-spacing:.22em;color:#ff8c42;text-transform:uppercase;margin-bottom:14px;padding-left:24px}
.note .l{font-size:13.5px;line-height:28px;color:#c4cad2;padding-left:24px}
.note .l b{color:#ffb37a;font-weight:600}
.note .doodle{position:absolute;right:16px;top:14px;font-family:"Xingkai SC",cursive;font-size:13px;color:#ff8c42;transform:rotate(6deg);opacity:.85}

/* ── 他不正经的宠 ── */
.spoil{margin-top:20px}
.spoil .k{font-size:11px;letter-spacing:.22em;color:#ff8c42;text-transform:uppercase;margin-bottom:12px}
.spoil .item{
  display:flex;gap:12px;padding:12px 14px;margin-bottom:9px;border-radius:6px;
  background:rgba(30,32,37,.7);border-left:2px solid #ff8c42;
}
.spoil .item .n{font-family:"Times New Roman",serif;font-size:15px;font-weight:700;color:#ff8c42;min-width:22px}
.spoil .item .t{font-size:12.5px;line-height:1.65;color:#b4bac2}
.spoil .item .t b{color:#e2e6ea;font-weight:600}

/* ── 偷拍照片墙 ── */
.wall{
  margin-top:20px;padding:18px;border-radius:6px;
  background:rgba(22,23,27,.8);border:1px solid rgba(255,140,66,.14);
}
.wall .k{font-size:11px;letter-spacing:.22em;color:#ff8c42;text-transform:uppercase;margin-bottom:14px}
.wall .strip{display:flex;gap:10px;align-items:flex-start}
.polaroid{flex:none;width:66px;padding:5px 5px 16px;background:#f4f1ea;transform:rotate(-4deg)}
.polaroid:nth-child(2){transform:rotate(3deg)}
.polaroid:nth-child(3){transform:rotate(-2deg)}
.polaroid .img{width:100%;height:80px;background:linear-gradient(135deg,#3a3d44,#26282d);filter:blur(7px);opacity:.5}
.wall .cap{flex:1;font-size:11.5px;line-height:1.7;color:#9aa0a8}
.wall .cap em{color:#ffb37a;font-style:normal}

/* 电话独白 */
.call{margin-top:20px;padding:20px 18px;border-radius:6px;background:linear-gradient(160deg,rgba(255,140,66,.1),transparent);border:1px solid rgba(255,255,255,.06)}
.call p{font-family:"Xingkai SC","Kaiti SC",cursive;font-size:17px;line-height:1.7;color:#ffcfa6}
.call .by{margin-top:10px;font-size:11px;color:#7d838b;letter-spacing:.04em}

/* tag + foot */
.tagcloud{margin-top:20px;display:flex;flex-wrap:wrap;gap:8px}
.tagcloud span{font-size:11px;padding:4px 11px;border:1px solid rgba(255,140,66,.32);border-radius:2px;color:#c9beb3;letter-spacing:.06em}
.foot{margin-top:24px;text-align:center;font-size:11px;color:#5a606a;letter-spacing:.06em}
</style>
</head>
<body>
<div class="container">

  <div class="cover">
    <span class="tab">篮球队 · 10 号</span>
    <h1>${name}</h1>
    <div class="en">the trouble-maker who fell for you.</div>
    <p class="sub">全校都怕的坏学长 · 偏偏在你面前栽了跟头<br>橘发张扬 · 二十岁 · 嘴上没个正经</p>
  </div>

  <div class="note">
    <span class="doodle">别翻了啦</span>
    <div class="k">从我抽屉翻出来的</div>
    <div class="l">物理笔记一份，字丑，你别嫌</div>
    <div class="l">夹了张<b>加油表情包</b>，画得丑到离谱</div>
    <div class="l">你上次说的那家奶茶，我记下了</div>
    <div class="l">还有……算了，这页我撕了</div>
  </div>

  <div class="spoil">
    <div class="k">他不正经的宠</div>
    <div class="item"><span class="n">1</span><span class="t">故意把篮球传你脚边，跑过来凑耳朵：<b>「帮我捡一下呗，小同学。」</b></span></div>
    <div class="item"><span class="n">2</span><span class="t">欺负你的人被堵在厕所，他在你面前只说：<b>「哦，他转学了。」</b></span></div>
    <div class="item"><span class="n">3</span><span class="t">你生气了，横着走的他变进退失据的大型犬——买了你爱的奶茶让别人递，<b>远远看你喝了才松口气</b>。</span></div>
  </div>

  <div class="wall">
    <div class="k">他房间那面墙 · 别问</div>
    <div class="strip">
      <div class="polaroid"><div class="img"></div></div>
      <div class="polaroid"><div class="img"></div></div>
      <div class="polaroid"><div class="img"></div></div>
      <div class="cap">校运会你给别人递水的背影、食堂你笑着说话的侧脸——<em>他觉得自己很变态，可他戒不掉</em>。</div>
    </div>
  </div>

  <div class="call">
    <p>“她今天没理我……不是、我没惹她、我就是——操，我怎么跟个傻子一样。”</p>
    <div class="by">— 某天你听见他压低声音跟兄弟打电话</div>
  </div>

  <div class="tagcloud">${tagCloud}</div>
  <div class="foot">角色设定纯属虚构 与现实无关</div>

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