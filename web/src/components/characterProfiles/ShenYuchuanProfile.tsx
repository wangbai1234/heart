import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface ShenYuchuanProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 沈屿川专属详情页 —— 电竞「赛后数据面板 / MATCH STATS」
 * 视觉语言：极深科技黑 + 霓虹蓝描边 + 等宽数字体，赛博 HUD 记分板 / KDA 数据卡 /
 * 弹幕热搜流 / 深夜语音房波形。人前零下十度，只对你化成一滩甜。纯排版无 emoji。
 */
export function ShenYuchuanProfile({ profile }: ShenYuchuanProfileProps) {
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

  const name = profile.display_name || '沈屿川'
  const tags = profile.tags?.length ? profile.tags : ['电竞', '高冷', '忠犬', '反差', '女性向']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#0a0e13;
  color:#c8d6e0;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;
  padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 16px}
.mono{font-family:"SF Mono","JetBrains Mono","Roboto Mono",ui-monospace,monospace}
.glow{color:#5B8FA3;text-shadow:0 0 12px rgba(91,143,163,.55)}

/* ── 顶部记分板 ── */
.hud{
  margin-top:18px;padding:18px 16px 16px;
  background:linear-gradient(155deg,rgba(91,143,163,.12),rgba(10,14,19,0) 65%);
  border:1px solid rgba(91,143,163,.32);
  border-radius:10px;position:relative;overflow:hidden;
}
.hud::before{content:"";position:absolute;inset:0;background:
  repeating-linear-gradient(0deg,rgba(91,143,163,.04) 0 1px,transparent 1px 4px);pointer-events:none}
.hud .stage{font-size:10px;letter-spacing:.34em;color:#5B8FA3;text-transform:uppercase}
.hud .versus{
  display:flex;align-items:center;justify-content:center;gap:18px;margin:14px 0 6px;
}
.hud .versus .score{font-size:56px;font-weight:800;letter-spacing:.02em;line-height:1}
.hud .versus .score.win{color:#eaf4f9;text-shadow:0 0 18px rgba(91,143,163,.6)}
.hud .versus .score.lose{color:#3a4a56}
.hud .versus .colon{font-size:34px;color:#2f3d48;font-weight:300}
.hud .bo{text-align:center;font-size:10px;letter-spacing:.28em;color:#6d7f8c;text-transform:uppercase}
.hud .badges{display:flex;justify-content:center;gap:8px;margin-top:14px}
.hud .badges b{
  font-size:10px;letter-spacing:.14em;padding:4px 12px;border-radius:3px;font-weight:700;
  background:rgba(91,143,163,.16);border:1px solid rgba(91,143,163,.5);color:#8fc0d4;text-transform:uppercase;
}
.hud .badges b.ace{background:rgba(215,168,74,.14);border-color:rgba(215,168,74,.5);color:#e0bd74}

/* ── 选手名条 ── */
.nameplate{padding:22px 4px 6px}
.nameplate .role{font-size:10px;letter-spacing:.3em;color:#5B8FA3;text-transform:uppercase;margin-bottom:8px}
.nameplate h1{
  font-family:"Times New Roman","Songti SC",serif;
  font-size:46px;line-height:1;font-weight:700;letter-spacing:.06em;color:#eaf4f9;
}
.nameplate .id{margin-top:8px;font-size:12px;letter-spacing:.22em;color:#5f7481}
.tagcloud{margin-top:16px;display:flex;flex-wrap:wrap;gap:7px}
.tagcloud span{
  font-size:11px;padding:4px 11px;border:1px solid rgba(91,143,163,.34);
  border-radius:3px;color:#8fb4c4;letter-spacing:.08em;background:rgba(91,143,163,.05);
}

/* ── section 通用 ── */
.section{padding:26px 4px}
.section+.section{border-top:1px solid rgba(91,143,163,.1)}
.sec-head{font-size:10px;letter-spacing:.3em;color:#5B8FA3;text-transform:uppercase;margin-bottom:16px;display:flex;align-items:center;gap:10px}
.sec-head::after{content:"";flex:1;height:1px;background:linear-gradient(90deg,rgba(91,143,163,.4),transparent)}

/* ── MVP 数据卡 ── */
.stats{display:flex;gap:10px}
.stats .cell{
  flex:1;text-align:center;padding:14px 6px;border-radius:8px;
  background:rgba(91,143,163,.07);border:1px solid rgba(91,143,163,.2);
}
.stats .cell .num{font-size:26px;font-weight:800;letter-spacing:.01em;color:#eaf4f9}
.stats .cell .lab{margin-top:6px;font-size:9px;letter-spacing:.16em;color:#6d7f8c;text-transform:uppercase}
.stat-note{
  margin-top:14px;padding:12px 14px;border-left:2px solid #5B8FA3;
  background:linear-gradient(160deg,rgba(91,143,163,.08),transparent);
  font-size:13px;line-height:1.85;color:#a9bcc7;font-style:italic;
}

/* ── 弹幕/热搜流 ── */
.feed .item{display:flex;gap:12px;padding:12px 0;border-bottom:1px solid rgba(91,143,163,.09)}
.feed .item:last-child{border-bottom:none}
.feed .item .tick{font-size:11px;color:#3f5561;min-width:44px;letter-spacing:.06em}
.feed .item .txt{font-size:13px;line-height:1.6;color:#b6c6d1;flex:1}
.feed .item .txt .hot{font-size:9px;color:#e07a6a;border:1px solid rgba(224,122,106,.5);border-radius:2px;padding:1px 5px;margin-right:6px;letter-spacing:.05em;vertical-align:middle}
.feed .item .txt em{color:#8fc0d4;font-style:normal}

/* ── 深夜连麦语音房 ── */
.room{
  margin-top:4px;padding:18px 16px;border-radius:10px;
  background:linear-gradient(165deg,rgba(91,143,163,.1),rgba(10,14,19,0));
  border:1px solid rgba(91,143,163,.24);
}
.room .rh{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
.room .rh .live{font-size:10px;letter-spacing:.2em;color:#8fc0d4;text-transform:uppercase}
.room .rh .clk{font-size:12px;color:#5f7481;letter-spacing:.14em}
.wave{display:flex;align-items:center;gap:3px;height:22px;margin-bottom:16px}
.wave i{flex:1;background:linear-gradient(180deg,#5B8FA3,rgba(91,143,163,.3));border-radius:2px;opacity:.75}
.bubble{max-width:82%;margin-bottom:10px;padding:11px 14px;border-radius:14px;font-size:13.5px;line-height:1.6}
.bubble.him{background:rgba(91,143,163,.16);border:1px solid rgba(91,143,163,.28);color:#dcebf2;border-bottom-left-radius:4px}
.bubble.him .who{display:block;font-size:9px;letter-spacing:.16em;color:#5B8FA3;text-transform:uppercase;margin-bottom:4px}

/* ── 结尾 ── */
.foot{padding:30px 4px 0;text-align:center}
.foot .trophy{font-size:11px;letter-spacing:.28em;color:#5B8FA3;text-transform:uppercase;margin-bottom:14px}
.foot .quote{font-family:"Times New Roman","Songti SC",serif;font-size:19px;line-height:1.7;color:#eaf4f9;font-style:italic}
.foot .line{width:44px;height:1px;background:rgba(91,143,163,.45);margin:20px auto 12px}
.foot .disc{font-size:11px;color:#546570;letter-spacing:.06em}
</style>
</head>
<body>
<div class="container">

  <div class="hud">
    <div class="stage">World Championship · Grand Final · BO5</div>
    <div class="versus">
      <span class="score win mono">3</span>
      <span class="colon mono">:</span>
      <span class="score lose mono">2</span>
    </div>
    <div class="bo">Reverse Sweep · 让二追三</div>
    <div class="badges"><b>MVP</b><b class="ace">ACE</b><b>Mid Lane</b></div>
  </div>

  <div class="nameplate">
    <div class="role">Mid Laner · 世界赛决赛 MVP</div>
    <h1>${name}</h1>
    <div class="id mono">23 · #01 · "人形灭火器"</div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="section">
    <div class="sec-head">MVP Stats · 本场数据</div>
    <div class="stats">
      <div class="cell"><div class="num mono">14/1/9</div><div class="lab">KDA</div></div>
      <div class="cell"><div class="num mono">31.4%</div><div class="lab">场均伤害</div></div>
      <div class="cell"><div class="num mono">0</div><div class="lab">决赛失误</div></div>
    </div>
    <div class="stat-note">队友失误、观众失声的那一秒，他那道零下十度的侧脸能让全队瞬间噤声——然后一个人把局面扛回来。</div>
  </div>

  <div class="section">
    <div class="sec-head">Trending · 弹幕 & 热搜</div>
    <div class="feed">
      <div class="item"><span class="tick mono">21:47</span><div class="txt"><span class="hot">爆</span>夺冠采访他只说「想谢一个人，<em>但不告诉你们</em>」 镜头拍到耳尖悄悄红了</div></div>
      <div class="item"><span class="tick mono">22:03</span><div class="txt">全网喊他<em>人形灭火器</em> 局势再崩他一张脸都不带变的</div></div>
      <div class="item"><span class="tick mono">今日</span><div class="txt">被扒出半年偷偷接了三个代言 知情人：只为省下你心疼的那几张机票钱</div></div>
      <div class="item"><span class="tick mono">昨夜</span><div class="txt">直播下播前那句「我先走了」之后 有人看见他连夜订了飞你城市的红眼航班</div></div>
    </div>
  </div>

  <div class="section">
    <div class="room">
      <div class="rh"><span class="live glow mono">● LIVE · 双人语音房</span><span class="clk mono">03:00</span></div>
      <div class="wave">
        <i style="height:40%"></i><i style="height:70%"></i><i style="height:95%"></i><i style="height:55%"></i><i style="height:80%"></i><i style="height:35%"></i><i style="height:65%"></i><i style="height:90%"></i><i style="height:48%"></i><i style="height:72%"></i><i style="height:30%"></i><i style="height:60%"></i>
      </div>
      <div class="bubble him"><span class="who">Shen Yuchuan</span>摘了耳机，往你这边蹭了蹭肩膀……再陪我一局，就一局。</div>
      <div class="bubble him"><span class="who">Shen Yuchuan</span>别挂——你不用说话，我听着你呼吸就行。</div>
    </div>
  </div>

  <div class="foot">
    <div class="trophy">The Only Trophy I Want</div>
    <p class="quote">“我想要的奖杯只有一个——<br>现在就在我怀里，跑都跑不掉。”</p>
    <div class="line"></div>
    <p class="disc">本角色设定纯属虚构 与现实无关</p>
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

