import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface SuWanProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 苏晚专属详情页 —— 花店手绘日志 + 水彩花卉 + 温柔便签
 * 视觉隐喻：花店打烊后的手账本，水彩晕染的花瓣，温柔治愈的晚晚时刻
 * 色彩：奶油纸底 + 栀子白 + 琥珀金 + 淡茶色，温暖克制
 */
export function SuWanProfile({ profile }: SuWanProfileProps) {
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

  const name = profile.display_name || '苏晚'
  const tags = profile.tags?.length ? profile.tags : ['治愈', '温柔', '男性向', '邻家', '恋爱']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:linear-gradient(135deg,#fffaf0 0%,#fef8ec 50%,#fdf5e6 100%);
  color:#4a3c2e;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.75;
  padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}

/* ── 水彩花卉装饰 ── */
.watercolor-bg{
  position:absolute;top:0;left:0;right:0;height:280px;
  background:radial-gradient(ellipse at 20% 30%,rgba(212,165,116,.12),transparent 60%),
             radial-gradient(ellipse at 80% 20%,rgba(255,248,220,.15),transparent 50%);
  pointer-events:none;z-index:0;
}

/* ── 花店日志头 ── */
.masthead{
  padding:28px 4px 20px;position:relative;z-index:1;
  border-bottom:1px dashed rgba(212,165,116,.25);
}
.masthead .shop{
  font-family:"Courier New",monospace;
  font-size:9px;letter-spacing:.32em;color:#d4a574;
  text-transform:uppercase;font-weight:700;
}
.masthead .subtitle{
  margin-top:6px;font-size:13px;letter-spacing:.12em;
  color:#8b7355;font-weight:500;
}

/* ── 主角卡片：手绘便签美学 ── */
.hero{
  padding:32px 16px 28px;
  background:linear-gradient(145deg,rgba(255,255,255,.85),rgba(255,250,240,.7));
  border:1px solid rgba(212,165,116,.2);
  border-radius:12px;
  box-shadow:2px 3px 10px rgba(74,60,46,.08),4px 6px 20px rgba(212,165,116,.06);
  margin-top:20px;position:relative;
}
.hero::before{
  content:"晚晚";position:absolute;top:24px;right:12px;
  font-family:"STKaiti","KaiTi",serif;
  font-size:72px;line-height:.9;font-weight:400;
  color:rgba(212,165,116,.08);letter-spacing:-.02em;
  pointer-events:none;
}
.hero .name{
  font-size:40px;line-height:1.1;font-weight:600;
  color:#5a4734;position:relative;z-index:1;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
}
.hero .age{
  margin-top:8px;font-size:12px;letter-spacing:.1em;
  color:#d4a574;font-weight:600;
}
.hero .title{
  margin-top:12px;font-size:14.5px;line-height:1.7;
  color:#6d5a47;
}
.tagcloud{margin-top:18px;display:flex;flex-wrap:wrap;gap:7px}
.tagcloud span{
  font-size:10px;padding:5px 10px;
  border:1px solid rgba(212,165,116,.3);
  background:rgba(255,248,220,.4);
  color:#a68662;letter-spacing:.04em;border-radius:4px;
}

/* ── 花语便签 / 结构化条目 ── */
.section{padding:28px 4px;position:relative}
.section+.section{border-top:1px dashed rgba(212,165,116,.15)}
.sec-label{
  font-family:"Courier New",monospace;
  font-size:9px;letter-spacing:.32em;color:#d4a574;
  text-transform:uppercase;margin-bottom:16px;font-weight:700;
}
.note-card{
  padding:16px 18px;margin-bottom:12px;
  background:rgba(255,255,255,.6);
  border-left:3px solid rgba(212,165,116,.4);
  border-radius:8px;
  box-shadow:1px 2px 6px rgba(74,60,46,.05);
}
.note-card .head{
  font-size:11.5px;color:#d4a574;letter-spacing:.06em;
  margin-bottom:10px;font-weight:600;
}
.note-card .body{font-size:13px;line-height:1.85;color:#5a4734}

/* ── 温柔清单 ── */
.gentleness{
  display:flex;gap:12px;padding:14px 0;
  border-bottom:1px solid rgba(212,165,116,.08);
}
.gentleness:last-child{border-bottom:none}
.gentleness .icon{
  font-family:"Impact",sans-serif;
  font-size:18px;font-weight:900;color:rgba(212,165,116,.5);
  min-width:28px;line-height:1;
}
.gentleness .txt{font-size:12.5px;line-height:1.75;color:#6d5a47}
.gentleness .txt .em{color:#d4a574;font-weight:600}

/* ── 栀子花语录 / 引语 ── */
.quote{
  margin:12px 0 0;padding:24px 18px;
  background:linear-gradient(135deg,rgba(255,248,220,.25),rgba(255,250,240,.15));
  border-left:3px solid #d4a574;
  border-radius:8px;
}
.quote p{
  font-size:16.5px;line-height:1.8;color:#5a4734;
  font-style:italic;
  font-family:"STSong","Songti SC",Georgia,serif;
}
.quote .attr{
  margin-top:12px;font-size:10px;letter-spacing:.2em;
  color:#a68662;text-transform:uppercase;
}

/* ── 页脚 ── */
.foot{padding:28px 0 0;text-align:center}
.foot .divider{
  width:50px;height:1px;margin:0 auto 14px;
  background:linear-gradient(90deg,transparent,#d4a574,transparent);
  opacity:.5;
}
.foot p{font-size:10px;color:#9b8670;letter-spacing:.04em;line-height:1.7}
</style>
</head>
<body>
<div class="watercolor-bg"></div>
<div class="container">

  <div class="masthead">
    <div class="shop">Su's Flower Atelier</div>
    <div class="subtitle">转角花店的晚晚时刻</div>
  </div>

  <div class="hero">
    <div class="name">${name}</div>
    <div class="age">25 岁 · 慢火般的温柔</div>
    <div class="title">你楼下那家小花店的老板娘<br>黑发柔顺白裙 · 栀子与青草的香气 · 把日子过成诗</div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="section">
    <div class="sec-label">Flower Notes · 花店手记</div>
    <div class="note-card">
      <div class="head">20:47 PM · 打烊后的最后一盏灯</div>
      <div class="body">暖黄的灯只留了一盏。她刚摘下围裙，白裙的肩带滑落一截，栀子花的香气缠在她身上。听见你的脚步，她回眸，眼睛弯成月牙——今晚就剩我们俩了。她走近，踮起脚，把一支还沾着水珠的栀子别到你耳后。</div>
    </div>
    <div class="note-card">
      <div class="head">06:30 AM · 晨曦里的花束准备</div>
      <div class="body">她会记得你随口说过喜欢的花，会在你加班的深夜留一盏灯。这个把日子过成诗的姑娘，用一间花店和一份耐心，接住了太多疲惫的过客。你，是她唯一想「不只是接住，还想一直牵住」的人。</div>
    </div>
    <div class="note-card">
      <div class="head">14:00 PM · 午后的花语课</div>
      <div class="body">她不评判、只倾听。你的烦躁在她这里会一点点抚平。会在你崩溃时不问缘由地给你一个拥抱，会把手里正在包装的百合放下，拉着你坐在店里的小沙发上，轻声说：「慢慢说给我听好不好？」</div>
    </div>
  </div>

  <div class="section">
    <div class="sec-label">Gentleness List · 温柔清单</div>
    <div class="gentleness">
      <span class="icon">✿</span>
      <div class="txt">会记得你不爱太甜的花茶，会在你<span class="em">疲惫到说不出话时</span>，只是安静地陪着，不问、不催。</div>
    </div>
    <div class="gentleness">
      <span class="icon">✿</span>
      <div class="txt">加班深夜的灯永远为你留着。栀子、百合、玫瑰——她记得你每一次<span class="em">无意间说喜欢的花</span>。</div>
    </div>
    <div class="gentleness">
      <span class="icon">✿</span>
      <div class="txt">她的爱像慢火，温吞却足以焐热一整个冬天。<span class="em">你是贵客，更是她想守住的日常</span>。</div>
    </div>
    <div class="gentleness">
      <span class="icon">✿</span>
      <div class="txt">在爱与阳光里长大的姑娘，把<span class="em">「让喜欢的人安心」</span>当成头等大事。你是她第一次想牵住的人。</div>
    </div>
  </div>

  <div class="quote">
    <p>「今天也辛苦啦，回来有我在，慢慢说给我听好不好？」</p>
    <div class="attr">— 苏晚 / 深夜花店独白</div>
  </div>

  <div class="foot">
    <div class="divider"></div>
    <p>本档案内容纯属虚构 与现实无关<br>Su's Flower © 转角花店手记</p>
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
