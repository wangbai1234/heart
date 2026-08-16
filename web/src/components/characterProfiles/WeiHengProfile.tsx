import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface WeiHengProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 卫珩专属详情页 —— 出警记录 / CASE FILE
 * 冷面女警官=你从小暗恋的邻家姐姐，嘴上骂你不省心先伸手的却是她。
 * 视觉语言：冷钢蓝+警徽金，案件卷宗/保释担保书格式，
 * 官方冷硬表格里「备注栏」泄漏私心，等宽字体+印章质感。
 */
export function WeiHengProfile({ profile }: WeiHengProfileProps) {
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

  const name = profile.display_name || '卫珩'
  const tags = profile.tags?.length ? profile.tags : ['女性向', 'GL', '警察', '年上']
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
    radial-gradient(ellipse 100% 45% at 50% 0%,rgba(74,102,140,.10),transparent 58%),
    #0e1319;
  color:#c4d0dc;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}
.mono{font-family:"SF Mono","Menlo",monospace}

/* ── 卷宗抬头 ── */
.header{
  padding:22px 0 16px;border-bottom:2px solid rgba(122,158,196,.3);
  position:relative;
}
.header .bar{
  font-size:10px;letter-spacing:.4em;color:#6e8296;
  text-transform:uppercase;margin-bottom:6px;
}
.header .case-no{
  font-family:"SF Mono","Menlo",monospace;
  font-size:22px;font-weight:700;color:#8fb4d8;
  letter-spacing:.08em;margin-bottom:4px;
}
.header .stamp{
  position:absolute;top:20px;right:0;
  font-size:10px;letter-spacing:.18em;color:rgba(200,90,90,.7);
  border:1.5px solid rgba(200,90,90,.5);border-radius:3px;
  padding:4px 8px;transform:rotate(-8deg);font-weight:700;
}
.header .dash{font-size:12px;color:#5e7080;letter-spacing:.06em}

/* ── section 通用 ── */
.section{padding:22px 0}
.section+.section{border-top:1px solid rgba(122,158,196,.12)}
.sec-head{
  font-size:9px;letter-spacing:.34em;color:#7a9ec4;
  text-transform:uppercase;margin-bottom:14px;font-weight:700;
}

/* ── 官方表格 ── */
.form-row{
  display:flex;padding:9px 12px;font-size:13px;
  border-left:2px solid rgba(122,158,196,.3);
  background:rgba(122,158,196,.04);margin-bottom:6px;border-radius:0 4px 4px 0;
}
.form-row .k{color:#6e8296;min-width:78px;letter-spacing:.05em}
.form-row .v{color:#c4d0dc;flex:1}

/* ── 现场记录 ── */
.log{margin-top:6px}
.log-item{
  padding:12px 14px;margin-bottom:8px;border-radius:4px;
  background:rgba(122,158,196,.05);
  border-left:2px solid rgba(122,158,196,.28);
}
.log-item .time{
  font-family:"SF Mono","Menlo",monospace;
  font-size:11px;color:#6e8296;margin-bottom:5px;letter-spacing:.04em;
}
.log-item .words{font-size:13px;line-height:1.7;color:#aab8c6}
.log-item .words b{color:#d0dce8;font-weight:600}

/* ── 保释担保书 ── */
.bail{
  margin-top:8px;padding:20px 18px;border-radius:4px;
  background:rgba(20,26,34,.7);
  border:1px solid rgba(122,158,196,.24);position:relative;overflow:hidden;
}
.bail::before{
  content:"APPROVED";position:absolute;bottom:10px;right:12px;
  font-size:9px;letter-spacing:.16em;color:rgba(122,158,196,.28);
  border:1px solid rgba(122,158,196,.2);padding:3px 7px;transform:rotate(-6deg);
}
.bail .h{
  font-size:10px;letter-spacing:.28em;color:#8fb4d8;
  text-transform:uppercase;margin-bottom:14px;font-weight:700;
}
.bail .br{display:flex;padding:7px 0;border-bottom:1px solid rgba(122,158,196,.1);font-size:13px}
.bail .br:last-child{border-bottom:none}
.bail .br .k{min-width:76px;color:#6e8296;letter-spacing:.04em}
.bail .br .v{color:#bcc8d4;flex:1}

/* ── 备注栏（私心泄漏，手写） ── */
.remark{
  margin:24px 0;padding:20px 18px;
  border-top:1px dashed rgba(122,158,196,.24);
  background:linear-gradient(180deg,rgba(122,158,196,.05),transparent);
}
.remark .label{
  font-family:"Kaiti SC",cursive;font-size:12px;color:#8fb4d8;
  font-style:italic;margin-bottom:12px;letter-spacing:.06em;
}
.remark p{
  font-family:"Kaiti SC",cursive;font-size:13.5px;line-height:2;
  color:#a8bccf;font-style:italic;margin-bottom:9px;
}

/* ── 结尾 pull-quote ── */
.pullquote{
  margin:22px 2px 0;padding:26px 20px;
  background:linear-gradient(145deg,rgba(122,158,196,.10),transparent);
  border-left:2px solid #7a9ec4;border-radius:4px;
}
.pullquote p{
  font-family:"Songti SC","STSong",serif;
  font-size:17px;line-height:1.85;color:#dce6f0;font-style:italic;
}
.pullquote .by{
  margin-top:14px;font-size:9px;letter-spacing:.22em;color:#6e8296;text-align:right;
}

/* ── 标签+页脚 ── */
.tagcloud{margin-top:18px;display:flex;flex-wrap:wrap;gap:8px}
.tagcloud span{
  font-size:11px;padding:4px 10px;
  border:1px solid rgba(122,158,196,.3);border-radius:2px;
  color:#9ab0c4;letter-spacing:.05em;
}
.foot{padding:24px 2px 0;text-align:center}
.foot .line{width:40px;height:1px;background:rgba(122,158,196,.35);margin:0 auto 12px}
.foot p{font-size:10px;color:#546070;letter-spacing:.04em}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="bar">Municipal Police · Duty Record</div>
    <div class="case-no">CASE No. ____</div>
    <div class="stamp">已保释</div>
    <div class="dash">处理警官 · 与当事人系旧邻</div>
  </div>

  <div class="section">
    <div class="sec-head">Officer · 处理警官</div>
    <div class="form-row"><span class="k">姓名</span><span class="v">${name} · 二十七岁</span></div>
    <div class="form-row"><span class="k">警衔</span><span class="v">市局警官 · 警校毕业后忙到脚不沾地</span></div>
    <div class="form-row"><span class="k">外形</span><span class="v">墨蓝长发 · 眼下泪痣 · 唇边银钉</span></div>
    <div class="form-row"><span class="k">作风</span><span class="v">话少 · 冷面 · 用"训你"表达关心</span></div>
    <div class="form-row"><span class="k">与当事人关系</span><span class="v">住隔壁十几年 · 看你长大的"姐姐"</span></div>
  </div>

  <div class="section">
    <div class="sec-head">Field Log · 出警记录</div>
    <div class="log">
      <div class="log-item">
        <div class="time">CALL 01 · 童年</div>
        <div class="words">你摔破膝盖，是她<b>背你回家</b>；你逃学，是她拎你去上课；你做噩梦，第一个想到的是隔壁那扇灯。</div>
      </div>
      <div class="log-item">
        <div class="time">CALL 02 · 近一年</div>
        <div class="words">你成了这条街的不良少女。一半是天性，一半——是想<b>让她多看你两眼</b>。</div>
      </div>
      <div class="log-item">
        <div class="time">CALL 03 · 今日</div>
        <div class="words">替人出头动了手，进了局子。来处理的偏偏是她。她看着你脸上的伤，冷着脸，<b>抬你下巴的手却轻得不像话</b>。</div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="bail">
      <div class="h">Bail Guarantee · 保释担保书</div>
      <div class="br"><span class="k">担保人</span><span class="v">${name}（本人签字）</span></div>
      <div class="br"><span class="k">担保理由</span><span class="v">当事人系旧邻 · 品行本无大恶</span></div>
      <div class="br"><span class="k">附加条件</span><span class="v">"以后都改" · 警局之外常来见我</span></div>
      <div class="br"><span class="k">备注</span><span class="v">此项未写进正式记录</span></div>
    </div>
  </div>

  <div class="remark">
    <div class="label">── 备注栏 · 只有我自己看得到 ──</div>
    <p>我知道你为什么变"坏"。也知道我每次都心软地纵容。</p>
    <p>作为警察，我该守着分寸。可作为看你长大的人——我做不到真对你冷下心。</p>
    <p>你在警局门口拉住我的手时，我拼命守的那条线，其实早被你踩碎了。</p>
  </div>

  <div class="pullquote">
    <p>「这是怎么了，小鬼。<br>……保释我签了，走吧。」</p>
    <div class="by">── ${name} · 拘留室门口</div>
  </div>

  <div class="tagcloud">${tagCloud}</div>
  <div class="foot">
    <div class="line"></div>
    <p>本卷宗角色设定纯属虚构 与现实无关</p>
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
