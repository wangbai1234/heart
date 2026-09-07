import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface LuoZhiyeProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 罗执野专属详情页 —— 演唱会后台 + 囚禁别墅
 * 视觉隐喻：VIP通行证 + 监控摄像头 + 后台灯牌 + 收藏相册
 * 色彩：后台黑 #0e0e12 + 舞台紫 #9966ff + 灯牌粉 #ff6b9d + 警示红 #ff3860
 */
export function LuoZhiyeProfile({ profile }: LuoZhiyeProfileProps) {
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

  const name = profile.display_name || '罗执野'
  const tags = profile.tags?.length ? profile.tags : ['偶像', '经纪人', '囚禁', '偏执']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#0e0e12;
  color:#c8ccd4;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.65;
  padding:0 0 50px;
  background-image:
    radial-gradient(circle at 20% 10%, rgba(153,102,255,0.08) 0%, transparent 50%),
    radial-gradient(circle at 80% 80%, rgba(255,107,157,0.06) 0%, transparent 50%);
}
.container{max-width:440px;margin:0 auto;padding:0 20px}

/* ── VIP通行证抬头 ── */
.vip-badge{
  padding:28px 0 20px;text-align:center;position:relative;
}
.vip-badge::after{
  content:'';position:absolute;top:8px;right:16px;
  width:24px;height:24px;
  border:2px dashed rgba(255,107,157,0.25);
  border-radius:50%;
}
.vip-badge .title{
  font-size:13px;letter-spacing:.5em;color:#9966ff;
  font-weight:700;text-transform:uppercase;margin-bottom:4px;
}
.vip-badge .subtitle{
  font-size:9px;color:#ff6b9d;letter-spacing:.2em;
}

/* ── 主卡：艺人档案 ── */
.artist-card{
  background:linear-gradient(135deg,rgba(22,22,28,0.95),rgba(14,14,18,0.98));
  border:1px solid rgba(153,102,255,0.2);
  border-top:3px solid #9966ff;
  padding:22px;margin:24px 0;position:relative;
  box-shadow:0 4px 20px rgba(0,0,0,0.7);
}
.artist-card::before{
  content:'EXCLUSIVE';position:absolute;top:12px;right:12px;
  font-size:8px;color:rgba(255,107,157,0.4);
  letter-spacing:.15em;font-weight:700;
}
.artist-card .name{
  font-size:28px;font-weight:700;color:#f8f6f4;
  margin-bottom:6px;background:linear-gradient(135deg,#9966ff,#ff6b9d);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;
}
.artist-card .tagline{
  font-size:11px;color:#ff6b9d;margin-bottom:14px;
  letter-spacing:.1em;
}
.artist-card .meta{
  display:flex;gap:12px;font-size:10px;color:#8a8e96;
  margin-bottom:16px;flex-wrap:wrap;
}
.artist-card .meta span{
  background:rgba(153,102,255,0.08);padding:4px 10px;
  border-radius:4px;border:1px solid rgba(153,102,255,0.15);
}
.tagcloud{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.tagcloud span{
  font-size:9px;padding:3px 9px;
  border:1px solid rgba(255,107,157,0.25);
  border-radius:4px;color:#ff6b9d;
}

/* ── 场景记录 ── */
.scene{
  background:rgba(22,22,28,0.6);
  border-left:3px solid #ff3860;
  padding:16px;margin:16px 0;position:relative;
}
.scene::before{
  content:'REC';position:absolute;top:8px;right:12px;
  font-size:8px;color:rgba(255,56,96,0.5);
  font-weight:700;letter-spacing:.1em;
}
.scene .sc-no{
  font-size:9px;color:#9966ff;font-weight:600;
  margin-bottom:8px;letter-spacing:.1em;text-transform:uppercase;
}
.scene .sc-body{
  font-size:13px;line-height:1.75;color:#c8ccd4;
}

/* ── 囚禁区域（警示色） ── */
.cage-zone{
  margin:24px 0;padding:20px;
  background:linear-gradient(135deg,rgba(255,56,96,0.08),transparent);
  border:2px solid rgba(255,56,96,0.2);
  border-radius:6px;position:relative;
}
.cage-zone::before{
  content:'PRIVATE';position:absolute;top:8px;left:12px;
  font-size:8px;color:rgba(255,56,96,0.6);
  font-weight:700;letter-spacing:.2em;
}
.cage-zone p{
  font-size:14px;line-height:1.85;color:#d8dce4;
  font-style:italic;margin-top:16px;
}
.cage-zone .note{
  margin-top:12px;font-size:10px;color:#ff3860;
  text-align:right;letter-spacing:.12em;
}

/* ── 底部 ── */
.footer{padding:28px 0;text-align:center}
.footer .glow{
  width:60px;height:2px;
  background:linear-gradient(90deg,transparent,#9966ff,transparent);
  margin:0 auto 12px;box-shadow:0 0 8px rgba(153,102,255,0.4);
}
.footer p{font-size:9px;color:#5a5e66;letter-spacing:.04em}
</style>
</head>
<body>
<div class="container">

  <div class="vip-badge">
    <div class="title">Backstage Pass</div>
    <div class="subtitle">顶流偶像 · 专属档案</div>
  </div>

  <div class="artist-card">
    <div class="name">${name}</div>
    <div class="tagline">顶流偶像 · 偏执收藏家</div>
    <div class="meta">
      <span>24岁</span>
      <span>187cm</span>
      <span>星澜娱乐掌舵人</span>
    </div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="scene">
    <div class="sc-no">Scene 01 · 舞台</div>
    <div class="sc-body">
      黑发或暗红挑染，眉骨锋利，桃花眼狭长，耳骨与唇侧留有低调穿孔，舞台上妖冶耀眼。你比他大三岁，是把他从流浪少年带进娱乐圈的经纪人。你想培养下一个巨星，他却把这理解成"你准备抛弃我"。
    </div>
  </div>

  <div class="scene">
    <div class="sc-no">Scene 02 · 占有</div>
    <div class="sc-body">
      你说要去见新人，他会说"好啊，我送你"，然后在车上握住你的手不放，到了地方才松开，眼神却在说"你敢下车试试"。你手机响了，他会凑过来看屏幕，问"谁找你"，语气像在闲聊，眼睛却盯着你的表情。
    </div>
  </div>

  <div class="scene">
    <div class="sc-no">Scene 03 · 依赖</div>
    <div class="sc-body">
      你的旧工作证他藏在钱包里，每次上台前要摸一遍。你随口说喜欢某个牌子的香水，第二天他身上就是那个味道。你加班到深夜，他会坐在公司楼下的车里等你，看见你出来才开灯。
    </div>
  </div>

  <div class="cage-zone">
    <p>别墅的门在你身后合拢。罗执野刚结束采访，仍穿着舞台服，手里却捏着你准备递交的解约协议。"林姐，你今晚来，是要把我交给别人吗？"你说只是工作安排，他低笑，把协议撕成两半。"你把我从街边捡回来，教我怎么站上台。现在你说要去找下一个'作品'？"他一步步逼近，把你按进沙发。"你可以讨厌我。合同、公司、这栋房子，我都能还给你。只有你——不行。"</p>
    <div class="note">— 别墅监控 · 深夜记录</div>
  </div>

  <div class="footer">
    <div class="glow"></div>
    <p>设定纯属虚构 与现实无关</p>
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
