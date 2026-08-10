import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface GuBeichenProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 顾北辰专属详情页 —— 高定商业杂志封面 + 独家专访 + 财经热榜
 * 参考 nimoo「闻斯璟」杂志封面模板：editorial 排版 / Q&A / trending list
 * 视觉语言：禁欲冷淡的墨黑 + 象牙白 + 香槟金，衬线大标题，纯排版无 emoji
 */
export function GuBeichenProfile({ profile }: GuBeichenProfileProps) {
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

  const name = profile.display_name || '顾北辰'
  const tags = profile.tags?.length ? profile.tags : ['都市', '豪门', '霸总', '禁欲', '年上']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#0c0c0e;
  color:#e8e4dd;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;
  padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}
.serif{font-family:"Times New Roman","Songti SC",serif}

/* ── 杂志刊头 ── */
.masthead{
  display:flex;align-items:baseline;justify-content:space-between;
  padding:22px 2px 12px;
  border-bottom:1px solid rgba(196,147,125,.28);
}
.masthead .logo{
  font-family:"Times New Roman",serif;
  font-size:15px;letter-spacing:.42em;font-weight:600;
  color:#c4937d;text-transform:uppercase;
}
.masthead .issue{
  font-size:10px;letter-spacing:.24em;color:#7a7168;text-transform:uppercase;
}

/* ── 封面标题 THE UNTOUCHABLE ── */
.cover{padding:34px 2px 26px;border-bottom:1px solid rgba(255,255,255,.06)}
.cover .kicker{font-size:10px;letter-spacing:.34em;color:#c4937d;text-transform:uppercase;margin-bottom:14px}
.cover h1{
  font-family:"Times New Roman",serif;
  font-size:52px;line-height:.94;font-weight:700;
  letter-spacing:-.01em;color:#f2ede6;
}
.cover h1 .thin{display:block;font-weight:400;font-style:italic;color:#b9b0a6;font-size:40px}
.cover .zh{margin-top:16px;font-size:19px;letter-spacing:.5em;color:#e8e4dd;font-weight:600}
.cover .sub{margin-top:12px;font-size:13px;line-height:1.9;color:#9a938a}
.cover .meta{margin-top:16px;display:flex;gap:18px;font-size:11px;color:#8a8178;letter-spacing:.08em}
.cover .meta b{color:#c4937d;font-weight:600}
.tagcloud{margin-top:18px;display:flex;flex-wrap:wrap;gap:8px}
.tagcloud span{
  font-size:11px;padding:4px 11px;border:1px solid rgba(196,147,125,.3);
  border-radius:2px;color:#c9beb3;letter-spacing:.06em;
}

/* ── section 通用 ── */
.section{padding:30px 2px}
.section+.section{border-top:1px solid rgba(255,255,255,.06)}
.sec-head{font-size:10px;letter-spacing:.32em;color:#c4937d;text-transform:uppercase;margin-bottom:20px}

/* ── 独家专访 Q&A ── */
.qa{margin-bottom:22px}
.qa .q{
  font-family:"Times New Roman",serif;font-style:italic;
  font-size:15px;color:#e8e4dd;margin-bottom:9px;padding-left:26px;position:relative;
}
.qa .q::before{content:"Q";position:absolute;left:0;top:-2px;font-size:18px;font-weight:700;color:#c4937d;font-style:normal}
.qa .a{font-size:13.5px;line-height:1.95;color:#a89f95;padding-left:26px;position:relative}
.qa .a::before{content:"A";position:absolute;left:0;top:-1px;font-size:14px;font-weight:700;color:#5f5851;font-style:normal}

/* ── 财经热榜 ── */
.trend{display:flex;gap:14px;padding:13px 0;border-bottom:1px solid rgba(255,255,255,.05)}
.trend:last-child{border-bottom:none}
.trend .rank{font-family:"Times New Roman",serif;font-size:20px;font-weight:700;color:#3f3a34;min-width:26px}
.trend.hot .rank{color:#c4937d}
.trend .txt{font-size:13px;line-height:1.55;color:#c2b9af}
.trend .txt .badge{font-size:9px;color:#b83a52;border:1px solid rgba(184,58,82,.5);border-radius:2px;padding:1px 5px;margin-right:6px;letter-spacing:.05em;vertical-align:middle}

/* ── 深夜独白 pull-quote ── */
.pullquote{
  margin:8px 2px 0;padding:30px 24px;
  background:linear-gradient(160deg,rgba(196,147,125,.07),rgba(0,0,0,0));
  border-left:2px solid #c4937d;
}
.pullquote p{font-family:"Times New Roman","Songti SC",serif;font-size:19px;line-height:1.75;color:#ede8e1;font-style:italic}
.pullquote .by{margin-top:14px;font-size:10px;letter-spacing:.28em;color:#8a8178;text-transform:uppercase}

/* ── 页脚声明 ── */
.foot{padding:26px 2px 0;text-align:center}
.foot .line{width:40px;height:1px;background:rgba(196,147,125,.4);margin:0 auto 14px}
.foot p{font-size:11px;color:#6a635b;letter-spacing:.06em;line-height:1.7}
</style>
</head>
<body>
<div class="container">

  <div class="masthead">
    <span class="logo">Empire</span>
    <span class="issue">Issue 07 · Cover Story</span>
  </div>

  <div class="cover">
    <div class="kicker">The Untouchable</div>
    <h1>THE CEO<span class="thin">who never waits.</span></h1>
    <div class="zh">${name}</div>
    <p class="sub">顾氏集团总裁 · 万亿身家掌舵人<br>三十二岁 · 商界翻云覆雨的冷面君王</p>
    <div class="meta"><span>身价 <b>万亿</b></span><span>作息 <b>精确到分</b></span><span>软肋 <b>唯你一人</b></span></div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="section">
    <div class="sec-head">Exclusive Interview · 独家专访</div>
    <div class="qa">
      <div class="q">听说您的时间以分钟计价？</div>
      <div class="a">是。唯独有个人例外——为她，我能心甘情愿浪费一整个下午，还觉得赚了。</div>
    </div>
    <div class="qa">
      <div class="q">您如何表达在意？</div>
      <div class="a">把她的咖啡记成「少冰、一泵糖浆、燕麦奶」，把整层楼买下来只为她上班少走两步。我不懂浪漫，只懂把她要的都提前备好。</div>
    </div>
    <div class="qa">
      <div class="q">有什么是您掌控不了的？</div>
      <div class="a">她发来的一张午餐照片，能让我在董事会中途看手机。这种失控……我至今没学会如何写进报表。</div>
    </div>
  </div>

  <div class="section">
    <div class="sec-head">Today Trending · 顾北辰今日热榜</div>
    <div class="trend hot"><span class="rank">1</span><div class="txt"><span class="badge">爆</span>顾氏总裁取消飞纽约行程 疑因一句「我想你了」</div></div>
    <div class="trend hot"><span class="rank">2</span><div class="txt"><span class="badge">热</span>年度述职会上罕见走神 玻璃墙外那道身影是谁</div></div>
    <div class="trend"><span class="rank">3</span><div class="txt">冷面君王的手机备忘录 只有一个人的口味被精确记录</div></div>
    <div class="trend"><span class="rank">4</span><div class="txt">她身边的男同事为何接连被调岗 内部人士：不动声色</div></div>
    <div class="trend"><span class="rank">5</span><div class="txt">深夜车库 他把车内温度调到她喜欢的度数 却始终没敲那扇门</div></div>
  </div>

  <div class="pullquote">
    <p>“如果我什么都没有……你还在不在？”</p>
    <div class="by">— 深夜独处时，他收紧了搂着你的手臂</div>
  </div>

  <div class="foot">
    <div class="line"></div>
    <p>本刊角色设定纯属虚构 与现实无关</p>
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

