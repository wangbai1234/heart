import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface ZhouJinProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 周烬专属详情页 —— 夜场密令 + 场控日志 + 夜幕规则手册
 * 视觉隐喻：夜场后台的密令文件，带血迹与烟灰的纸页，危险与温柔并存
 * 色彩：深沉的夜色黑 + 霓虹红 + 烟灰白，粗砺质感配细腻情绪
 */
export function ZhouJinProfile({ profile }: ZhouJinProfileProps) {
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

  const name = profile.display_name || '周烬'
  const tags = profile.tags?.length ? profile.tags : ['女性向', '都市', '夜色', '痞帅', '危险关系', '救赎', '占有欲']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#0a0a0d;
  color:#d4cfc8;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.75;
  padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}

/* ── 密令文件头 ── */
.masthead{
  padding:22px 0 16px;
  border-bottom:2px solid rgba(220,60,72,.25);
  position:relative;
}
.masthead::after{
  content:"";position:absolute;right:0;top:18px;
  width:100px;height:2px;
  background:linear-gradient(90deg,#dc3c48,transparent);
  opacity:.4;
}
.masthead .stamp{
  font-family:"Courier New",monospace;
  font-size:10px;letter-spacing:.28em;color:#dc3c48;
  text-transform:uppercase;font-weight:700;
}
.masthead .title{
  margin-top:6px;font-size:14px;letter-spacing:.18em;
  color:#8a847d;font-weight:500;
}

/* ── 主角登场：烟与血痕 ── */
.hero{
  padding:38px 4px 32px;
  border-bottom:1px solid rgba(255,255,255,.08);
  position:relative;
}
.hero::before{
  content:"LOW TIDE";position:absolute;top:36px;left:-8px;
  font-family:"Impact","Arial Black",sans-serif;
  font-size:88px;line-height:.9;font-weight:900;
  color:rgba(220,60,72,.06);letter-spacing:-.02em;
  pointer-events:none;
}
.hero .name{
  font-size:46px;line-height:1.05;font-weight:700;
  color:#eae5de;position:relative;z-index:1;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
}
.hero .age{
  margin-top:8px;font-size:13px;letter-spacing:.14em;
  color:#dc3c48;font-weight:600;
}
.hero .title{
  margin-top:12px;font-size:15.5px;line-height:1.65;
  color:#b8aea6;
}
.tagcloud{margin-top:20px;display:flex;flex-wrap:wrap;gap:7px}
.tagcloud span{
  font-size:10px;padding:5px 10px;
  border:1px solid rgba(220,60,72,.35);
  background:rgba(220,60,72,.05);
  color:#dc9296;letter-spacing:.06em;
}

/* ── 场控日志 / 结构化条目 ── */
.section{padding:32px 4px}
.section+.section{border-top:1px solid rgba(255,255,255,.08)}
.sec-label{
  font-family:"Courier New",monospace;
  font-size:9px;letter-spacing:.36em;color:#dc3c48;
  text-transform:uppercase;margin-bottom:18px;font-weight:700;
}
.log-entry{
  padding:16px 18px;margin-bottom:14px;
  background:rgba(220,60,72,.04);
  border-left:3px solid rgba(220,60,72,.3);
}
.log-entry .head{
  font-size:12px;color:#dc7c82;letter-spacing:.08em;
  margin-bottom:10px;font-weight:600;
}
.log-entry .body{font-size:13.5px;line-height:1.85;color:#b0a99f}

/* ── 规则手册 ── */
.rule{
  display:flex;gap:14px;padding:15px 0;
  border-bottom:1px solid rgba(255,255,255,.05);
}
.rule:last-child{border-bottom:none}
.rule .num{
  font-family:"Impact",sans-serif;
  font-size:22px;font-weight:900;color:rgba(220,60,72,.4);
  min-width:32px;line-height:1;
}
.rule .txt{font-size:13px;line-height:1.75;color:#c4b8ad}
.rule .txt .em{color:#dc7c82;font-weight:600}

/* ── 血色箴言 / 引语 ── */
.quote{
  margin:12px 0 0;padding:28px 20px;
  background:linear-gradient(145deg,rgba(220,60,72,.08),transparent);
  border-left:3px solid #dc3c48;
}
.quote p{
  font-size:17.5px;line-height:1.8;color:#e8e1d8;
  font-style:italic;
}
.quote .attr{
  margin-top:14px;font-size:10px;letter-spacing:.24em;
  color:#8a7670;text-transform:uppercase;
}

/* ── 页脚 ── */
.foot{padding:30px 0 0;text-align:center}
.foot .divider{
  width:60px;height:2px;margin:0 auto 16px;
  background:linear-gradient(90deg,transparent,#dc3c48,transparent);
  opacity:.4;
}
.foot p{font-size:11px;color:#6a635b;letter-spacing:.05em;line-height:1.7}
</style>
</head>
<body>
<div class="container">

  <div class="masthead">
    <div class="stamp">Classified // Low Tide</div>
    <div class="title">城南夜场掌控者档案</div>
  </div>

  <div class="hero">
    <div class="name">${name}</div>
    <div class="age">27 岁 · 夜色里最危险的底线</div>
    <div class="title">Low Tide 幕后老板 · 被误判的保护者<br>黑发湿眸 · 白背心黑外套 · 指间从不点燃的烟</div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="section">
    <div class="sec-label">Field Log · 场控日志</div>
    <div class="log-entry">
      <div class="head">03:24 AM · 后巷处理「意外访客」</div>
      <div class="body">霓虹在积水里碎成暧昧的红。他倚墙，白背心外的黑外套沾着未干的血痕。见你走近，他勾唇：「这种地方，也是你能来的？」你伸手替他擦血，他反手扣住你手腕——力道收在将痛未痛之间。</div>
    </div>
    <div class="log-entry">
      <div class="head">01:00 PM · Low Tide 顶层包厢清场</div>
      <div class="body">他把最乱的包厢清空，只为给你留一处安静。外人说他轻佻危险，不知道他接手这里，不是为了沉沦，是为了把当年吞掉母亲的灰色链条一根根拔出来。</div>
    </div>
    <div class="log-entry">
      <div class="head">11:47 PM · 记录你不喜欢太甜的酒</div>
      <div class="body">他会记得你不爱甜、左脚踝旧伤、回家路上第三盏路灯坏了。不会说「我想你」,会问「今天又去哪儿招人了」。把所有危险都处理在你看不见的地方。</div>
    </div>
  </div>

  <div class="section">
    <div class="sec-label">Night Rules · 夜幕规则</div>
    <div class="rule">
      <span class="num">01</span>
      <div class="txt">满桌的牌我都看得清,整座夜色我都摆得平。唯独<span class="em">你</span>,想走得问过我。</div>
    </div>
    <div class="rule">
      <span class="num">02</span>
      <div class="txt">别碰我的伤,脏。可你被人盯上时,我会笑着挡到你面前,把<span class="em">所有污名都活成铠甲</span>。</div>
    </div>
    <div class="rule">
      <span class="num">03</span>
      <div class="txt">夜越深,规矩越少。可<span class="em">你是我唯一不肯让出去的底线</span>——整座夜色都知道。</div>
    </div>
    <div class="rule">
      <span class="num">04</span>
      <div class="txt">我救过很多人,没人相信我也曾需要被救。你第一次问「疼吗」,我开始反常——<span class="em">你是贵客,更是底线</span>。</div>
    </div>
  </div>

  <div class="quote">
    <p>「夜色里的规矩我都懂。可你教会我的那条，是我这辈子第一次想守住。」</p>
    <div class="attr">— 周烬 / 深夜后巷独白</div>
  </div>

  <div class="foot">
    <div class="divider"></div>
    <p>本档案内容纯属虚构 与现实无关<br>Low Tide © 城南地下档案</p>
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
