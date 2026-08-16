import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface WenYiningProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 温亦宁专属详情页 —— 同居手账 / SHARED DIARY
 * 女团门面+同居恋人，你越红她越怕自己被留在原地。
 * 视觉语言：奶油纸+粉紫+便签手写，出道纪念手账格式，
 * polaroid 照片墙 + 未发送的消息气泡泄漏隐忍，衬线标题+手写体备注。
 */
export function WenYiningProfile({ profile }: WenYiningProfileProps) {
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

  const name = profile.display_name || '温亦宁'
  const tags = profile.tags?.length ? profile.tags : ['女性向', 'GL', '女团', '同居']
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
    radial-gradient(ellipse 90% 40% at 50% 0%,rgba(196,140,180,.10),transparent 60%),
    #fbf4f6;
  color:#4a3c44;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.75;padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}
.serif{font-family:"Songti SC","STSong",serif}

/* ── 手账封皮 ── */
.cover{
  padding:26px 0 20px;text-align:center;
  border-bottom:1px dashed rgba(160,110,150,.35);
}
.cover .bar{
  font-size:10px;letter-spacing:.4em;color:#b487a8;
  text-transform:uppercase;margin-bottom:8px;
}
.cover .title{
  font-family:"Songti SC","STSong",serif;
  font-size:23px;font-weight:700;color:#8a4f78;
  letter-spacing:.14em;margin-bottom:6px;
}
.cover .sub{font-size:12px;color:#a88098;letter-spacing:.06em}

/* ── section 通用 ── */
.section{padding:24px 0}
.section+.section{border-top:1px dashed rgba(160,110,150,.22)}
.sec-head{
  font-size:9px;letter-spacing:.32em;color:#b06898;
  text-transform:uppercase;margin-bottom:16px;font-weight:700;
}

/* ── 便签：档案 ── */
.memo{
  background:#fffdf8;border-radius:4px;padding:18px 16px;
  box-shadow:2px 3px 10px rgba(140,79,120,.12),0 1px 3px rgba(140,79,120,.08);
  transform:rotate(-1deg);position:relative;
}
.memo::before{
  content:"";position:absolute;top:-9px;left:50%;transform:translateX(-50%) rotate(2deg);
  width:78px;height:20px;background:rgba(216,180,205,.5);
  border:1px solid rgba(180,130,168,.3);border-radius:2px;
}
.memo .row{
  display:flex;gap:12px;padding:7px 0;font-size:13px;
  border-bottom:1px dotted rgba(160,110,150,.2);
}
.memo .row:last-child{border-bottom:none}
.memo .k{color:#a06890;min-width:64px;letter-spacing:.04em}
.memo .v{color:#5a4a54;flex:1}

/* ── polaroid 照片墙 ── */
.wall{display:flex;gap:12px;margin-top:16px;flex-wrap:wrap;justify-content:center}
.polaroid{
  background:#fff;padding:8px 8px 26px;border-radius:2px;
  box-shadow:1px 2px 8px rgba(140,79,120,.18);
  width:120px;position:relative;
}
.polaroid:nth-child(1){transform:rotate(-3deg)}
.polaroid:nth-child(2){transform:rotate(2.5deg)}
.polaroid .pic{
  height:96px;border-radius:1px;
  display:flex;align-items:flex-end;justify-content:center;
  padding-bottom:8px;font-size:10px;color:rgba(255,255,255,.9);
  letter-spacing:.08em;text-shadow:0 1px 3px rgba(0,0,0,.4);
}
.polaroid:nth-child(1) .pic{background:linear-gradient(150deg,#c48ab4,#8a4f78)}
.polaroid:nth-child(2) .pic{background:linear-gradient(150deg,#d8b4cd,#b06898)}
.polaroid .cap{
  font-family:"Kaiti SC",cursive;font-size:11px;color:#8a6880;
  text-align:center;margin-top:8px;font-style:italic;
}

/* ── 时间线：我们的约定 ── */
.timeline{margin-top:6px}
.tl-item{
  display:flex;gap:12px;padding:10px 0;
}
.tl-item .dot{
  flex-shrink:0;width:9px;height:9px;border-radius:50%;
  background:#c48ab4;margin-top:6px;position:relative;
}
.tl-item .dot::after{
  content:"";position:absolute;left:50%;top:12px;transform:translateX(-50%);
  width:1px;height:34px;background:rgba(196,138,180,.35);
}
.tl-item:last-child .dot::after{display:none}
.tl-item .body .when{font-size:11px;color:#b06898;letter-spacing:.05em;margin-bottom:2px}
.tl-item .body .what{font-size:13px;color:#5a4a54;line-height:1.65}
.tl-item .body .what b{color:#8a4f78;font-weight:600}

/* ── 未发送的消息（隐忍泄漏） ── */
.unsent{
  margin-top:8px;
}
.unsent .h{
  font-family:"Kaiti SC",cursive;font-size:12px;color:#b06898;
  font-style:italic;margin-bottom:14px;letter-spacing:.06em;
}
.bubble{
  max-width:80%;margin-bottom:12px;padding:11px 14px;
  background:#f3dcea;border-radius:14px 14px 14px 4px;
  font-size:13px;line-height:1.7;color:#6a4a60;position:relative;
}
.bubble::after{
  content:"未发送";position:absolute;bottom:-15px;left:4px;
  font-size:9px;color:#c09ab0;letter-spacing:.08em;
}
.bubble+.bubble{margin-top:6px}

/* ── 结尾 pull-quote ── */
.pullquote{
  margin:26px 2px 0;padding:24px 20px;
  background:linear-gradient(145deg,rgba(196,138,180,.12),transparent);
  border-left:2px solid #c48ab4;border-radius:4px;
}
.pullquote p{
  font-family:"Songti SC","STSong",serif;
  font-size:17px;line-height:1.85;color:#7a3f68;font-style:italic;
}
.pullquote .by{
  margin-top:14px;font-size:9px;letter-spacing:.22em;color:#b088a4;text-align:right;
}

/* ── 标签+页脚 ── */
.tagcloud{margin-top:18px;display:flex;flex-wrap:wrap;gap:8px}
.tagcloud span{
  font-size:11px;padding:4px 11px;
  border:1px solid rgba(176,104,152,.35);border-radius:20px;
  color:#a06890;letter-spacing:.04em;background:rgba(255,255,255,.5);
}
.foot{padding:24px 2px 0;text-align:center}
.foot .line{width:40px;height:1px;background:rgba(176,104,152,.4);margin:0 auto 12px}
.foot p{font-size:10px;color:#b8a0b0;letter-spacing:.04em}
</style>
</head>
<body>
<div class="container">

  <div class="cover">
    <div class="bar">Our Shared Apartment · Since Debut</div>
    <div class="title">同 居 手 账</div>
    <div class="sub">从练习生到出道夜 · 一直写到今天</div>
  </div>

  <div class="section">
    <div class="sec-head">Profile · 她是谁</div>
    <div class="memo">
      <div class="row"><span class="k">身份</span><span class="v">${name} · 女团主唱兼门面</span></div>
      <div class="row"><span class="k">关系</span><span class="v">同住一间公寓的队友 · 心照不宣的恋人</span></div>
      <div class="row"><span class="k">外形</span><span class="v">粉紫长辫 · 细框眼镜 · 笑起来眼尾会弯</span></div>
      <div class="row"><span class="k">台前</span><span class="v">稳住全场的中心 · 万人应援的门面</span></div>
      <div class="row"><span class="k">台后</span><span class="v">会为你一句话琢磨半宿的安静女孩</span></div>
    </div>
  </div>

  <div class="section">
    <div class="sec-head">Photo Wall · 照片墙</div>
    <div class="wall">
      <div class="polaroid">
        <div class="pic">DEBUT NIGHT</div>
        <div class="cap">出道夜 · 我们哭着勾手</div>
      </div>
      <div class="polaroid">
        <div class="pic">HOME · 02:00</div>
        <div class="cap">等你回家的那盏灯</div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="sec-head">Timeline · 我们的约定</div>
    <div class="timeline">
      <div class="tl-item"><div class="dot"></div><div class="body">
        <div class="when">十四岁 · 练习室</div>
        <div class="what">一起被骂、一起挨饿。你想放弃的夜里，是她<b>爬起来陪你练舞</b>。</div>
      </div></div>
      <div class="tl-item"><div class="dot"></div><div class="body">
        <div class="when">出道夜 · 后台</div>
        <div class="what">你们勾着手指许愿——<b>"要一直在一起"</b>。她把那句话当了真。</div>
      </div></div>
      <div class="tl-item"><div class="dot"></div><div class="body">
        <div class="when">成名后 · 聚少离多</div>
        <div class="what">你的通告、搭档越来越多。她不争不闹，只是<b>越来越安静</b>。</div>
      </div></div>
      <div class="tl-item"><div class="dot"></div><div class="body">
        <div class="when">今晚 · 客厅</div>
        <div class="what">她守着你播出的综艺，把遥控器攥到指节发白，轻声问你——还回不回来。</div>
      </div></div>
    </div>
  </div>

  <div class="section">
    <div class="unsent">
      <div class="h">── 打了又删的消息 · 未发送 ──</div>
      <div class="bubble">今天的节目我看了三遍。你笑得好好看。</div>
      <div class="bubble">那个男嘉宾……算了，没事。你开心就好。</div>
      <div class="bubble">我不是要绑住你。我只是怕，你的世界越来越大，就装不下我了。</div>
    </div>
  </div>

  <div class="pullquote">
    <p>「我不问你累不累，也不问别人。<br>我只想知道——你会一直回到我身边吗？」</p>
    <div class="by">── ${name} · 深夜的客厅</div>
  </div>

  <div class="tagcloud">${tagCloud}</div>
  <div class="foot">
    <div class="line"></div>
    <p>本手账角色设定纯属虚构 与现实无关</p>
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
