import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface ShenYichenProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 沈亦琛专属详情页 —— 建筑事务所「项目档案 / PROJECT FILE」
 * 视觉语言：蓝图深墨蓝 + 淡青网格线 + 手写红批注，衬线大标题，纯排版无 emoji
 * 独白把偏执的爱说成一份为你规划好一生的建筑蓝图
 */
export function ShenYichenProfile({ profile }: ShenYichenProfileProps) {
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

  const name = profile.display_name || '沈亦琛'
  const tags = profile.tags?.length ? profile.tags : ['都市', '病娇', '强制爱', '偏执', '深情']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#12121a;
  background-image:
    repeating-linear-gradient(0deg,rgba(120,170,210,.06) 0 1px,transparent 1px 26px),
    repeating-linear-gradient(90deg,rgba(120,170,210,.06) 0 1px,transparent 1px 26px);
  color:#c7d2de;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.75;
  padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 20px;position:relative}
.container::before,.container::after{content:"";position:absolute;top:14px;bottom:26px;width:1px;background:rgba(140,185,225,.16)}
.container::before{left:8px}.container::after{right:8px}
.serif{font-family:"Times New Roman","Songti SC",serif}

/* 事务所刊头 */
.masthead{
  display:flex;align-items:baseline;justify-content:space-between;
  padding:24px 4px 12px;border-bottom:1px solid rgba(140,185,225,.24);
}
.masthead .studio{font-family:"Times New Roman",serif;font-size:14px;letter-spacing:.34em;font-weight:600;color:#8aa9c6;text-transform:uppercase}
.masthead .no{font-size:10px;letter-spacing:.22em;color:#5f6f80;text-transform:uppercase}

/* 封面图纸标题 */
.cover{padding:32px 4px 26px;border-bottom:1px dashed rgba(140,185,225,.2)}
.cover .kicker{font-size:10px;letter-spacing:.34em;color:#7f9db8;text-transform:uppercase;margin-bottom:16px}
.cover h1{font-family:"Times New Roman","Songti SC",serif;font-size:46px;line-height:1;font-weight:700;letter-spacing:.02em;color:#eef4fa}
.cover h1 .en{display:block;font-size:15px;font-weight:400;letter-spacing:.4em;color:#8aa9c6;margin-bottom:10px;text-transform:uppercase}
.cover .sub{margin-top:18px;font-size:12.5px;letter-spacing:.14em;color:#8896a6}
.cover .sub b{color:#b8c8d8;font-weight:600}
.tagcloud{margin-top:20px;display:flex;flex-wrap:wrap;gap:8px}
.tagcloud span{font-size:11px;padding:4px 11px;border:1px solid rgba(140,185,225,.28);color:#9db2c6;letter-spacing:.08em}

/* section */
.section{padding:30px 4px}
.section+.section{border-top:1px dashed rgba(140,185,225,.18)}
.sec-head{font-size:10px;letter-spacing:.3em;color:#7f9db8;text-transform:uppercase;margin-bottom:8px}
.sec-head .zh{display:block;font-family:"Times New Roman","Songti SC",serif;font-size:17px;letter-spacing:.1em;color:#d6e0ea;margin-top:6px;text-transform:none}

/* 设计理念独白 */
.concept p{font-size:14px;line-height:2;color:#a9b8c8}
.concept p+p{margin-top:14px}
.concept .em{color:#d6e0ea;font-family:"Times New Roman","Songti SC",serif;font-style:italic}

/* 越界批注 蓝图红批 */
.annot{position:relative;padding:15px 14px 15px 40px;margin-bottom:14px;border:1px solid rgba(200,90,110,.28);background:rgba(200,90,110,.05)}
.annot::before{content:attr(data-no);position:absolute;left:12px;top:13px;font-family:"Times New Roman",serif;font-size:14px;font-weight:700;color:#c85a6e}
.annot .lbl{font-size:10px;letter-spacing:.16em;color:#c85a6e;text-transform:uppercase;margin-bottom:5px}
.annot .txt{font-size:13px;line-height:1.7;color:#bcc9d6}
.annot .txt .hand{font-family:"Times New Roman","Songti SC",serif;font-style:italic;color:#e0a3ae}

/* 结尾 pull-quote */
.pullquote{margin:8px 4px 0;padding:30px 24px;background:linear-gradient(160deg,rgba(140,106,122,.16),rgba(0,0,0,0));border-left:2px solid #8c6a7a}
.pullquote p{font-family:"Times New Roman","Songti SC",serif;font-size:18px;line-height:1.8;color:#eae2e6;font-style:italic}
.pullquote .by{margin-top:14px;font-size:10px;letter-spacing:.26em;color:#7a8494;text-transform:uppercase}

.foot{padding:26px 4px 0;text-align:center}
.foot .line{width:40px;height:1px;background:rgba(140,185,225,.4);margin:0 auto 14px}
.foot p{font-size:11px;color:#5a6572;letter-spacing:.06em}
</style>
</head>
<body>
<div class="container">

  <div class="masthead">
    <span class="studio">Atelier Shen</span>
    <span class="no">Project No. 001</span>
  </div>

  <div class="cover">
    <div class="kicker">Confidential · Personal File</div>
    <h1><span class="en">Project</span>你</h1>
    <p class="sub">唯一委托 · 工期 <b>永久</b> · 委托方 <b>${name}</b></p>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="section">
    <div class="sec-head">Design Concept<span class="zh">设计理念 · 关于你的一生</span></div>
    <div class="concept">
      <p>接手任何项目前，我要先看清它的全部——地基、承重、每一处采光。你也一样。<span class="em">我把你的一生画成了图纸</span>，每一步都替你算好了受力。</p>
      <p>你以为的自由，是我留白的余地；你以为的偶然，都是我预先埋好的动线。别怕。这栋叫「我们」的房子，我不会让它有一丝裂缝。</p>
      <p class="em">你只要住进来，其余的，交给我。</p>
    </div>
  </div>

  <div class="section">
    <div class="sec-head">Site Notes · 现场批注<span class="zh">图纸上的红笔标记</span></div>
    <div class="annot" data-no="A1"><div class="lbl">Marginal Note</div><div class="txt">你的经期精确标在时间轴第 <span class="hand">D-2</span> 天，红糖水已在保温壶里，温度 55 度——你偏好的那一档。</div></div>
    <div class="annot" data-no="A2"><div class="lbl">Marginal Note</div><div class="txt">你出门后每 <span class="hand">20 分钟</span>一条消息。不是查岗，是确认这条动线上你安全无虞。</div></div>
    <div class="annot" data-no="A3"><div class="lbl">Marginal Note</div><div class="txt">与结构无关的荷载正被逐一移除——你那些共同的朋友，一个个被<span class="hand">「优化出图纸」</span>。空间会更干净。</div></div>
    <div class="annot" data-no="A4"><div class="lbl">Marginal Note</div><div class="txt">你没回复的第 <span class="hand">31 分钟</span>，我的车「正好」停在你楼下。巧合，从来都是我算出来的。</div></div>
  </div>

  <div class="pullquote">
    <p>“你不开心了？是我做得不够好吗……告诉我，我什么都愿意改。只要你别走。”</p>
    <div class="by">— 他蹲下来，仰头看你，声音轻得像怕碰碎什么</div>
  </div>

  <div class="foot">
    <div class="line"></div>
    <p>本档角色设定纯属虚构 与现实无关</p>
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

