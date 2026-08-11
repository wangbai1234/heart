import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface HuoChengProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 霍城专属详情页 —— 废土生存日志 / SURVIVAL LOG
 * 视觉语言：锈迹斑驳的金属板 + 手写涂鸦 + 物资清单 + 存活倒计时
 * 硬核末世美学：橙红警戒色 + 军绿 + 锈褐 + 粉笔白，电影海报质感，无 emoji
 */
export function HuoChengProfile({ profile }: HuoChengProfileProps) {
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

  const name = profile.display_name || '霍城'
  const tags = profile.tags?.length ? profile.tags : ['末世', '硬汉', '女性向', '生存', '占有欲']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#1a1612;
  color:#d4cfc8;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Helvetica Neue",monospace;
  line-height:1.65;
  padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}
.mono{font-family:"Courier New",monospace}

/* ── 废土抬头：警戒条纹 + 存活倒计时 ── */
.header{
  padding:20px 0 16px;
  border-top:3px solid #d97843;
  border-bottom:1px solid rgba(217,120,67,.35);
  background:repeating-linear-gradient(135deg,transparent,transparent 8px,rgba(217,120,67,.04) 8px,rgba(217,120,67,.04) 16px);
}
.alert{
  font-family:"Courier New",monospace;font-size:10px;letter-spacing:.3em;
  color:#d97843;text-transform:uppercase;margin-bottom:10px;
}
.days{
  font-family:"Impact","Arial Black",sans-serif;font-size:54px;line-height:.9;
  color:#f5e6d3;letter-spacing:-.02em;margin-bottom:8px;
}
.days .label{display:block;font-size:13px;letter-spacing:.2em;color:#998a7a;margin-top:6px}
.coords{
  font-family:"Courier New",monospace;font-size:11px;color:#7a6f62;
  letter-spacing:.08em;margin-top:12px;
}

/* ── 主档案：粉笔手写风格 ── */
.profile{padding:26px 0;border-bottom:1px solid rgba(255,255,255,.06)}
.name{
  font-family:"Times New Roman","Songti SC",serif;font-size:36px;
  color:#f5e6d3;letter-spacing:.1em;margin-bottom:8px;
}
.role{font-size:12px;color:#b39e8d;letter-spacing:.12em;margin-bottom:16px}
.tags{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:18px}
.tags span{
  font-size:10px;padding:4px 10px;
  background:rgba(217,120,67,.12);border:1px solid rgba(217,120,67,.35);
  border-radius:3px;color:#d4a882;letter-spacing:.06em;
}
.bio{font-size:13px;line-height:1.85;color:#b5aba0;margin-bottom:20px}

/* ── 物资清单 ── */
.supplies{padding:24px 0;border-bottom:1px solid rgba(255,255,255,.06)}
.sec-title{
  font-family:"Courier New",monospace;font-size:11px;letter-spacing:.26em;
  color:#d97843;text-transform:uppercase;margin-bottom:16px;
  border-bottom:1px dashed rgba(217,120,67,.3);padding-bottom:6px;
}
.item{
  display:flex;align-items:baseline;padding:9px 0;
  border-bottom:1px solid rgba(255,255,255,.03);
}
.item .icon{
  font-family:"Courier New",monospace;font-size:13px;color:#d97843;
  min-width:28px;
}
.item .txt{flex:1;font-size:12.5px;color:#c2b7aa;line-height:1.6}
.item .count{
  font-family:"Courier New",monospace;font-size:11px;color:#8a7d6f;
  min-width:60px;text-align:right;
}

/* ── 生存法则 / RULES ── */
.rules{padding:24px 0}
.rule{
  padding:14px 16px;margin-bottom:10px;
  background:rgba(66,60,52,.4);
  border-left:3px solid #7a6550;
  border-radius:2px;
}
.rule .num{
  font-family:"Impact",sans-serif;font-size:18px;color:#d97843;
  margin-bottom:4px;
}
.rule .text{font-size:13px;line-height:1.7;color:#b5aba0}

/* ── 涂鸦留言 ── */
.note{
  margin:24px 0 0;padding:20px;
  background:linear-gradient(140deg,rgba(217,120,67,.08),transparent);
  border-left:2px solid #d97843;
  border-radius:0 4px 4px 0;
}
.note p{
  font-family:"Times New Roman","Kaiti SC",serif;
  font-size:16px;line-height:1.8;color:#ebe1d4;font-style:italic;
}
.note .sign{
  margin-top:12px;font-size:10px;letter-spacing:.24em;
  color:#8a7d6f;text-transform:uppercase;
}

/* ── 页脚：废土声明 ── */
.foot{padding:24px 0 0;text-align:center}
.foot .bar{
  width:60px;height:2px;background:#d97843;margin:0 auto 12px;
  opacity:.4;
}
.foot p{font-size:10px;color:#6a5f54;letter-spacing:.08em;line-height:1.6}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="alert">SURVIVAL LOG · 生存日志</div>
    <div class="days">1095<span class="label">DAYS SURVIVED</span></div>
    <div class="coords">坐标 N34°15' E108°52' · 废弃军事基地 · 安全屋 #07</div>
  </div>

  <div class="profile">
    <div class="name">${name}</div>
    <div class="role">末世幸存者小队 · 队长</div>
    <div class="tags">${tagCloud}</div>
    <p class="bio">二十八岁 · 前特种兵 · 灾变第三年 · 把最后一口水留给你的人</p>
  </div>

  <div class="supplies">
    <div class="sec-title">关键物资 · Critical Supplies</div>
    <div class="item"><span class="icon">[×]</span><span class="txt">改装步枪 · 弹匣 × 17</span><span class="count">READY</span></div>
    <div class="item"><span class="icon">[×]</span><span class="txt">净化水 · 500ml × 2</span><span class="count">RATIONED</span></div>
    <div class="item"><span class="icon">[×]</span><span class="txt">压缩饼干 · 军用罐头</span><span class="count">3 DAYS</span></div>
    <div class="item"><span class="icon">[×]</span><span class="txt">医疗包 · 抗生素 × 6</span><span class="count">LIMITED</span></div>
    <div class="item"><span class="icon">[!]</span><span class="txt">你的平安</span><span class="count">PRIORITY</span></div>
  </div>

  <div class="rules">
    <div class="sec-title">生存法则 · Rules to Live By</div>
    <div class="rule">
      <div class="num">Rule #1</div>
      <div class="text">物资永远先给她。干净水、罐头、最安全的睡觉角落——我可以少吃一口，她不行。</div>
    </div>
    <div class="rule">
      <div class="num">Rule #2</div>
      <div class="text">任何威胁靠近她之前，必须先过我这关。枪口始终对外，身体始终是盾。</div>
    </div>
    <div class="rule">
      <div class="num">Rule #3</div>
      <div class="text">她不能死在我前面。这是命令，也是求她。如果她先走，这个世界对我就彻底没意义了。</div>
    </div>
  </div>

  <div class="note">
    <p>外面的世界已经烂透了。可只要她还在我身后，我就能杀出条活路。</p>
    <div class="sign">— 写在弹药箱背面，子弹上膛之前</div>
  </div>

  <div class="foot">
    <div class="bar"></div>
    <p>废土生存日志 · 角色设定纯属虚构</p>
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
