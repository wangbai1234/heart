import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface JiangYuezeProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 江月泽专属详情页 —— 三年未发送的对话框 + 悔意草稿箱 + 树干信物
 * 参考 nimoo 论坛/聊天记录质感，改造为「追妻火葬场」独有的 IM 草稿视觉
 * 视觉语言：深夜手机冷光 · 银白(呼应银发) + 石墨蓝 + 未读红点，克制无 emoji
 */
export function JiangYuezeProfile({ profile }: JiangYuezeProfileProps) {
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

  const name = profile.display_name || '江月泽'
  const tags = profile.tags?.length ? profile.tags : ['都市', 'NTR', '前任', '追妻火葬场', '深情']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#0a0c10;
  color:#cbd2da;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}

/* ── 聊天窗顶栏 ── */
.imhead{
  display:flex;align-items:center;gap:12px;
  padding:20px 4px 16px;border-bottom:1px solid rgba(255,255,255,.06);
}
.imhead .av{width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#2a3038,#1a1e24);border:1px solid rgba(160,175,195,.25)}
.imhead .who{flex:1}
.imhead .who .n{font-size:14px;color:#e2e8f0;font-weight:600}
.imhead .who .s{font-size:11px;color:#5c6672;margin-top:2px}
.imhead .dot{width:7px;height:7px;border-radius:50%;background:#3a424d}

/* ── 会话日期 ── */
.daysep{text-align:center;font-size:10px;color:#4a525c;letter-spacing:.1em;margin:20px 0 12px}

/* ── 气泡 ── */
.msg{display:flex;margin-bottom:12px}
.msg.out{justify-content:flex-end}
.bubble{max-width:80%;padding:11px 14px;font-size:13.5px;line-height:1.7;border-radius:14px}
.msg.in .bubble{background:rgba(38,44,52,.9);color:#c4ccd6;border-bottom-left-radius:4px}
.msg.out .bubble{background:linear-gradient(135deg,#33607e,#2a4d66);color:#e6eef5;border-bottom-right-radius:4px}
.msg .time{align-self:flex-end;font-size:9px;color:#454d57;margin:0 6px}

/* ── 未发送草稿箱 ── */
.draft{
  margin:22px 0 0;padding:20px 18px;border-radius:12px;
  background:rgba(20,24,30,.8);border:1px dashed rgba(160,175,195,.22);
}
.draft .h{font-size:11px;letter-spacing:.24em;color:#7c8896;text-transform:uppercase;margin-bottom:14px}
.draft .line{
  font-size:13px;line-height:1.9;color:#8b95a1;padding:9px 0;
  border-bottom:1px solid rgba(255,255,255,.05);position:relative;padding-left:16px;
}
.draft .line:last-child{border-bottom:none}
.draft .line::before{content:"|";position:absolute;left:2px;color:#33607e;animation:blink 1.2s step-end infinite}
@keyframes blink{50%{opacity:0}}
.draft .line b{color:#c4ccd6;font-weight:500}
.draft .status{margin-top:14px;font-size:11px;color:#5a636e;text-align:center;letter-spacing:.06em}

/* ── 便利店守望卡 ── */
.watch{
  margin-top:22px;padding:20px 18px;border-radius:12px;
  background:linear-gradient(160deg,rgba(51,96,126,.12),transparent);
  border:1px solid rgba(255,255,255,.06);
}
.watch .h{font-size:11px;letter-spacing:.24em;color:#7c8896;text-transform:uppercase;margin-bottom:12px}
.watch p{font-size:13.5px;line-height:1.95;color:#a8b2be}
.watch p em{color:#d6dee8;font-style:normal;background:linear-gradient(transparent 62%,rgba(51,96,126,.35) 62%)}

/* ── 信物：树干 ── */
.relic{
  margin-top:22px;padding:22px 20px;border-radius:12px;text-align:center;
  background:rgba(18,15,13,.7);border:1px solid rgba(150,120,90,.2);
}
.relic .h{font-size:11px;letter-spacing:.24em;color:#9a8468;text-transform:uppercase;margin-bottom:12px}
.relic .carve{font-family:"Songti SC","STSong",serif;font-size:17px;color:#d8c4a8;letter-spacing:.1em;line-height:1.8}
.relic .note{margin-top:12px;font-size:12px;line-height:1.8;color:#7d7468}

/* tag + foot */
.tagcloud{margin-top:22px;display:flex;flex-wrap:wrap;gap:8px}
.tagcloud span{font-size:11px;padding:4px 11px;border:1px solid rgba(160,175,195,.28);border-radius:2px;color:#aeb8c4;letter-spacing:.06em}
.foot{margin-top:24px;text-align:center;font-size:11px;color:#4a525c;letter-spacing:.06em}
</style>
</head>
<body>
<div class="container">

  <div class="imhead">
    <div class="av"></div>
    <div class="who"><div class="n">${name}</div><div class="s">最后上线 三年前 · 未读消息 0</div></div>
    <div class="dot"></div>
  </div>

  <div class="daysep">三年前 · 那天下午</div>
  <div class="msg in"><div class="bubble">那条短信不是你想的那样，我可以解释</div></div>
  <div class="msg out"><span class="time">16:42</span><div class="bubble">不用了。我们到此为止。</div></div>
  <div class="daysep">此后 · 已读不回的对话框亮了整整三年</div>

  <div class="draft">
    <div class="h">Unsent · 未发送草稿</div>
    <div class="line">在第七个国家的凌晨，他打下：<b>「你那边天亮了吗」</b>——删了。</div>
    <div class="line">戒酒第 90 天复喝那晚：<b>「我错了。是我太骄傲。」</b>——删了。</div>
    <div class="line">听说你那三天哭到住院后：<b>「对不起，我不知道你打过我电话没」</b>——删了。</div>
    <div class="status">光标闪了整夜 · 一个字也没发出去</div>
  </div>

  <div class="watch">
    <div class="h">Now · 他回来了</div>
    <p>他不再进那家便利店，只站在门口，<em>确认你今天的便当里有没有那道你不爱吃的醋溜菜</em>。你新男友出现时他后退一步，笑得像在割肉：「他对你好吗？好就行。」可你深夜独行时，<em>身后二十米，他的车灯一直亮着</em>。</p>
  </div>

  <div class="relic">
    <div class="h">Relic · 那截买回来的树干</div>
    <div class="carve">此生 唯你 死不放手</div>
    <div class="note">走之前他在你家楼下的树上刻了字。三年后树被砍了——他花了很多钱把那段树干买回来，放在公寓角落。</div>
  </div>

  <div class="tagcloud">${tagCloud}</div>
  <div class="foot">角色设定纯属虚构 与现实无关</div>

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