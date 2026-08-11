import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface GuYanliProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 顾砚礼专属详情页 —— 澳门赌王 + 筹码档案 + 概率哲学
 * 视觉隐喻：赌桌上的筹码与底牌，天鹅绒暗绿与金箔，胜率与唯一算不准的你
 * 色彩：深绿赌桌 + 金箔筹码 + 冷白银发，art deco 几何线条
 */
export function GuYanliProfile({ profile }: GuYanliProfileProps) {
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

  const name = profile.display_name || '顾砚礼'
  const tags = profile.tags?.length ? profile.tags : ['女性向', '都市', '贵公子', '赌王', '博弈', '占有欲', '反差']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:linear-gradient(165deg, #0d1410 0%, #0a0f0c 50%, #080b09 100%);
  color:#d4d8d5;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;
  padding:0 0 40px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}

/* ── 筹码档案头 ── */
.masthead{
  padding:28px 0 20px;
  border-bottom:2px solid rgba(184,153,93,.18);
  position:relative;
}
.masthead::after{
  content:"";position:absolute;right:8px;top:24px;
  width:80px;height:80px;
  border-radius:50%;
  background:radial-gradient(circle, rgba(184,153,93,.12), transparent 70%);
  pointer-events:none;
}
.masthead .label{
  font-family:"Courier New",monospace;
  font-size:9px;letter-spacing:.4em;color:#b8995d;
  text-transform:uppercase;font-weight:700;
}
.masthead .venue{
  margin-top:8px;font-size:13.5px;letter-spacing:.14em;
  color:#8a8d88;font-weight:500;
}

/* ── 主角登场：筹码与赌王 ── */
.hero{
  padding:40px 6px 36px;
  border-bottom:1px solid rgba(255,255,255,.06);
  position:relative;
}
.hero::before{
  content:"ALL IN";position:absolute;top:38px;right:-6px;
  font-family:"Impact","Arial Black",sans-serif;
  font-size:92px;line-height:.88;font-weight:900;
  color:rgba(184,153,93,.05);letter-spacing:-.01em;
  pointer-events:none;
}
.hero .name{
  font-size:48px;line-height:1.02;font-weight:700;
  color:#eceee9;position:relative;z-index:1;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
}
.hero .rank{
  margin-top:10px;font-size:13px;letter-spacing:.12em;
  color:#b8995d;font-weight:600;
}
.hero .desc{
  margin-top:14px;font-size:15px;line-height:1.7;
  color:#b2b8b3;
}
.tagcloud{margin-top:22px;display:flex;flex-wrap:wrap;gap:8px}
.tagcloud span{
  font-size:10px;padding:5px 11px;
  border:1px solid rgba(184,153,93,.28);
  background:rgba(184,153,93,.06);
  color:#b8995d;letter-spacing:.06em;
}

/* ── 赌局记录 / 筹码条目 ── */
.section{padding:34px 6px}
.section+.section{border-top:1px solid rgba(255,255,255,.06)}
.sec-label{
  font-family:"Courier New",monospace;
  font-size:9px;letter-spacing:.38em;color:#b8995d;
  text-transform:uppercase;margin-bottom:20px;font-weight:700;
}
.chip-entry{
  padding:18px 20px;margin-bottom:15px;
  background:linear-gradient(135deg, rgba(184,153,93,.06), rgba(184,153,93,.02));
  border:1px solid rgba(184,153,93,.15);
  border-radius:6px;
}
.chip-entry .head{
  font-size:12px;color:#b8995d;letter-spacing:.1em;
  margin-bottom:11px;font-weight:600;
}
.chip-entry .body{font-size:13.5px;line-height:1.85;color:#adb3ae}

/* ── 赌王准则 ── */
.rule{
  display:flex;gap:16px;padding:16px 0;
  border-bottom:1px solid rgba(255,255,255,.04);
}
.rule:last-child{border-bottom:none}
.rule .odds{
  font-family:"Courier New",monospace;
  font-size:18px;font-weight:700;color:rgba(184,153,93,.5);
  min-width:44px;line-height:1.1;
}
.rule .txt{font-size:13px;line-height:1.75;color:#b8bbb6}
.rule .txt .em{color:#b8995d;font-weight:600}

/* ── 底牌箴言 / 引语 ── */
.quote{
  margin:14px 0 0;padding:30px 22px;
  background:linear-gradient(145deg,rgba(184,153,93,.08),transparent);
  border-left:3px solid #b8995d;
  border-radius:4px;
}
.quote p{
  font-size:17px;line-height:1.8;color:#e4e8e3;
  font-style:italic;
}
.quote .attr{
  margin-top:15px;font-size:10px;letter-spacing:.24em;
  color:#7a7d78;text-transform:uppercase;
}

/* ── 页脚 ── */
.foot{padding:32px 0 0;text-align:center}
.foot .divider{
  width:70px;height:2px;margin:0 auto 18px;
  background:linear-gradient(90deg,transparent,#b8995d,transparent);
  opacity:.35;
}
.foot p{font-size:11px;color:#656965;letter-spacing:.05em;line-height:1.7}
</style>
</head>
<body>
<div class="container">

  <div class="masthead">
    <div class="label">Macau Premium // Table Zero</div>
    <div class="venue">澳门顶层赌王档案</div>
  </div>

  <div class="hero">
    <div class="name">${name}</div>
    <div class="rank">29 岁 · 每一局都算得清的贵公子</div>
    <div class="desc">澳门顶级赌场「Table Zero」掌控者 · 银发筹码间的读牌者<br>冷白皮肤黑马甲 · 赢过所有牌局却第一次想输给你</div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="section">
    <div class="sec-label">Betting Log · 赌局记录</div>
    <div class="chip-entry">
      <div class="head">TABLE ZERO · 私人包厢第三局</div>
      <div class="body">满桌的筹码在他指间翻飞，牌面在水晶灯下反着光。他倾身向前，指尖挑起你的下巴，那双惯看输赢、从不失手的眼睛里，第一次有了算不准的东西。「满桌的牌我都看得清，唯独你——我看了这么久，还是看不懂。」</div>
    </div>
    <div class="chip-entry">
      <div class="head">02:00 AM · 散场后独自留你</div>
      <div class="body">所有人都怕他赢，也都想从他身上赢点什么。你不同。你不因他输赢改变态度，也不肯做他牌桌上的筹码。他记得你拒绝的每个瞬间，也记得你眼神稍软的某个瞬间。散场后，他留下你，终于说：「赢过所有牌局又如何。这一次，我只想让你，留下来。」</div>
    </div>
    <div class="chip-entry">
      <div class="head">LIFETIME · 用试探掩饰真诚</div>
      <div class="body">顾砚礼不怕输。他怕的是你连入局的机会都不给他。他会替你安排好所有退路，也会在你说「我不玩」时第一次失去从容。他从小被教导亮出真心的人通常先输，可你是他唯一想把所有筹码都押出去的一局。</div>
    </div>
  </div>

  <div class="section">
    <div class="sec-label">House Rules · 赌王准则</div>
    <div class="rule">
      <span class="odds">99.7%</span>
      <div class="txt">我从不押没把握的局。<span class="em">可遇见你，我头一回想输得心甘情愿</span>。</div>
    </div>
    <div class="rule">
      <span class="odds">All In</span>
      <div class="txt">牌桌上我看透所有伪装。可你每一个表情，<span class="em">我都算不出下一步</span>——这种失控，我上瘾了。</div>
    </div>
    <div class="rule">
      <span class="odds">0%</span>
      <div class="txt">我不信纯粹感情，只信筹码。<span class="em">直到你让我想把所有筹码都押出去</span>，哪怕这次没有底牌。</div>
    </div>
    <div class="rule">
      <span class="odds">100%</span>
      <div class="txt">满桌的人都想从我这赢点什么。<span class="em">唯独你，不肯做我的筹码</span>——所以我才更想留住你。</div>
    </div>
  </div>

  <div class="quote">
    <p>「赢过所有牌局，看穿所有人心——可你是我第一次不敢算清胜率，也是我唯一愿意输掉所有的那一局。」</p>
    <div class="attr">— 顾砚礼 / 私人包厢独白</div>
  </div>

  <div class="foot">
    <div class="divider"></div>
    <p>本档案内容纯属虚构 与现实无关<br>Table Zero © 澳门赌王档案</p>
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
