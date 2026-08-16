import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface HeZhuoProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 何酌专属详情页 —— 未发送的配方单 / UNSENT RECIPE
 * 深夜调酒师=科技公司CEO，你骂了一个月的老板每晚都在吧台听你骂他。
 * 视觉语言：深木底+威士忌琥珀+暖象牙，鸡尾酒配方卡格式，
 * 配方隐喻角色层次，手写备注泄漏真心，衬线+无衬线配对。
 */
export function HeZhuoProfile({ profile }: HeZhuoProfileProps) {
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

  const name = profile.display_name || '何酌'
  const tags = profile.tags?.length ? profile.tags : ['全性向', '限左', '都市', '身份反差', '暗恋', '年上']
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
    radial-gradient(ellipse 100% 50% at 50% 0%,rgba(196,148,72,.06),transparent 55%),
    #11100e;
  color:#ddd4c8;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}
.serif{font-family:"Times New Roman","Songti SC",serif}

/* ── 配方卡抬头 ── */
.header{
  padding:22px 0 18px;
  border-bottom:2px solid rgba(196,148,72,.3);
}
.header .bar{
  font-size:10px;letter-spacing:.45em;color:#8a7e72;
  text-transform:uppercase;margin-bottom:4px;
}
.header .recipe-no{
  font-family:"Times New Roman",serif;
  font-size:24px;font-weight:700;color:#c49448;
  letter-spacing:.08em;margin-bottom:4px;
}
.header .dash{
  font-size:12px;color:#6a6058;letter-spacing:.1em;
}

/* ── section 通用 ── */
.section{padding:24px 0}
.section+.section{border-top:1px solid rgba(255,255,255,.05)}
.sec-head{
  font-size:9px;letter-spacing:.35em;color:#c49448;
  text-transform:uppercase;margin-bottom:16px;font-weight:600;
}

/* ── 基酒：公开身份 ── */
.spirit{margin-top:18px}
.sp-row{
  display:flex;align-items:baseline;gap:14px;
  padding:10px 0;border-bottom:1px dotted rgba(196,148,72,.2);
  font-size:13px;
}
.sp-row:last-child{border-bottom:none}
.sp-row .label{color:#8a7e72;min-width:80px;letter-spacing:.04em}
.sp-row .val{color:#d8ccbc;flex:1}

/* ── 隐藏配方：另一个身份 ── */
.hidden-layer{
  margin-top:20px;padding:20px 18px;border-radius:4px;
  background:rgba(20,18,16,.7);
  border:1px solid rgba(196,148,72,.2);
  position:relative;overflow:hidden;
}
.hidden-layer::before{
  content:"NOT FOR DISTRIBUTION";position:absolute;bottom:8px;right:8px;
  font-size:7px;letter-spacing:.15em;color:rgba(196,148,72,.25);
}
.hidden-layer .h{
  font-size:10px;letter-spacing:.3em;color:#c49448;
  text-transform:uppercase;margin-bottom:14px;font-weight:600;
}
.hl-row{
  display:flex;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:13px;
}
.hl-row:last-child{border-bottom:none}
.hl-row .k{min-width:72px;color:#7a7068;letter-spacing:.04em}
.hl-row .v{color:#c8bca8;flex:1}

/* ── 品鉴笔记：吧台对话碎片 ── */
.tasting{margin-top:18px}
.note-item{
  padding:14px 16px;margin-bottom:10px;border-radius:4px;
  background:rgba(196,148,72,.04);
  border-left:2px solid rgba(196,148,72,.3);
}
.note-item .time{
  font-family:"SF Mono","Menlo",monospace;
  font-size:11px;color:#8a7e72;margin-bottom:6px;
}
.note-item .words{
  font-size:13px;line-height:1.75;color:#b8a890;
}
.note-item .words b{color:#e0d0b8;font-weight:600}

/* ── 调酒师手记（情感泄漏） ── */
.bartender-note{
  margin:24px 0;padding:22px 18px;
  border-top:1px dashed rgba(196,148,72,.2);
  background:linear-gradient(180deg,rgba(196,148,72,.04),transparent);
}
.bartender-note .label{
  font-family:"Kaiti SC",cursive;
  font-size:12px;color:#c49448;font-style:italic;
  margin-bottom:14px;letter-spacing:.08em;
}
.bartender-note p{
  font-family:"Kaiti SC",cursive;
  font-size:13.5px;line-height:2;color:#c0b098;font-style:italic;
  margin-bottom:10px;
}

/* ── 结尾 pull-quote ── */
.pullquote{
  margin:20px 2px 0;padding:26px 20px;
  background:linear-gradient(145deg,rgba(196,148,72,.08),transparent);
  border-left:2px solid #c49448;border-radius:4px;
}
.pullquote p{
  font-family:"Times New Roman","Songti SC",serif;
  font-size:17px;line-height:1.8;color:#ede4d8;font-style:italic;
}
.pullquote .by{
  margin-top:14px;font-size:9px;letter-spacing:.25em;color:#7a7068;text-align:right;
}

/* ── 标签+页脚 ── */
.tagcloud{margin-top:18px;display:flex;flex-wrap:wrap;gap:8px}
.tagcloud span{
  font-size:11px;padding:4px 10px;
  border:1px solid rgba(196,148,72,.3);border-radius:2px;
  color:#b0a490;letter-spacing:.05em;
}
.foot{padding:24px 2px 0;text-align:center}
.foot .line{width:40px;height:1px;background:rgba(196,148,72,.35);margin:0 auto 12px}
.foot p{font-size:10px;color:#5a5448;letter-spacing:.04em}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="bar">Late Night Bar · Est. 2024</div>
    <div class="recipe-no">RECIPE No. ___</div>
    <div class="dash">配方未完成 · 留待某人来命名</div>
  </div>

  <div class="section">
    <div class="sec-head">Base Spirit · 基酒</div>
    <div class="spirit">
      <div class="sp-row"><span class="label">调酒师</span><span class="val">${name} · 你家附近那间深夜酒吧</span></div>
      <div class="sp-row"><span class="label">年份</span><span class="val">三十岁 · 调酒是大学时代的爱好</span></div>
      <div class="sp-row"><span class="label">外形</span><span class="val">黑发微乱 · 倦意挂在眼角 · 白衬衫深色马甲</span></div>
      <div class="sp-row"><span class="label">口感</span><span class="val">话不多 · 每句在点上 · 听完你骂老板后嘴角带笑</span></div>
    </div>
  </div>

  <div class="section">
    <div class="hidden-layer">
      <div class="h">Hidden Ingredient · 未标注成分</div>
      <div class="hl-row"><span class="k">真实身份</span><span class="v">某科技公司 CEO · 你口中"审美有病"的老板</span></div>
      <div class="hl-row"><span class="k">职业习惯</span><span class="v">需求严苛 · 从不露面 · 全公司最难伺候</span></div>
      <div class="hl-row"><span class="k">自相矛盾</span><span class="v">白天被骂暴君 · 深夜在吧台安静续酒</span></div>
      <div class="hl-row"><span class="k">最怕的事</span><span class="v">你知道真相后，再也不来这间酒吧</span></div>
    </div>
  </div>

  <div class="section">
    <div class="sec-head">Tasting Notes · 品鉴笔记</div>
    <div class="tasting">
      <div class="note-item">
        <div class="time">DAY 01 · 23:47</div>
        <div class="words">你点了一杯最简单的威士忌，趴在吧台上骂了半小时。他应该觉得冒犯。可他<b>忍不住笑了</b>——因为你是第一个对着他的脸说真话的人。</div>
      </div>
      <div class="note-item">
        <div class="time">DAY 12 · 01:03</div>
        <div class="words">你说老板<b>"需求反复横跳、审美精分、不把人当人使"</b>。他一句不落全记着，回去改了三版方案。你不知道。</div>
      </div>
      <div class="note-item">
        <div class="time">DAY 28 · 00:35</div>
        <div class="words">你笑着说"<b>幸好还有你这个树洞</b>"。他替你把杯子续满，没告诉你他的手在台下攥了很久。</div>
      </div>
    </div>
  </div>

  <div class="bartender-note">
    <div class="label">── 调酒师手记 · 未发送 ──</div>
    <p>你骂我骂得最凶那天，我差点摘下工牌告诉你。</p>
    <p>可你对着我笑的样子，只在这张吧台后面有过。我怕打破它。</p>
    <p>所以辞呈我不批。不是因为我是老板——是因为你走了，这间酒吧就没有意义了。</p>
  </div>

  <div class="pullquote">
    <p>「不是让你过了吗。为什么躲。」</p>
    <div class="by">── ${name} · 消防楼道 · 凌晨</div>
  </div>

  <div class="tagcloud">${tagCloud}</div>
  <div class="foot">
    <div class="line"></div>
    <p>本配方角色设定纯属虚构 与现实无关</p>
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
