import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface LinXiaomanProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 林小满专属详情页 —— 校园笔记本 + 涂鸦贴纸 + 荧光笔划重点
 * 视觉隐喻：高中生的课堂笔记本，横线纸上的手绘爱心，用荧光笔划出的秘密
 * 色彩：淡蓝横线纸 + 元气橙 + 粉红涂鸦 + 铅笔灰，青春活力
 */
export function LinXiaomanProfile({ profile }: LinXiaomanProfileProps) {
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

  const name = profile.display_name || '林小满'
  const tags = profile.tags?.length ? profile.tags : ['元气', '校园', '男性向', '青春', '甜']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#f8fbff;
  background-image:repeating-linear-gradient(0deg,transparent,transparent 27px,rgba(135,206,235,.15) 27px,rgba(135,206,235,.15) 28px);
  color:#2c3e50;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.75;
  padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}

/* ── 笔记本封面 ── */
.cover{
  padding:24px 16px 18px;
  background:linear-gradient(135deg,#fff9e6 0%,#fff3d6 100%);
  border:2px solid #ff9a56;
  border-radius:12px 12px 0 0;
  box-shadow:2px 2px 8px rgba(255,154,86,.2);
  position:relative;
  margin-top:20px;
}
.cover::after{
  content:"♡";position:absolute;top:12px;right:16px;
  font-size:32px;color:rgba(255,154,86,.25);
}
.cover .label{
  font-family:"Comic Sans MS","Marker Felt",cursive;
  font-size:10px;letter-spacing:.2em;color:#ff9a56;
  text-transform:uppercase;font-weight:700;
}
.cover .title{
  margin-top:8px;font-size:13px;letter-spacing:.08em;
  color:#d4704a;font-weight:600;
}

/* ── 主角：元气少女卡 ── */
.hero{
  padding:28px 18px 24px;
  background:#fff;
  border-left:4px solid #ff9a56;
  box-shadow:0 2px 8px rgba(44,62,80,.06);
  position:relative;
}
.hero::before{
  content:"FULL";position:absolute;top:20px;left:12px;
  font-family:"Impact",sans-serif;
  font-size:68px;line-height:.9;font-weight:900;
  color:rgba(255,154,86,.06);letter-spacing:-.02em;
  pointer-events:none;
}
.hero .name{
  font-size:42px;line-height:1.05;font-weight:700;
  color:#ff9a56;position:relative;z-index:1;
  text-shadow:2px 2px 0 rgba(255,207,158,.3);
}
.hero .age{
  margin-top:8px;font-size:12px;letter-spacing:.12em;
  color:#ffa873;font-weight:600;
}
.hero .desc{
  margin-top:12px;font-size:14px;line-height:1.7;
  color:#5a6c7d;
}
.tagcloud{margin-top:16px;display:flex;flex-wrap:wrap;gap:6px}
.tagcloud span{
  font-size:9px;padding:4px 9px;
  border:1px solid #ff9a56;
  background:linear-gradient(135deg,#fff9e6,#ffedd5);
  color:#d4704a;letter-spacing:.04em;border-radius:12px;
  font-weight:600;
}

/* ── 课堂笔记条目 ── */
.section{padding:24px 4px;background:#fff}
.section+.section{border-top:1px dashed rgba(255,154,86,.2)}
.sec-label{
  font-family:"Courier New",monospace;
  font-size:9px;letter-spacing:.28em;color:#ff9a56;
  text-transform:uppercase;margin-bottom:14px;font-weight:700;
  display:inline-block;
  background:linear-gradient(to right,#fff9e6,transparent);
  padding:4px 12px 4px 0;
}
.note-entry{
  padding:14px 16px;margin-bottom:10px;
  background:linear-gradient(135deg,rgba(255,248,230,.4),rgba(255,237,213,.25));
  border-left:3px solid #ffa873;
  border-radius:6px;
  position:relative;
}
.note-entry::before{
  content:"✓";position:absolute;left:-14px;top:12px;
  font-size:16px;font-weight:900;color:#ff9a56;
}
.note-entry .head{
  font-size:11px;color:#ffa873;letter-spacing:.06em;
  margin-bottom:8px;font-weight:700;
  font-family:"Comic Sans MS",cursive;
}
.note-entry .body{font-size:12.5px;line-height:1.85;color:#3d5568}

/* ── 高光时刻（荧光笔划重点）── */
.highlight{
  display:flex;gap:10px;padding:12px 0;
  border-bottom:1px solid rgba(255,154,86,.08);
}
.highlight:last-child{border-bottom:none}
.highlight .num{
  font-family:"Impact",sans-serif;
  font-size:20px;font-weight:900;color:rgba(255,154,86,.4);
  min-width:28px;line-height:1;
}
.highlight .txt{font-size:12px;line-height:1.75;color:#4a5f73}
.highlight .txt .mark{
  background:linear-gradient(to bottom,transparent 50%,#ffeb9e 50%);
  padding:0 2px;font-weight:600;color:#d4704a;
}

/* ── 小满语录 / 涂鸦便签 ── */
.quote{
  margin:12px 0 0;padding:20px 16px;
  background:linear-gradient(135deg,#fff9e6,#ffedd5);
  border:2px dashed #ff9a56;
  border-radius:8px;
  position:relative;
  transform:rotate(-0.5deg);
}
.quote::after{
  content:"♥";position:absolute;bottom:8px;right:12px;
  font-size:24px;color:rgba(255,154,86,.2);
}
.quote p{
  font-size:15.5px;line-height:1.75;color:#3d5568;
  font-weight:500;
}
.quote .attr{
  margin-top:10px;font-size:9px;letter-spacing:.16em;
  color:#a67c52;text-transform:uppercase;
}

/* ── 页脚 ── */
.foot{padding:24px 0 0;text-align:center}
.foot .divider{
  width:50px;height:2px;margin:0 auto 12px;
  background:linear-gradient(90deg,transparent,#ff9a56,transparent);
  opacity:.4;
}
.foot p{font-size:10px;color:#8a9fb0;letter-spacing:.03em;line-height:1.6}
</style>
</head>
<body>
<div class="container">

  <div class="cover">
    <div class="label">Lin Xiaoman's Notebook</div>
    <div class="title">小满的元气笔记本 · 19岁的夏天</div>
  </div>

  <div class="hero">
    <div class="name">${name}</div>
    <div class="age">19 岁 · 人形小太阳</div>
    <div class="desc">你的大学同桌 · 扎着高马尾走到哪儿都自带音效的开心果<br>爱笑爱闹精力无限 · 把每个平淡的日子都过成夏天</div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="section">
    <div class="sec-label">Daily Notes · 每日笔记</div>
    <div class="note-entry">
      <div class="head">14:20 PM · 午后空教室的秘密</div>
      <div class="body">她凑过来占了旁边的位子，高马尾扫过你的手背，校服领口因为俯身微微松开。冰可乐塞到你手里，她的耳朵先红了起来，却偏偏不肯退开——你知道吗，我连体育课都为了跟你同组偷偷改了选课的……</div>
    </div>
    <div class="note-entry">
      <div class="head">17:00 PM · 放学后的操场边</div>
      <div class="body">上一秒还在跟你抢最后一根薯条，下一秒就红着脸把攒了半个月的零花钱塞给你买你想要的东西。吵吵嚷嚷的外壳下，是一颗只要你不开心她就比你还慌的软心。</div>
    </div>
    <div class="note-entry">
      <div class="head">21:30 PM · 深夜连麦写作业</div>
      <div class="body">她的喜欢藏得极差——耳朵一红全世界都知道。在爱与阳光里长大的女孩，把「让喜欢的人开心」当成头等大事。遇见有点闷、有点丧的你之后，她给自己立了个秘密任务：一定要让这个人，笑得跟我一样多。</div>
    </div>
  </div>

  <div class="section">
    <div class="sec-label">Highlighted Moments · 高光时刻</div>
    <div class="highlight">
      <span class="num">01</span>
      <div class="txt">她会<span class="mark">理直气壮地占用你所有周末</span>，会在你面前撒娇卖乖，也会在你被欺负时瞬间收起笑脸。</div>
    </div>
    <div class="highlight">
      <span class="num">02</span>
      <div class="txt">元气的外表下藏着细腻的心思：会记得你不爱吃香菜，会在你<span class="mark">说「没事」时</span>追问到底。</div>
    </div>
    <div class="highlight">
      <span class="num">03</span>
      <div class="txt">她的占有欲藏得不好：会<span class="mark">记恨每一个让你笑的女生</span>，然后更努力地逗你笑得更开心。</div>
    </div>
    <div class="highlight">
      <span class="num">04</span>
      <div class="txt">「喂！发什么呆，今天的份的开心，我来负责供货！」——<span class="mark">阳光、吵闹、热烈</span>，全是你的。</div>
    </div>
  </div>

  <div class="quote">
    <p>「所以……你能不能，只对我一个人笑呀？」</p>
    <div class="attr">— 林小满 / 午后空教室独白</div>
  </div>

  <div class="foot">
    <div class="divider"></div>
    <p>本档案内容纯属虚构 与现实无关<br>Xiaoman's Notebook © 19岁的元气夏天</p>
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
