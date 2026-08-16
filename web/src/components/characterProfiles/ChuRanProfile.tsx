import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface ChuRanProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 楚燃专属详情页 —— 赛道遥测 / RACE TELEMETRY
 * 天才赛车手把"以事业为重"输给了一封分手信，追妻火葬场。
 * 视觉语言：碳黑 + 赛车猩红 + 银紫，仪表盘/进站记录/维修板格式，
 * 一格"公开恋情"始终 PIT（进站未出），末尾停在机场那句失控的占有。
 */
export function ChuRanProfile({ profile }: ChuRanProfileProps) {
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

  const name = profile.display_name || '楚燃'
  const tags = profile.tags?.length ? profile.tags : ['全性向', '限左', '赛车手', '占有欲']
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
    radial-gradient(ellipse 88% 36% at 50% 0%,rgba(228,56,64,.16),transparent 56%),
    #0a0a0c;
  color:#c8c2c8;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}
.mono{font-family:"SF Mono","Menlo",monospace}

/* ── 抬头（起跑灯） ── */
.header{
  padding:24px 0 18px;border-bottom:2px solid rgba(228,56,64,.35);text-align:center;
}
.header .lights{display:flex;gap:6px;justify-content:center;margin-bottom:12px}
.header .lights i{
  width:10px;height:10px;border-radius:50%;
  background:radial-gradient(circle at 35% 30%,#ff5a60,#c0202a);
  box-shadow:0 0 8px rgba(228,56,64,.6);
}
.header .title{
  font-family:"Arial Black","Impact",sans-serif;
  font-size:28px;font-weight:900;color:#ece6ea;
  letter-spacing:.06em;margin-bottom:6px;
  text-shadow:0 0 20px rgba(228,56,64,.35);
}
.header .sub{font-size:11px;color:#8a7a86;letter-spacing:.2em;text-transform:uppercase}

/* ── section 通用 ── */
.section{padding:22px 0}
.section+.section{border-top:1px solid rgba(228,56,64,.12)}
.sec-head{
  font-size:9px;letter-spacing:.34em;color:#e4485a;
  text-transform:uppercase;margin-bottom:14px;font-weight:700;
}

/* ── 遥测面板 ── */
.telemetry{
  padding:16px;border-radius:6px;
  background:linear-gradient(135deg,rgba(24,14,16,.95),rgba(14,10,11,.95));
  border:1px solid rgba(228,56,64,.24);position:relative;overflow:hidden;
}
.telemetry::before{
  content:"CAR NO.03";position:absolute;top:10px;right:12px;
  font-family:"SF Mono",monospace;font-size:8px;letter-spacing:.12em;
  color:rgba(228,56,64,.4);font-weight:700;
}
.telemetry .row{display:flex;padding:7px 0;font-size:13px;border-bottom:1px dotted rgba(228,56,64,.16)}
.telemetry .row:last-child{border-bottom:none}
.telemetry .k{color:#9a7a80;min-width:72px;letter-spacing:.04em;font-size:11px}
.telemetry .v{color:#d4c4c8;flex:1}
.telemetry .v b{color:#e4485a;font-weight:600}

/* ── 进站记录 ── */
.laps{margin-top:4px}
.lap{
  display:flex;align-items:baseline;gap:12px;
  padding:11px 0;border-bottom:1px solid rgba(228,56,64,.1);
}
.lap .no{font-family:"SF Mono","Menlo",monospace;font-size:12px;color:#8a5a5e;min-width:44px}
.lap .body{flex:1}
.lap .body .t{font-size:14px;color:#dccacc;font-weight:600}
.lap .body .d{font-size:11px;color:#9a7a80;margin-top:2px;line-height:1.5}
.lap.dnf{
  background:linear-gradient(90deg,rgba(228,56,64,.12),transparent);
  border-radius:4px;padding:14px 12px;border-bottom:none;margin-top:6px;
  border:1px dashed rgba(228,56,64,.45);
}
.lap.dnf .no{color:#e4485a}
.lap.dnf .body .t{color:#ff5a60}
.lap.dnf .badge{
  font-size:9px;letter-spacing:.1em;color:#ff5a60;
  border:1px solid rgba(228,56,64,.55);border-radius:3px;padding:2px 6px;
  margin-left:8px;vertical-align:middle;
}

/* ── 无线电（车队通讯） ── */
.radio{margin-top:6px;display:flex;flex-direction:column;gap:8px}
.radio .line{
  font-size:12px;color:#b09a9e;padding:9px 12px;
  background:rgba(228,56,64,.05);border-radius:6px;
  border-left:2px solid rgba(228,56,64,.35);
}
.radio .line .who{
  font-family:"SF Mono",monospace;font-size:9px;letter-spacing:.1em;
  color:#8a5a5e;display:block;margin-bottom:3px;text-transform:uppercase;
}
.radio .line b{color:#e4989c;font-weight:600}

/* ── 手记（撕碎的分手信） ── */
.note{
  margin:24px 0;padding:20px 18px;
  border-top:1px dashed rgba(228,56,64,.24);
  background:linear-gradient(180deg,rgba(228,56,64,.05),transparent);
}
.note .label{
  font-family:"Kaiti SC",cursive;font-size:12px;color:#e4485a;
  font-style:italic;margin-bottom:12px;letter-spacing:.06em;
}
.note p{
  font-family:"Kaiti SC",cursive;font-size:13.5px;line-height:2;
  color:#c4a8ac;font-style:italic;margin-bottom:9px;
}

/* ── 结尾 pull-quote ── */
.pullquote{
  margin:22px 2px 0;padding:26px 20px;
  background:linear-gradient(145deg,rgba(228,56,64,.14),transparent);
  border-left:2px solid #e4485a;border-radius:4px;
}
.pullquote p{
  font-family:"Times New Roman","Songti SC",serif;
  font-size:17px;line-height:1.85;color:#f0e4e6;font-style:italic;
}
.pullquote .by{
  margin-top:14px;font-size:9px;letter-spacing:.22em;color:#9a6a70;text-align:right;
}

/* ── 标签+页脚 ── */
.tagcloud{margin-top:18px;display:flex;flex-wrap:wrap;gap:8px}
.tagcloud span{
  font-size:11px;padding:4px 10px;
  border:1px solid rgba(228,56,64,.3);border-radius:2px;
  color:#b08a8e;letter-spacing:.05em;
}
.foot{padding:24px 2px 0;text-align:center}
.foot .line{width:40px;height:1px;background:rgba(228,56,64,.35);margin:0 auto 12px}
.foot p{font-size:10px;color:#6a5256;letter-spacing:.04em}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="lights"><i></i><i></i><i></i><i></i><i></i></div>
    <div class="title">${name}</div>
    <div class="sub">Race Telemetry · 藏了你三年</div>
  </div>

  <div class="section">
    <div class="sec-head">Driver Data · 车手数据</div>
    <div class="telemetry">
      <div class="row"><span class="k">车手</span><span class="v">${name} · 纵横赛场的天才车手</span></div>
      <div class="row"><span class="k">同行者</span><span class="v">你 · 地下恋爱三年的秘密恋人</span></div>
      <div class="row"><span class="k">造型</span><span class="v">银紫短发 · 赤红瞳 · 红黑赛服</span></div>
      <div class="row"><span class="k">恋情状态</span><span class="v"><b>PIT · 进站未出（拒绝公开 3 年）</b></span></div>
    </div>
  </div>

  <div class="section">
    <div class="sec-head">Pit Log · 进站记录</div>
    <div class="laps">
      <div class="lap"><span class="no">LAP 1</span><span class="body"><span class="t">雨夜维修区</span><span class="d">三年前你们相遇 · 一段谁都不知道的地下恋情</span></span></div>
      <div class="lap"><span class="no">LAP 2</span><span class="body"><span class="t">短暂又热烈的每一次见面</span><span class="d">他深夜赶来 · 天没亮又要离开</span></span></div>
      <div class="lap"><span class="no">LAP 3</span><span class="body"><span class="t">"以事业为重"</span><span class="d">每次提公开都被婉拒 · 你被藏在镜头照不到的角落</span></span></div>
      <div class="lap dnf"><span class="no">FINAL</span><span class="body"><span class="t">机场 · 那封分手信<span class="badge">DNF · 他疾驰而来</span></span><span class="d">这次再被拒绝你就走 · 收到信的他第一次尝到失控的怕</span></span></div>
    </div>
  </div>

  <div class="section">
    <div class="sec-head">Team Radio · 车队无线电</div>
    <div class="radio">
      <div class="line"><span class="who">— 机场 · 他 —</span>你要去哪？<b>分手信？我这辈子还没输过，你以为我会让你走？</b></div>
      <div class="line"><span class="who">— 酒店 · 他 —</span>是我不好，藏了你三年。<b>但从今天起——</b></div>
      <div class="line"><span class="who">— 气息灼在耳侧 —</span>你这辈子<b>只能是我的。哪儿都不许去。</b></div>
    </div>
  </div>

  <div class="note">
    <div class="label">── 输掉比赛不可怕 · 手记 ──</div>
    <p>我信奉一句话：分心的车手活不到终点。所以我把你藏起来，理所当然地以为你会一直等。</p>
    <p>我没算到你会累。收到那封信的一刻，我才知道有些东西比输掉比赛可怕得多。</p>
    <p>我不会说漂亮的挽回话。我只会用最霸道的方式把你锁在身边，然后在夜里用力得发抖地抱着你。</p>
  </div>

  <div class="pullquote">
    <p>「藏了你三年是我错。<br>可这封分手信——你休想签成。<br>你这辈子只能是我的，哪儿都不许去。」</p>
    <div class="by">── ${name} · 机场到酒店</div>
  </div>

  <div class="tagcloud">${tagCloud}</div>
  <div class="foot">
    <div class="line"></div>
    <p>本设定纯属虚构 与现实无关</p>
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
