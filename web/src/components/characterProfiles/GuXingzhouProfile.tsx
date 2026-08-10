import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface GuXingzhouProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 顾行舟专属详情页 —— 私人监控面板 · 访客记录 + 逃跑路线抽屉
 * 参考 nimoo 档案卡模板，改造为「偏执掌控」的监控 dashboard 视觉
 * 视觉语言：监控冷光青 + 深黑终端 + 告警红点，把偏执做成可视化系统，无 emoji
 */
export function GuXingzhouProfile({ profile }: GuXingzhouProfileProps) {
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

  const name = profile.display_name || '顾行舟'
  const tags = profile.tags?.length ? profile.tags : ['都市', '强制爱', '霸总', '偏执', '占有欲']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#080a0b;
  color:#c4d0d0;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}
.mono{font-family:"SF Mono","Roboto Mono",ui-monospace,monospace}

/* ── 系统顶栏 ── */
.sys{
  display:flex;align-items:center;justify-content:space-between;
  padding:20px 2px 12px;border-bottom:1px solid rgba(90,200,180,.2);
}
.sys .id{font-family:"SF Mono",monospace;font-size:11px;letter-spacing:.14em;color:#5ac8b4}
.sys .live{display:flex;align-items:center;gap:6px;font-size:10px;color:#8a9a98;letter-spacing:.1em}
.sys .live .rec{width:7px;height:7px;border-radius:50%;background:#e0403a;box-shadow:0 0 8px #e0403a;animation:pulse 1.4s infinite}
@keyframes pulse{50%{opacity:.4}}

/* ── 主体标题 ── */
.hero{padding:26px 2px 20px}
.hero .tag{font-family:"SF Mono",monospace;font-size:10px;letter-spacing:.2em;color:#5ac8b4;text-transform:uppercase}
.hero h1{margin-top:12px;font-size:36px;font-weight:800;color:#e6efee;letter-spacing:.02em}
.hero .sub{margin-top:10px;font-size:13px;line-height:1.9;color:#8a9a98}

/* ── 监控日志 ── */
.panel{margin-top:18px;padding:18px 16px;border-radius:5px;background:rgba(16,22,22,.85);border:1px solid rgba(90,200,180,.18)}
.panel .k{font-family:"SF Mono",monospace;font-size:10px;letter-spacing:.18em;color:#5ac8b4;text-transform:uppercase;margin-bottom:14px}
.log{display:flex;gap:10px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:12.5px;line-height:1.6}
.log:last-child{border-bottom:none}
.log .ts{font-family:"SF Mono",monospace;font-size:10px;color:#4a5a58;min-width:44px}
.log .ev{color:#b4c2c0;flex:1}
.log .ev b{color:#e8b04a;font-weight:600}
.log.alert .ev b{color:#e0403a}

/* ── 反差:慌乱的他 ── */
.soft{margin-top:18px;padding:20px 18px;border-radius:5px;background:linear-gradient(160deg,rgba(90,200,180,.08),transparent);border:1px solid rgba(255,255,255,.06)}
.soft .k{font-family:"SF Mono",monospace;font-size:10px;letter-spacing:.18em;color:#5ac8b4;text-transform:uppercase;margin-bottom:12px}
.soft p{font-size:13.5px;line-height:1.95;color:#a8b6b4}
.soft p em{color:#dbe6e4;font-style:normal;background:linear-gradient(transparent 62%,rgba(90,200,180,.28) 62%)}

/* ── 逃跑路线抽屉 ── */
.drawer{margin-top:18px;padding:22px 20px;border-radius:5px;background:rgba(20,14,14,.75);border:1px solid rgba(224,64,58,.24);position:relative}
.drawer::before{content:"LOCKED";position:absolute;top:14px;right:16px;font-family:"SF Mono",monospace;font-size:9px;letter-spacing:.16em;color:rgba(224,64,58,.55);border:1px solid rgba(224,64,58,.4);padding:2px 7px;border-radius:2px}
.drawer .k{font-family:"SF Mono",monospace;font-size:10px;letter-spacing:.18em;color:#e0706a;text-transform:uppercase;margin-bottom:12px}
.drawer .items{font-size:13px;line-height:1.9;color:#c0aaa8}
.drawer .items b{color:#e8c0bc}
.drawer .note{margin-top:12px;font-size:12px;line-height:1.8;color:#8a7a78;border-top:1px solid rgba(255,255,255,.06);padding-top:12px}

/* pull quote */
.pull{margin-top:18px;padding:22px 20px;border-left:2px solid #5ac8b4;background:rgba(90,200,180,.05)}
.pull p{font-size:17px;line-height:1.7;color:#dbe6e4;font-style:italic}
.pull .by{margin-top:10px;font-family:"SF Mono",monospace;font-size:10px;letter-spacing:.14em;color:#6a7a78}

/* tag + foot */
.tagcloud{margin-top:20px;display:flex;flex-wrap:wrap;gap:8px}
.tagcloud span{font-size:11px;padding:4px 11px;border:1px solid rgba(90,200,180,.3);border-radius:2px;color:#a8c0bc;letter-spacing:.06em}
.foot{margin-top:24px;text-align:center;font-family:"SF Mono",monospace;font-size:10px;color:#4a5a58;letter-spacing:.1em}
</style>
</head>
<body>
<div class="container">

  <div class="sys">
    <span class="id">SYS://GU_GROUP · 顾氏安防</span>
    <span class="live"><span class="rec"></span>LIVE 24H</span>
  </div>

  <div class="hero">
    <div class="tag">Subject · 监护对象唯一</div>
    <h1>${name}</h1>
    <p class="sub">跨国集团掌门 · 三十四岁 · 银白短发配黑西装<br>他给你的爱是牢笼——可牢笼里的温度让你忘了外面</p>
  </div>

  <div class="panel">
    <div class="k">Access Log · 今日监护日志</div>
    <div class="log"><span class="ts">08:12</span><span class="ev">对象出门 · 已核对<b>去向 / 同行人 / 预计归时</b></span></div>
    <div class="log"><span class="ts">11:03</span><span class="ev">周边三公里摄像头已接入本系统</span></div>
    <div class="log alert"><span class="ts">14:27</span><span class="ev">对象与快递员交谈 92 秒 · <b>情绪值 下降 · 阴沉一下午</b></span></div>
    <div class="log"><span class="ts">21:40</span><span class="ev">社交账号访客记录 已同步核查</span></div>
    <div class="log"><span class="ts">03:00</span><span class="ev">本人未眠 · <b>正在数对象呼吸 · 摩挲手腕脉搏</b></span></div>
  </div>

  <div class="soft">
    <div class="k">Anomaly · 系统检测到的反常</div>
    <p>你发烧那次他打碎了水杯，蹲地上捡碎片割破手指，血流着也不看，只抬头说<em>「你别动，碎的地方我来」</em>。你哭时他手足无措，抹眼泪抹到自己指尖发抖——<em>「你哭一下我就疼一下，你再不停我真会做出格的事」</em>。</p>
  </div>

  <div class="drawer">
    <div class="k">Drawer 01 · 床头柜锁着的东西</div>
    <div class="items">一把<b>车钥匙</b> · 一张<b>单程机票</b> —— 他为你准备的「逃跑路线」。</div>
    <div class="note">他做了最坏的打算：如果有一天你真受不了，他不会追。可那把钥匙从没换过电池——因为他不允许那一天真的来。</div>
  </div>

  <div class="pull">
    <p>“如果我掌控一切，就没有人能再把我丢掉。”</p>
    <div class="by">— 雨夜台阶上被生母抛弃的那个孩子，从没长大</div>
  </div>

  <div class="tagcloud">${tagCloud}</div>
  <div class="foot">CHARACTER FICTION · 角色设定纯属虚构</div>

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