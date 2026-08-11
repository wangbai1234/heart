import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface QingyuBandProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 青羽乐队专属详情页 —— 演出曲目单 / SETLIST
 * 视觉隐喻：Live 演出海报 · 五人乐队名册 · 一张手写曲目单
 * 色彩：舞台冷调 #8FA5B8 + 深夜 #15181f + 暖聚光 #E0A96D
 */
export function QingyuBandProfile({ profile }: QingyuBandProfileProps) {
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

  const name = profile.display_name || '青羽乐队'
  const tags = profile.tags?.length ? profile.tags : ['群像', '校园', '全性向', '模拟器', '高自由']
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
    radial-gradient(100% 55% at 50% 0,rgba(224,169,109,0.12),transparent 55%),
    linear-gradient(180deg,#15181f 0%,#0a0d12 100%);
  color:#c6cdd6;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.75;padding:0 0 46px;
}
.container{max-width:440px;margin:0 auto;padding:0 20px}
/* 演出海报头 */
.header{padding:28px 2px 12px;text-align:center;position:relative}
.header .live{
  display:inline-block;font-size:9px;letter-spacing:.4em;color:#E0A96D;
  border:1px solid rgba(224,169,109,0.5);border-radius:2px;padding:3px 12px;text-transform:uppercase;
}
.header .zh{
  font-family:"Songti SC","Noto Serif SC",serif;font-size:30px;font-weight:600;
  color:#e6ebf0;margin-top:14px;letter-spacing:.2em;
}
.header .sub{font-size:11px;color:#8792a0;letter-spacing:.14em;margin-top:8px}
/* 均衡器条 */
.eq{display:flex;justify-content:center;align-items:flex-end;gap:4px;height:26px;margin:18px 0}
.eq i{width:3px;background:linear-gradient(180deg,#8FA5B8,rgba(143,165,184,0.2));border-radius:2px}
.eq i:nth-child(1){height:40%}.eq i:nth-child(2){height:75%}.eq i:nth-child(3){height:55%}
.eq i:nth-child(4){height:100%}.eq i:nth-child(5){height:65%}.eq i:nth-child(6){height:85%}
.eq i:nth-child(7){height:45%}.eq i:nth-child(8){height:70%}.eq i:nth-child(9){height:35%}
.tagcloud{display:flex;flex-wrap:wrap;gap:7px;justify-content:center;margin-bottom:6px}
.tagcloud span{
  font-size:10px;padding:4px 11px;background:rgba(143,165,184,0.1);
  border:1px solid rgba(143,165,184,0.28);border-radius:20px;color:#9aa6b3;letter-spacing:.06em;
}
.intro{
  margin:18px 0;padding:16px 18px;
  background:linear-gradient(135deg,rgba(143,165,184,0.08),transparent);
  border-left:2px solid #8FA5B8;border-radius:2px;
  font-size:13px;line-height:1.9;color:#b2bbc5;
}
.sec-label{
  font-size:10px;color:#E0A96D;letter-spacing:.3em;text-transform:uppercase;
  margin:24px 2px 14px;font-weight:600;
}
/* ── 成员名册（曲目单行）── */
.track{
  display:flex;align-items:flex-start;gap:13px;padding:14px 4px;
  border-bottom:1px solid rgba(143,165,184,0.14);
}
.track .no{
  font-family:"Times New Roman",serif;font-size:15px;font-style:italic;
  color:#E0A96D;min-width:24px;padding-top:1px;
}
.track .body{flex:1}
.track .head{display:flex;align-items:baseline;gap:8px;margin-bottom:3px}
.track .inst{font-size:14px;font-weight:600;color:#e2e7ec}
.track .tone{font-size:11px;color:#8FA5B8;letter-spacing:.08em}
.track .line{font-size:12px;line-height:1.7;color:#96a1ac}
.note-card{
  margin:22px 2px 0;padding:18px 16px;
  background:linear-gradient(135deg,rgba(224,169,109,0.08),transparent);
  border:1px solid rgba(224,169,109,0.2);border-radius:4px;
}
.note-card p{
  font-family:"Songti SC","Noto Serif SC",serif;font-size:14px;line-height:1.95;
  color:#c6ccd4;font-style:italic;
}
.note-card .by{margin-top:12px;font-size:10px;color:#6c7783;letter-spacing:.2em}
.footer{padding:26px 2px 0;text-align:center}
.footer .ln{width:34px;height:1px;background:rgba(143,165,184,0.45);margin:0 auto 12px}
.footer p{font-size:10px;color:#5c6672;letter-spacing:.06em}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="live">Live Setlist</div>
    <div class="zh">${name}</div>
    <div class="sub">校园乐队群像 · 五种心动 · 多线可攻略</div>
  </div>

  <div class="eq"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
  <div class="tagcloud">${tagCloud}</div>

  <div class="intro">「青羽」是一支校园乐队，五名成员性格迥异。你以新任经纪人/成员的身份加入，与每个人都有独立的相处线。剧情与攻略对象，全由你选。</div>

  <div class="sec-label">Lineup · 今夜阵容</div>

  <div class="track">
    <div class="no">01</div>
    <div class="body">
      <div class="head"><span class="inst">主唱</span><span class="tone">清冷</span></div>
      <div class="line">只淡淡扫你一眼就低头调话筒。台上万丈光芒，台下沉默寡言——可以陪他练到深夜，听他没说出口的旋律。</div>
    </div>
  </div>
  <div class="track">
    <div class="no">02</div>
    <div class="body">
      <div class="head"><span class="inst">吉他手</span><span class="tone">痞帅</span></div>
      <div class="line">抱着吉他先咧嘴笑，用琴头朝你一挑，把椅子踢到你面前起哄。眼里的光，藏着不肯说的认真。</div>
    </div>
  </div>
  <div class="track">
    <div class="no">03</div>
    <div class="body">
      <div class="head"><span class="inst">键盘手</span><span class="tone">温柔</span></div>
      <div class="line">对你温柔笑了笑。安静地坐在琴键后，是最愿意听你倾诉、也把心事悄悄写进曲子的人。</div>
    </div>
  </div>
  <div class="track">
    <div class="no">04</div>
    <div class="body">
      <div class="head"><span class="inst">鼓手</span><span class="tone">毒舌</span></div>
      <div class="line">在后面敲了个促狭的鼓点。嘴上没个正经，跟你斗嘴斗得欢，鼓点却总在你需要时稳稳接住。</div>
    </div>
  </div>
  <div class="track">
    <div class="no">05</div>
    <div class="body">
      <div class="head"><span class="inst">贝斯手</span><span class="tone">笑眯眯</span></div>
      <div class="line">小声说了句欢迎。总是笑眯眯地站在角落，稳住整支乐队的低音，也悄悄把你当成了唯一的树洞。</div>
    </div>
  </div>

  <div class="note-card">
    <p>五个因音乐聚在一起的少年，在青春的十字路口各自迷茫。你的加入像一段新的旋律——这支乐队的故事往哪走、谁的独奏先为你响起，取决于你的每一次选择。</p>
    <div class="by">— 排练厅手记 · 某个午后</div>
  </div>

  <div class="footer">
    <div class="ln"></div>
    <p>角色设定纯属虚构 与现实无关</p>
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