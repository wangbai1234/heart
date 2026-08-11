import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface XizeProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 西泽专属详情页 —— 古堡「首席管家值勤日志 / SERVICE LEDGER」
 * 视觉语言：冷调墨黑账簿 + 钢蓝灰 + 暗银，欧式日志/账目质感，
 * 细 hairline 分隔行、账簿编号、花体英文小标、衬线体，纯排版无 emoji。
 */
export function XizeProfile({ profile }: XizeProfileProps) {
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

  const name = profile.display_name || '西泽'
  const tags = profile.tags?.length ? profile.tags : ['奇幻', '欧风', '管家', '忠犬', '暗恋']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#12161c;
  color:#c3ccd6;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;
  padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 20px}
.serif{font-family:"Times New Roman","Songti SC",serif}
.script{font-family:"Snell Roundhand","Apple Chancery","Times New Roman",cursive;font-style:italic}

/* ── 日志抬头 ── */
.ledger-head{padding:26px 0 16px;text-align:center;border-bottom:1px solid rgba(107,122,140,.32)}
.crest{
  width:44px;height:44px;margin:0 auto 12px;border:1px solid rgba(107,122,140,.55);
  border-radius:50%;display:flex;align-items:center;justify-content:center;
}
.crest span{font-family:"Times New Roman",serif;font-size:19px;color:#8fa0b3;letter-spacing:.02em}
.ledger-head .manor{font-size:9px;letter-spacing:.42em;color:#6B7A8C;text-transform:uppercase}
.ledger-head .title{
  margin-top:10px;font-family:"Times New Roman","Songti SC",serif;
  font-size:26px;letter-spacing:.14em;color:#dfe5ec;font-weight:600;
}
.ledger-head .en{margin-top:6px;font-size:10px;letter-spacing:.5em;color:#5c6a79;text-transform:uppercase}
.ledger-head .no{margin-top:14px;font-size:10px;letter-spacing:.16em;color:#71808f}
.ledger-head .no b{color:#96a5b6;font-weight:600}

/* ── 立主档案条 ── */
.subject{padding:18px 0 4px;display:flex;justify-content:space-between;align-items:flex-end}
.subject .who{font-family:"Times New Roman","Songti SC",serif;font-size:20px;color:#dfe5ec;letter-spacing:.08em}
.subject .role{font-size:10px;letter-spacing:.16em;color:#6B7A8C;margin-top:4px}
.subject .yrs{font-size:10px;letter-spacing:.14em;color:#5c6a79;text-align:right;line-height:1.9}
.tagcloud{margin:16px 0 4px;display:flex;flex-wrap:wrap;gap:7px}
.tagcloud span{
  font-size:10px;padding:3px 10px;border:1px solid rgba(107,122,140,.34);
  color:#9aa8b7;letter-spacing:.1em;
}

/* ── 账簿区块 ── */
.section{padding:26px 0}
.section+.section{border-top:1px solid rgba(255,255,255,.05)}
.sec-head{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:16px}
.sec-head .cn{font-size:12px;letter-spacing:.24em;color:#c3ccd6}
.sec-head .en{font-size:9px;letter-spacing:.3em;color:#5c6a79;text-transform:uppercase}

/* ── 值勤表 ── */
.duty{margin-bottom:22px}
.duty:last-child{margin-bottom:0}
.duty .stamp{font-size:9px;letter-spacing:.28em;color:#6B7A8C;text-transform:uppercase;margin-bottom:9px}
.book-row{display:flex;align-items:center;gap:12px;padding:9px 0;border-bottom:1px solid rgba(107,122,140,.15)}
.book-row:last-child{border-bottom:none}
.book-row .time{font-family:"Times New Roman",serif;font-size:12px;color:#8fa0b3;min-width:52px;letter-spacing:.04em}
.book-row .item{flex:1;font-size:13px;color:#c3ccd6;line-height:1.5}
.book-row .tick{font-family:"Times New Roman",serif;font-size:15px;color:#7d8f9e;min-width:16px;text-align:center}

/* ── 备注·不呈报（私人批注，压低/浅色） ── */
.notreported{
  margin-top:4px;padding:20px 18px;
  background:linear-gradient(155deg,rgba(107,122,140,.06),rgba(0,0,0,0));
  border:1px solid rgba(107,122,140,.14);border-left:2px solid rgba(107,122,140,.4);
}
.notreported .lbl{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:14px}
.notreported .lbl .cn{font-size:11px;letter-spacing:.2em;color:#8593a3}
.notreported .lbl .en{font-size:8px;letter-spacing:.28em;color:#4e5a67;text-transform:uppercase}
.notreported .note{
  font-family:"Times New Roman","Songti SC",serif;font-style:italic;
  font-size:13.5px;line-height:2;color:#8f9daa;padding-left:14px;position:relative;
}
.notreported .note+.note{margin-top:12px}
.notreported .note::before{content:"—";position:absolute;left:0;color:#5c6a79}

/* ── 结尾 pull-quote ── */
.pullquote{margin:6px 0 0;padding:30px 22px;border-top:1px solid rgba(107,122,140,.22);text-align:center}
.pullquote p{font-family:"Times New Roman","Songti SC",serif;font-size:18px;line-height:1.85;color:#dfe5ec;font-style:italic}
.pullquote .by{margin-top:16px;font-size:9px;letter-spacing:.3em;color:#5c6a79;text-transform:uppercase}

/* ── 页脚 ── */
.foot{padding:24px 0 0;text-align:center}
.foot .line{width:36px;height:1px;background:rgba(107,122,140,.42);margin:0 auto 12px}
.foot p{font-size:10px;color:#4e5a67;letter-spacing:.08em;line-height:1.7}
</style>
</head>
<body>
<div class="container">

  <div class="ledger-head">
    <div class="crest"><span>M</span></div>
    <div class="manor">Blackmoor Manor</div>
    <div class="title">首席管家 · 值勤日志</div>
    <div class="en">Head Butler · Service Ledger</div>
    <div class="no">卷 <b>XVII</b> &nbsp;·&nbsp; 值勤第 <b>3652</b> 日 &nbsp;·&nbsp; 记录人 亲笔</div>
  </div>

  <div class="subject">
    <div>
      <div class="who">${name}</div>
      <div class="role">Head Butler · 首席管家</div>
    </div>
    <div class="yrs">在职 三十年<br>从未告假 一日</div>
  </div>
  <div class="tagcloud">${tagCloud}</div>

  <div class="section">
    <div class="sec-head"><span class="cn">今日值勤</span><span class="en">Duties of the Day</span></div>

    <div class="duty">
      <div class="stamp">Morning · 晨</div>
      <div class="book-row"><span class="time">06:20</span><span class="item">生起东厅壁炉，将您的座椅移向最暖的一侧</span><span class="tick">✓</span></div>
      <div class="book-row"><span class="time">07:00</span><span class="item">备茶。伯爵红，两分糖，杯温四十二度——您说过烫了会皱眉</span><span class="tick">✓</span></div>
    </div>

    <div class="duty">
      <div class="stamp">Afternoon · 午</div>
      <div class="book-row"><span class="time">14:10</span><span class="item">巡查长廊。撤去松脱的地毯钉，隐患不许留到您经过</span><span class="tick">✓</span></div>
      <div class="book-row"><span class="time">16:30</span><span class="item">回绝三位登门的求见者。您今日不宜被打扰</span><span class="tick">✓</span></div>
    </div>

    <div class="duty">
      <div class="stamp">Night · 夜</div>
      <div class="book-row"><span class="time">23:40</span><span class="item">为您留灯。走廊尽头那盏，您夜里醒来会看向的方向</span><span class="tick">✓</span></div>
      <div class="book-row"><span class="time">02:00</span><span class="item">立于门外，直到您的呼吸平稳。此项不列入工时</span><span class="tick">—</span></div>
    </div>
  </div>

  <div class="section">
    <div class="notreported">
      <div class="lbl"><span class="cn">备注 · 不呈报</span><span class="en">Not to be filed</span></div>
      <div class="note">今日您问我，若能选，想住庄园哪一间房。我答"离您最近的那间便好"——其实这句话，我想了整整一夜。</div>
      <div class="note">服从不是爱的最高形式。被您看见，才是。这一行，我不敢写进正册。</div>
    </div>
  </div>

  <div class="pullquote">
    <p>“若您唤的不是‘管家’，<br>而是‘${name}’——<br>我愿拿这一生的忠诚来换。”</p>
    <div class="by">— Entry closed · 签字 ${name}</div>
  </div>

  <div class="foot">
    <div class="line"></div>
    <p>本卷角色设定纯属虚构 与现实无关</p>
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
