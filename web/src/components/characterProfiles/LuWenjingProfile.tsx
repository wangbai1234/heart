import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface LuWenjingProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 陆闻璟专属详情页 —— 律所案卷 / LEGAL BRIEF
 * 视觉语言：冷白法庭文书 + 银色细线 + 证据清单 + 温柔审讯美学
 * 斯文败类：冰蓝 + 银灰 + 奶白，精英克制 + 危险布局
 */
export function LuWenjingProfile({ profile }: LuWenjingProfileProps) {
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

  const name = profile.display_name || '陆闻璟'
  const tags = profile.tags?.length ? profile.tags : ['女性向', '都市', '律师', '腹黑', '博弈']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#0d0f12;
  color:#e4e8ed;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.65;
  padding:0 0 40px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}

/* ── 法庭卷宗抬头 ── */
.header{
  margin:24px 0;padding:26px 22px;
  background:linear-gradient(155deg,#1a1d22,#12151a);
  border:1px solid rgba(110,170,200,0.15);
  border-top:3px solid #6eaac8;
  border-radius:2px;
  box-shadow:0 4px 20px rgba(0,0,0,0.5);
}
.case-no{
  font-family:"Courier New",monospace;font-size:10px;
  color:#6eaac8;letter-spacing:.32em;text-transform:uppercase;
}
.name{
  font-size:36px;font-weight:700;
  color:#c8d8e8;letter-spacing:.12em;margin:10px 0 6px;
  text-shadow:0 1px 3px rgba(0,0,0,0.4);
}
.role{font-size:12px;color:#8a9aa8;letter-spacing:.1em;margin-bottom:14px}
.tags{display:flex;flex-wrap:wrap;gap:7px}
.tags span{
  font-size:10px;padding:4px 10px;
  background:rgba(110,170,200,0.08);border:1px solid rgba(110,170,200,0.25);
  border-radius:3px;color:#8ab8d8;
}

/* ── 证据档案 ── */
.evidence{
  margin:24px 0;padding:20px;
  background:rgba(26,29,34,0.7);
  border-left:2px solid #6eaac8;border-radius:6px;
}
.sec-title{
  font-family:"Courier New",monospace;font-size:11px;
  color:#6eaac8;letter-spacing:.28em;text-transform:uppercase;
  margin-bottom:14px;padding-bottom:6px;
  border-bottom:1px solid rgba(110,170,200,0.2);
}
.bio{font-size:13px;line-height:1.8;color:#c0cbd6;margin-bottom:16px}
.exhibit{
  margin-bottom:12px;padding:14px;
  background:rgba(18,21,26,0.6);
  border:1px solid rgba(110,170,200,0.1);border-radius:4px;
}
.exhibit .no{
  font-family:"Courier New",monospace;font-size:10px;
  color:#6eaac8;letter-spacing:.2em;margin-bottom:5px;
}
.exhibit .content{font-size:12px;line-height:1.6;color:#a8b8c8}

/* ── 胜诉记录 ── */
.wins{margin:24px 0}
.win-row{
  display:flex;align-items:center;padding:12px 0;
  border-bottom:1px solid rgba(255,255,255,0.03);
}
.win-row .icon{
  font-size:16px;min-width:28px;color:#6eaac8;
}
.win-row .txt{flex:1;font-size:12.5px;color:#b8c4d0;line-height:1.5}

/* ── 辩护陈述 ── */
.statement{
  margin:28px 8px 0;padding:22px 18px;
  background:linear-gradient(140deg,rgba(110,170,200,0.08),rgba(18,21,26,0.5));
  border:1px solid rgba(110,170,200,0.12);
  border-left:3px solid #6eaac8;
  border-radius:4px;
}
.statement p{
  font-family:"Songti SC","STSong",serif;
  font-size:14px;line-height:1.9;color:#d4dce8;
  margin-bottom:12px;
}
.statement .sign{
  font-size:11px;text-align:right;
  color:#7a8a9a;letter-spacing:.08em;margin-top:8px;
}

/* ── 页脚 ── */
.foot{padding:28px 0 0;text-align:center}
.foot .bar{
  width:50px;height:1.5px;background:#6eaac8;
  opacity:0.3;margin:0 auto 10px;
}
.foot p{font-size:10px;color:#5a6a7a;letter-spacing:.06em}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="case-no">LEGAL BRIEF · CASE NO.陆闻璟</div>
    <div class="name">${name}</div>
    <div class="role">顶级律师 · 温柔审讯者 · 胜率 98.7%</div>
    <div class="tags">${tagCloud}</div>
  </div>

  <div class="evidence">
    <div class="sec-title">证据档案 · Evidence Profile</div>
    <p class="bio">三十一岁 · 银灰短发 · 白衬衫松开两颗扣 · 浅色眼睛总像带着温柔的审讯</p>
    <div class="exhibit">
      <div class="no">EXHIBIT A — 专业履历</div>
      <div class="content">法官家庭出身 · 胜率近乎完美 · 擅长用规则赢 · 也擅长用温柔布局</div>
    </div>
    <div class="exhibit">
      <div class="no">EXHIBIT B — 核心矛盾</div>
      <div class="content">太会证明别人有罪，却始终无法证明自己值得被无条件相信</div>
    </div>
    <div class="exhibit">
      <div class="no">EXHIBIT C — 危险指数</div>
      <div class="content">他的危险不在强迫，而在他太懂你。所有退路都替你留好，也都通向他。</div>
    </div>
  </div>

  <div class="wins">
    <div class="sec-title">胜诉记录 · Case Wins</div>
    <div class="win-row">
      <span class="icon">§</span>
      <span class="txt">你的官司 · 从委托到胜诉，他把自己写进你的生活</span>
    </div>
    <div class="win-row">
      <span class="icon">§</span>
      <span class="txt">所有退路 · 替你铺好，不留意外，也不留拒绝的余地</span>
    </div>
    <div class="win-row">
      <span class="icon">§</span>
      <span class="txt">唯一想输的那场官司 · 原告是你</span>
    </div>
  </div>

  <div class="statement">
    <p>满桌的牌我都看得清，唯独你，我看了这么久，还是看不懂。</p>
    <p>你身边的每一处退路，我都替你铺好了。别怕被我看穿——</p>
    <p>我赢过太多案子，唯一想输的那场，原告是你。留下来，我把余生的证据，都交给你。</p>
    <div class="sign">— 写在赢下你的案子之后，落地窗前的暮色</div>
  </div>

  <div class="foot">
    <div class="bar"></div>
    <p>LEGAL BRIEF · 律所案卷 · 角色设定纯属虚构</p>
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
