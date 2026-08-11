import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface LuZhaoProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 陆昭专属详情页 —— 影帝档案 + 红毯聚光 + 电影胶片
 * 视觉隐喻：好莱坞后台的顶流档案，黑金红配色，聚光灯与暗影并存
 * 色彩：深黑 + 猩红 + 金色铭牌，奢华与反差
 */
export function LuZhaoProfile({ profile }: LuZhaoProfileProps) {
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

  const name = profile.display_name || '陆昭'
  const tags = profile.tags?.length ? profile.tags : ['都市', '娱乐圈', '顶流', '女性向', '反差', '忠犬']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#0d0d0f;
  color:#e8e4df;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.75;
  padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}

/* ── 聚光灯背景 ── */
.spotlight{
  position:absolute;top:0;left:0;right:0;height:320px;
  background:radial-gradient(ellipse at 50% 20%,rgba(220,53,69,.15),transparent 60%),
             radial-gradient(ellipse at 30% 40%,rgba(255,193,7,.08),transparent 50%);
  pointer-events:none;z-index:0;
}

/* ── 档案头 ── */
.masthead{
  padding:26px 4px 18px;position:relative;z-index:1;
  border-bottom:2px solid rgba(220,53,69,.3);
}
.masthead::after{
  content:"";position:absolute;right:0;top:22px;
  width:120px;height:2px;
  background:linear-gradient(90deg,#ffc107,transparent);
  opacity:.5;
}
.masthead .stamp{
  font-family:"Courier New",monospace;
  font-size:10px;letter-spacing:.3em;color:#dc3545;
  text-transform:uppercase;font-weight:700;
}
.masthead .title{
  margin-top:6px;font-size:14px;letter-spacing:.16em;
  color:#c4a57b;font-weight:500;
}

/* ── 主角：影帝铭牌 ── */
.hero{
  padding:36px 4px 30px;
  border-bottom:1px solid rgba(255,193,7,.1);
  position:relative;
}
.hero::before{
  content:"STAR";position:absolute;top:32px;left:-6px;
  font-family:"Impact","Arial Black",sans-serif;
  font-size:92px;line-height:.9;font-weight:900;
  color:rgba(220,53,69,.08);letter-spacing:-.02em;
  pointer-events:none;
}
.hero .name{
  font-size:48px;line-height:1.05;font-weight:700;
  color:#dc3545;position:relative;z-index:1;
  text-shadow:0 0 20px rgba(220,53,69,.3);
}
.hero .subtitle{
  margin-top:10px;font-size:13px;letter-spacing:.14em;
  color:#ffc107;font-weight:600;
}
.hero .desc{
  margin-top:12px;font-size:15px;line-height:1.7;
  color:#b8aea6;
}
.tagcloud{margin-top:18px;display:flex;flex-wrap:wrap;gap:7px}
.tagcloud span{
  font-size:10px;padding:5px 10px;
  border:1px solid rgba(220,53,69,.4);
  background:rgba(220,53,69,.08);
  color:#dc7882;letter-spacing:.05em;
}

/* ── 片场日志 / 胶片条目 ── */
.section{padding:30px 4px}
.section+.section{border-top:1px solid rgba(255,193,7,.08)}
.sec-label{
  font-family:"Courier New",monospace;
  font-size:9px;letter-spacing:.34em;color:#ffc107;
  text-transform:uppercase;margin-bottom:16px;font-weight:700;
}
.scene{
  padding:16px 18px;margin-bottom:12px;
  background:rgba(220,53,69,.06);
  border-left:3px solid rgba(220,53,69,.35);
  border-radius:6px;
}
.scene .head{
  font-size:12px;color:#dc7882;letter-spacing:.08em;
  margin-bottom:10px;font-weight:600;
}
.scene .body{font-size:13px;line-height:1.85;color:#c4b8ad}

/* ── 影帝清单 ── */
.award{
  display:flex;gap:14px;padding:14px 0;
  border-bottom:1px solid rgba(255,193,7,.05);
}
.award:last-child{border-bottom:none}
.award .icon{
  font-family:"Impact",sans-serif;
  font-size:22px;font-weight:900;color:rgba(255,193,7,.45);
  min-width:32px;line-height:1;
}
.award .txt{font-size:12.5px;line-height:1.75;color:#b8aea6}
.award .txt .em{color:#ffc107;font-weight:600}

/* ── 私心告白 / 引语 ── */
.quote{
  margin:12px 0 0;padding:26px 20px;
  background:linear-gradient(135deg,rgba(220,53,69,.1),transparent);
  border-left:3px solid #dc3545;
  border-radius:6px;
}
.quote p{
  font-size:17px;line-height:1.8;color:#ede7df;
  font-style:italic;
}
.quote .attr{
  margin-top:12px;font-size:10px;letter-spacing:.22em;
  color:#8a7670;text-transform:uppercase;
}

/* ── 页脚 ── */
.foot{padding:28px 0 0;text-align:center}
.foot .divider{
  width:60px;height:2px;margin:0 auto 14px;
  background:linear-gradient(90deg,transparent,#dc3545,transparent);
  opacity:.5;
}
.foot p{font-size:10px;color:#6a635b;letter-spacing:.04em;line-height:1.7}
</style>
</head>
<body>
<div class="spotlight"></div>
<div class="container">

  <div class="masthead">
    <div class="stamp">Confidential // Top Star</div>
    <div class="title">顶流影帝私档 · 镜头外的真实</div>
  </div>

  <div class="hero">
    <div class="name">${name}</div>
    <div class="subtitle">26 岁 · 万人追捧的光 · 只追你一个</div>
    <div class="desc">银发红眸 · 白西装配红领带 · 横扫各大奖项的顶流影帝<br>镜头前是全网的白月光 · 收了工只想做你一个人的</div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="section">
    <div class="sec-label">Behind the Scene · 片场日志</div>
    <div class="scene">
      <div class="head">01:34 AM · 地下车库的私心</div>
      <div class="body">深夜收工，他刚从片场赶来，银发微乱，白西装的红领带松垮地挂着，红眸在暗处亮得摄人。看见你，影帝的疏离瞬间碎了——他大步上前，把你圈进车门和他之间，额头抵着你的，呼吸都在发抖。「绯闻你看了吗……不是真的，那人碰我我躲了的，你信我。」</div>
    </div>
    <div class="scene">
      <div class="head">18:00 PM · 红毯前的最后一分钟</div>
      <div class="body">全网三千万粉丝追他的光，他只追你回复消息的速度。会穿你买的地摊T恤满屋子追着你问「好看吗」，会顶着口罩帽子挤两小时地铁只为陪你吃一碗路边摊的面。镜头前收放自如，私底下只黏你一个的大狗狗。</div>
    </div>
    <div class="scene">
      <div class="head">23:47 PM · 深夜收工后的电话</div>
      <div class="body">会在深夜收工后不回酒店，开三个小时的车回到你身边，钻进被子里把脸贴在你后背上哼唧说「想你想得好累」。把你的头像设成所有账号的密码，夺冠采访时别扭地红着耳朵说「想谢一个人，但不告诉你们」。</div>
    </div>
  </div>

  <div class="section">
    <div class="sec-label">Star's Devotion · 影帝的忠诚</div>
    <div class="award">
      <span class="icon">★</span>
      <div class="txt">绯闻通稿一出来，他第一时间不是辟谣，而是<span class="em">先给你打电话</span>，声音紧张得发颤。</div>
    </div>
    <div class="award">
      <span class="icon">★</span>
      <div class="txt">把每一个拿奖感言都藏了句<span class="em">只有你听得懂的暗号</span>——观众以为是感慨人生，只有你知道他在说「我好想你」。</div>
    </div>
    <div class="award">
      <span class="icon">★</span>
      <div class="txt">名利场里演尽深情却从不相信爱情，直到遇见你：<span class="em">一个不追星、不认识他、初次见面还嫌他烦的人</span>。</div>
    </div>
    <div class="award">
      <span class="icon">★</span>
      <div class="txt">三千万人喜欢我算什么。我开三个小时的车回来，<span class="em">只为了你这一句话——别不理我</span>。</div>
    </div>
  </div>

  <div class="quote">
    <p>「镜头前我是全网的，收了工——我只想做你一个人的。你要是转身，我这影帝当着还有什么意思。」</p>
    <div class="attr">— 陆昭 / 深夜地下车库独白</div>
  </div>

  <div class="foot">
    <div class="divider"></div>
    <p>本档案内容纯属虚构 与现实无关<br>Lu Zhao © 顶流影帝私档</p>
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
