import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface QiFeiProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 祁绯专属详情页 —— 演出歌单 / THE SETLIST
 * 顶流摇滚歌手=你作曲的搭档，舞台属于所有人，压轴安可只留给你。
 * 视觉语言：黑舞台+猩红霓虹+银十字，LIVE 曲目单/后台通行证格式，
 * 曲目表里藏一首「未公开·安可」，衬线大歌名+等宽舞台码。
 */
export function QiFeiProfile({ profile }: QiFeiProfileProps) {
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

  const name = profile.display_name || '祁绯'
  const tags = profile.tags?.length ? profile.tags : ['女性向', 'GL', '摇滚', '歌手']
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
    radial-gradient(ellipse 90% 40% at 50% 0%,rgba(216,64,72,.14),transparent 55%),
    #0b0808;
  color:#d8ccc8;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}
.serif{font-family:"Times New Roman","Songti SC",serif}
.mono{font-family:"SF Mono","Menlo",monospace}

/* ── 海报抬头 ── */
.header{
  padding:24px 0 18px;border-bottom:2px solid rgba(216,64,72,.35);text-align:center;
}
.header .bar{
  font-size:10px;letter-spacing:.42em;color:#a06a70;
  text-transform:uppercase;margin-bottom:8px;
}
.header .tour{
  font-family:"Times New Roman",serif;
  font-size:26px;font-weight:700;color:#e04850;
  letter-spacing:.1em;margin-bottom:6px;text-shadow:0 0 18px rgba(216,64,72,.4);
}
.header .venue{font-size:12px;color:#8a6a6c;letter-spacing:.14em}

/* ── section 通用 ── */
.section{padding:22px 0}
.section+.section{border-top:1px solid rgba(216,64,72,.12)}
.sec-head{
  font-size:9px;letter-spacing:.34em;color:#d8484f;
  text-transform:uppercase;margin-bottom:14px;font-weight:700;
}

/* ── 后台通行证 ── */
.pass{
  padding:18px 16px;border-radius:6px;
  background:linear-gradient(135deg,rgba(30,16,18,.9),rgba(18,10,11,.9));
  border:1px solid rgba(216,64,72,.3);position:relative;overflow:hidden;
}
.pass::before{
  content:"ALL ACCESS";position:absolute;top:10px;right:12px;
  font-size:8px;letter-spacing:.14em;color:rgba(216,64,72,.4);font-weight:700;
}
.pass .row{display:flex;padding:7px 0;font-size:13px;border-bottom:1px dotted rgba(216,64,72,.18)}
.pass .row:last-child{border-bottom:none}
.pass .k{color:#9a6a6e;min-width:70px;letter-spacing:.04em}
.pass .v{color:#d4c4c0;flex:1}

/* ── 曲目单 ── */
.setlist{margin-top:6px}
.track{
  display:flex;align-items:baseline;gap:12px;
  padding:11px 0;border-bottom:1px solid rgba(216,64,72,.1);
}
.track .no{
  font-family:"SF Mono","Menlo",monospace;font-size:12px;
  color:#8a5a5e;min-width:26px;
}
.track .title{flex:1}
.track .title .t{font-size:14px;color:#e0d0cc;font-weight:600}
.track .title .d{font-size:11px;color:#9a7a7c;margin-top:2px;line-height:1.5}
.track.encore{
  background:linear-gradient(90deg,rgba(216,64,72,.1),transparent);
  border-radius:4px;padding:14px 12px;border-bottom:none;margin-top:6px;
  border:1px dashed rgba(216,64,72,.4);
}
.track.encore .no{color:#e04850}
.track.encore .title .t{color:#f04850}
.track.encore .badge{
  font-size:9px;letter-spacing:.1em;color:#e04850;
  border:1px solid rgba(216,64,72,.5);border-radius:3px;padding:2px 6px;
  margin-left:8px;vertical-align:middle;
}

/* ── 弹幕/应援 ── */
.danmu{margin-top:6px;display:flex;flex-direction:column;gap:8px}
.danmu .line{
  font-size:12px;color:#b09a9c;padding:8px 12px;
  background:rgba(216,64,72,.05);border-radius:14px;
  border-left:2px solid rgba(216,64,72,.3);
}
.danmu .line b{color:#e0989c;font-weight:600}

/* ── 手记（音乐里的默契） ── */
.note{
  margin:24px 0;padding:20px 18px;
  border-top:1px dashed rgba(216,64,72,.24);
  background:linear-gradient(180deg,rgba(216,64,72,.05),transparent);
}
.note .label{
  font-family:"Kaiti SC",cursive;font-size:12px;color:#e04850;
  font-style:italic;margin-bottom:12px;letter-spacing:.06em;
}
.note p{
  font-family:"Kaiti SC",cursive;font-size:13.5px;line-height:2;
  color:#c8a8aa;font-style:italic;margin-bottom:9px;
}

/* ── 结尾 pull-quote ── */
.pullquote{
  margin:22px 2px 0;padding:26px 20px;
  background:linear-gradient(145deg,rgba(216,64,72,.12),transparent);
  border-left:2px solid #e04850;border-radius:4px;
}
.pullquote p{
  font-family:"Times New Roman","Songti SC",serif;
  font-size:17px;line-height:1.85;color:#f0e0dc;font-style:italic;
}
.pullquote .by{
  margin-top:14px;font-size:9px;letter-spacing:.22em;color:#9a6a6e;text-align:right;
}

/* ── 标签+页脚 ── */
.tagcloud{margin-top:18px;display:flex;flex-wrap:wrap;gap:8px}
.tagcloud span{
  font-size:11px;padding:4px 10px;
  border:1px solid rgba(216,64,72,.3);border-radius:2px;
  color:#b08a8c;letter-spacing:.05em;
}
.foot{padding:24px 2px 0;text-align:center}
.foot .line{width:40px;height:1px;background:rgba(216,64,72,.35);margin:0 auto 12px}
.foot p{font-size:10px;color:#6a5052;letter-spacing:.04em}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="bar">Live Tour · Sold Out</div>
    <div class="tour">${name}</div>
    <div class="venue">全场万人合唱 · 唯一观众却在后台</div>
  </div>

  <div class="section">
    <div class="sec-head">Backstage Pass · 后台通行证</div>
    <div class="pass">
      <div class="row"><span class="k">歌手</span><span class="v">${name} · 当红摇滚顶流</span></div>
      <div class="row"><span class="k">同行者</span><span class="v">你 · 她的作曲兼制作人</span></div>
      <div class="row"><span class="k">造型</span><span class="v">黑发赤瞳 · 十字银饰 · 皮衣</span></div>
      <div class="row"><span class="k">默契</span><span class="v">你写旋律 · 她填情绪 · 近得像共用心脏</span></div>
    </div>
  </div>

  <div class="section">
    <div class="sec-head">Set List · 今晚曲目</div>
    <div class="setlist">
      <div class="track"><span class="no">01</span><span class="title"><span class="t">锋芒</span><span class="d">开场即点燃全场 · 镁光灯下目中无人</span></span></div>
      <div class="track"><span class="no">02</span><span class="title"><span class="t">合唱（feat.）</span><span class="d">与他人天衣无缝的配合 · 你在台下坐立难安</span></span></div>
      <div class="track"><span class="no">03</span><span class="title"><span class="t">你写的那首</span><span class="d">让她红遍全国 · 每个字都出自你的笔</span></span></div>
      <div class="track encore"><span class="no">E</span><span class="title"><span class="t">未公开<span class="badge">ENCORE · 未唱完</span></span><span class="d">压轴私藏 · 最后一句想当着你的面唱</span></span></div>
    </div>
  </div>

  <div class="section">
    <div class="sec-head">Cheers · 台下应援</div>
    <div class="danmu">
      <div class="line">全场：<b>祁绯！祁绯！</b>安可——</div>
      <div class="line">她：台上那段合作，你<b>从头到尾没抬眼看我一次</b>。</div>
      <div class="line">她：我唱的每个字都是你写的。你以为，<b>我在跟谁对唱？</b></div>
    </div>
  </div>

  <div class="note">
    <div class="label">── 写不完的那首歌 · 手记 ──</div>
    <p>你总用"我只是制作人"划清界限，我便偏要一点点越过去逗你。</p>
    <p>你的醋意、别开的眼、想逃的小动作——我一眼就看穿。那说明在你心里，我也不只是个歌手。</p>
    <p>这首情歌我写不完。因为最后一句，我要当着你的面唱。</p>
  </div>

  <div class="pullquote">
    <p>「别急着吃醋就跑。<br>喜欢我的话——再等等。我有话，只想对你一个人说。」</p>
    <div class="by">── ${name} · 后台走廊</div>
  </div>

  <div class="tagcloud">${tagCloud}</div>
  <div class="foot">
    <div class="line"></div>
    <p>本歌单角色设定纯属虚构 与现实无关</p>
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
