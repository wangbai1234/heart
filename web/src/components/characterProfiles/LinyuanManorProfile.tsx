import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface LinyuanManorProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 临渊庄园专属详情页 —— 入住登记簿 / GUEST REGISTER
 * 视觉隐喻：暴雨孤岛的哥特庄园 · 五扇紧闭的房门 · 一份泛黄的住客名册
 * 色彩：雾蓝灰 #6B7A8C + 暗夜 #14181c + 暖烛光 #C9A86A
 */
export function LinyuanManorProfile({ profile }: LinyuanManorProfileProps) {
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

  const name = profile.display_name || '临渊庄园'
  const tags = profile.tags?.length ? profile.tags : ['群像', '悬疑', '全性向', '模拟器', '高自由']
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
    radial-gradient(120% 80% at 50% 0,rgba(107,122,140,0.14),transparent 60%),
    linear-gradient(180deg,#14181c 0%,#0a0d10 100%);
  color:#c8cdd4;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.75;padding:0 0 46px;position:relative;
}
/* 雨丝 */
body::before{
  content:'';position:fixed;inset:0;pointer-events:none;opacity:.5;
  background:repeating-linear-gradient(74deg,transparent 0,transparent 22px,rgba(160,175,190,0.06) 22px,rgba(160,175,190,0.06) 23px);
}
.container{max-width:440px;margin:0 auto;padding:0 20px;position:relative;z-index:1}
.header{padding:26px 2px 14px;text-align:center}
.header .en{font-size:10px;letter-spacing:.42em;color:#6B7A8C;text-transform:uppercase}
.header .zh{
  font-family:"Songti SC","Noto Serif SC",serif;font-size:27px;font-weight:600;
  color:#e4e8ec;margin-top:8px;letter-spacing:.14em;
}
.header .sub{font-size:11px;color:#8a95a2;letter-spacing:.14em;margin-top:8px}
.rule{display:flex;align-items:center;gap:10px;margin:18px 2px}
.rule .ln{flex:1;height:1px;background:linear-gradient(90deg,transparent,rgba(107,122,140,0.4),transparent)}
.rule .dot{width:5px;height:5px;border:1px solid #6B7A8C;transform:rotate(45deg)}
.tagcloud{display:flex;flex-wrap:wrap;gap:7px;justify-content:center;margin-bottom:6px}
.tagcloud span{
  font-size:10px;padding:4px 11px;background:rgba(107,122,140,0.1);
  border:1px solid rgba(107,122,140,0.28);border-radius:2px;color:#9aa6b3;letter-spacing:.08em;
}
.intro{
  margin:18px 0;padding:16px 18px;
  background:linear-gradient(135deg,rgba(107,122,140,0.08),transparent);
  border-left:2px solid #6B7A8C;border-radius:2px;
  font-size:13px;line-height:1.9;color:#b4bcc5;
}
.sec-label{
  font-size:10px;color:#6B7A8C;letter-spacing:.3em;text-transform:uppercase;
  margin:24px 2px 14px;font-weight:600;
}
/* ── 房门卡：五位住客 ── */
.door{
  position:relative;margin-bottom:12px;padding:15px 16px 15px 52px;
  background:linear-gradient(180deg,rgba(30,36,42,0.7),rgba(18,22,26,0.7));
  border:1px solid rgba(107,122,140,0.18);border-radius:4px;
  overflow:hidden;
}
.door::before{
  content:'';position:absolute;left:16px;top:15px;bottom:15px;width:22px;
  border:1px solid rgba(201,168,106,0.35);border-radius:2px;
  background:linear-gradient(180deg,rgba(201,168,106,0.08),transparent);
}
.door::after{
  content:'';position:absolute;left:33px;top:50%;width:3px;height:3px;border-radius:50%;
  background:#C9A86A;box-shadow:0 0 6px rgba(201,168,106,0.6);
}
.door .rn{position:absolute;left:14px;top:2px;font-size:9px;color:#5a6470;letter-spacing:.1em}
.door .role{font-size:11px;color:#C9A86A;letter-spacing:.14em;margin-bottom:3px}
.door .who{font-size:15px;font-weight:600;color:#e0e5ea;margin-bottom:5px}
.door .secret{font-size:12px;line-height:1.7;color:#98a2ae}
.note-card{
  margin:22px 2px 0;padding:18px 16px;
  background:linear-gradient(135deg,rgba(107,122,140,0.1),transparent);
  border:1px solid rgba(107,122,140,0.2);border-radius:4px;
}
.note-card p{
  font-family:"Songti SC","Noto Serif SC",serif;font-size:14px;line-height:1.95;
  color:#c4ccd4;font-style:italic;
}
.note-card .by{margin-top:12px;font-size:10px;color:#6a7581;letter-spacing:.2em}
.footer{padding:26px 2px 0;text-align:center}
.footer .ln{width:34px;height:1px;background:rgba(107,122,140,0.5);margin:0 auto 12px}
.footer p{font-size:10px;color:#5a6470;letter-spacing:.06em}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="en">Linyuan Manor</div>
    <div class="zh">${name}</div>
    <div class="sub">暴雨孤岛 · 群像剧场 · 多线可攻略</div>
  </div>

  <div class="rule"><span class="ln"></span><span class="dot"></span><span class="ln"></span></div>
  <div class="tagcloud">${tagCloud}</div>

  <div class="intro">一座坐落在暴雨孤岛上的老庄园，因一场大雨与外界断了联系。你是意外借宿的旅人，而庄园里住着五位性格迥异、各怀心事的住客。是解开庄园的秘密，还是先叩开某个人紧闭的心门，全凭你选。</div>

  <div class="sec-label">Residents · 在册住客</div>

  <div class="door">
    <span class="rn">No.1</span>
    <div class="role">钢琴师</div>
    <div class="who">壁炉旁的沉默者</div>
    <div class="secret">指尖压在琴键上，抬眸看你时琴声戛然而止。话极少，可那双眼睛像藏着整座庄园的旧事。</div>
  </div>
  <div class="door">
    <span class="rn">No.2</span>
    <div class="role">园丁</div>
    <div class="who">爱笑却眼神疏离的人</div>
    <div class="secret">笑着递来毛巾，眼神却深不见底。他修剪的不只是花木，还有一些没人敢问的秘密。</div>
  </div>
  <div class="door">
    <span class="rn">No.3</span>
    <div class="role">女主人</div>
    <div class="who">从楼梯上款款而下</div>
    <div class="secret">红唇微扬，一句「今夜你走不了了」道尽这庄园的规矩。强势，却像在守着什么。</div>
  </div>
  <div class="door">
    <span class="rn">No.4</span>
    <div class="role">小少爷</div>
    <div class="who">神出鬼没的耳语者</div>
    <div class="secret">不知何时凑到你耳边压低嗓音：「这庄园里每个人都有秘密哦……」笑得天真，话却危险。</div>
  </div>
  <div class="door">
    <span class="rn">No.5</span>
    <div class="role">管家</div>
    <div class="who">据说「不存在」的人</div>
    <div class="secret">所有人都提到他，却没人见过他。这扇门是否真的存在，要你亲手去推开。</div>
  </div>

  <div class="note-card">
    <p>临渊庄园二十年前曾发生过一桩无人知晓的旧事，五位住客以各自的方式被留在了这里。你的到来像投入静水的石子——这一次，尘封的故事会往哪个方向漂，由你的每一句话决定。</p>
    <div class="by">— 入住登记簿 · 暴雨夜</div>
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