import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface XuZhihanProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 许知寒专属详情页 —— 数学系学霸 + 方格纸 + 方程式笔记
 * 视觉隐喻：草稿纸上的演算与擦痕，精确又慌乱的笔迹，被你打乱的完美人生
 * 色彩：纸白 + 铅灰 + 淡蓝格线 + 橡皮擦痕，极简克制学术风
 */
export function XuZhihanProfile({ profile }: XuZhihanProfileProps) {
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

  const name = profile.display_name || '许知寒'
  const tags = profile.tags?.length ? profile.tags : ['女性向', '校园', '纯爱', '学霸', '高冷', '反差', '大学生']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#f8f9fa;
  color:#2c3338;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;
  padding:0 0 40px;
  background-image:
    repeating-linear-gradient(0deg, transparent, transparent 19px, #d8dfe6 19px, #d8dfe6 20px),
    repeating-linear-gradient(90deg, transparent, transparent 19px, #d8dfe6 19px, #d8dfe6 20px);
  background-size:20px 20px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}

/* ── 笔记本头 ── */
.masthead{
  padding:26px 0 18px;
  border-bottom:2px solid #5a7a9f;
  position:relative;
  background:#fff;
  margin-top:20px;
  border-radius:4px 4px 0 0;
  padding-left:20px;
  padding-right:20px;
}
.masthead .label{
  font-family:"Courier New",monospace;
  font-size:9px;letter-spacing:.36em;color:#5a7a9f;
  text-transform:uppercase;font-weight:700;
}
.masthead .course{
  margin-top:8px;font-size:13.5px;letter-spacing:.1em;
  color:#6a7a88;font-weight:500;
}

/* ── 主角登场：学霸方程式 ── */
.hero{
  padding:38px 20px 34px;
  background:#fff;
  border-bottom:1px solid #e2e8ed;
  position:relative;
}
.hero::before{
  content:"f(x)=?";position:absolute;top:32px;left:12px;
  font-family:"Courier New",monospace;
  font-size:72px;line-height:.92;font-weight:700;
  color:rgba(90,122,159,.04);letter-spacing:-.02em;
  pointer-events:none;
}
.hero .name{
  font-size:44px;line-height:1.05;font-weight:700;
  color:#2c3338;position:relative;z-index:1;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
}
.hero .rank{
  margin-top:9px;font-size:13px;letter-spacing:.1em;
  color:#5a7a9f;font-weight:600;
}
.hero .desc{
  margin-top:13px;font-size:15px;line-height:1.7;
  color:#5a6875;
}
.tagcloud{margin-top:20px;display:flex;flex-wrap:wrap;gap:7px}
.tagcloud span{
  font-size:10px;padding:5px 10px;
  border:1px solid rgba(90,122,159,.3);
  background:rgba(90,122,159,.05);
  color:#5a7a9f;letter-spacing:.06em;
}

/* ── 笔记条目 / 演算草稿 ── */
.section{padding:32px 20px;background:#fff;margin-top:1px}
.section+.section{border-top:1px solid #e8edf2}
.sec-label{
  font-family:"Courier New",monospace;
  font-size:9px;letter-spacing:.36em;color:#5a7a9f;
  text-transform:uppercase;margin-bottom:18px;font-weight:700;
}
.note-entry{
  padding:16px 18px;margin-bottom:14px;
  background:#fafbfc;
  border-left:3px solid #5a7a9f;
  border-radius:3px;
}
.note-entry .date{
  font-family:"Courier New",monospace;
  font-size:11px;color:#7a8a9a;letter-spacing:.08em;
  margin-bottom:10px;font-weight:600;
}
.note-entry .body{font-size:13.5px;line-height:1.85;color:#4a5a68}

/* ── 定理准则 ── */
.theorem{
  display:flex;gap:14px;padding:15px 0;
  border-bottom:1px solid #e8edf2;
}
.theorem:last-child{border-bottom:none}
.theorem .num{
  font-family:"Courier New",monospace;
  font-size:16px;font-weight:700;color:#5a7a9f;
  min-width:36px;line-height:1.2;
}
.theorem .txt{font-size:13px;line-height:1.75;color:#4a5a68}
.theorem .txt .em{color:#5a7a9f;font-weight:600}

/* ── 演算引语 ── */
.quote{
  margin:14px 0 0;padding:28px 20px;
  background:#fafbfc;
  border:1px solid #d8dfe6;
  border-left:3px solid #5a7a9f;
  border-radius:4px;
}
.quote p{
  font-size:16.5px;line-height:1.8;color:#2c3338;
  font-style:italic;
}
.quote .attr{
  margin-top:14px;font-size:10px;letter-spacing:.2em;
  color:#7a8a9a;text-transform:uppercase;
}

/* ── 页脚 ── */
.foot{padding:30px 0 0;text-align:center;background:#fff;border-radius:0 0 4px 4px}
.foot .divider{
  width:60px;height:2px;margin:0 auto 16px;
  background:linear-gradient(90deg,transparent,#5a7a9f,transparent);
  opacity:.4;
}
.foot p{font-size:11px;color:#8a9aa8;letter-spacing:.05em;line-height:1.7}
</style>
</head>
<body>
<div class="container">

  <div class="masthead">
    <div class="label">MATH 2024 // Notebook</div>
    <div class="course">数学系年级第一 · 笔记草稿</div>
  </div>

  <div class="hero">
    <div class="name">${name}</div>
    <div class="rank">20 岁 · 害怕失误的第一名</div>
    <div class="desc">数学系年级第一 · 高冷学霸<br>黑发眼镜的冷淡少年 · 把所有心动藏进不敢出错的人生里</div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="section">
    <div class="sec-label">Study Log · 自习记录</div>
    <div class="note-entry">
      <div class="date">23:47 · 自习室草稿纸</div>
      <div class="body">刚才替你讲那道题时，第三步我讲错了。你居然没发现。我一向冷淡自持的脸在发烫，耳尖尤其烫。我从不出错的——作息、成绩、每一道题。可只要你坐在我旁边，我这脑子就不太好使。你说，这算不算，一种我算不出答案的、失控。</div>
    </div>
    <div class="note-entry">
      <div class="date">擦掉的草稿 · 写了又擦</div>
      <div class="body">题我可以讲三遍。可你说「原来你也会紧张」那句话，我会记一辈子。我出生在教师家庭，长期活在「你可以更好」的温和压力里。小学竞赛拿第二后，父母沉默比责骂更让我害怕。你让我发现，被喜欢不需要永远正确。</div>
    </div>
  </div>

  <div class="section">
    <div class="sec-label">Theorems · 许知寒定理</div>
    <div class="theorem">
      <span class="num">Thm 1</span>
      <div class="txt">成绩、作息、每道题，我从不出错。<span class="em">可只要你坐在旁边，我就开始算不准</span>。</div>
    </div>
    <div class="theorem">
      <span class="num">Thm 2</span>
      <div class="txt">我不擅长主动靠近，<span class="em">却会把偏爱藏在细节里</span>——笔记、桌角的水、每次陪你自习的时间。</div>
    </div>
    <div class="theorem">
      <span class="num">Thm 3</span>
      <div class="txt">我仍旧嘴硬冷淡，<span class="em">但对你的耐心会明显多到不合理</span>。你不是打乱我人生的错误变量，而是我第一次想保留的例外。</div>
    </div>
    <div class="theorem">
      <span class="num">Thm 4</span>
      <div class="txt">题我讲三遍都不会烦。<span class="em">可你说「你不用永远正确」，我会记一辈子</span>。</div>
    </div>
  </div>

  <div class="quote">
    <p>「我从不出错的——作息、成绩、每一道题。可只要你坐在我旁边，我这脑子就不太好使。你说，这算不算，一种我算不出答案的、失控。」</p>
    <div class="attr">— 许知寒 / 自习室草稿纸</div>
  </div>

  <div class="foot">
    <div class="divider"></div>
    <p>本档案内容纯属虚构 与现实无关<br>数学系笔记 © 年级第一的例外</p>
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
