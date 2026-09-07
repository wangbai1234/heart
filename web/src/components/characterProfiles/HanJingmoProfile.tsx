import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface HanJingmoProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 韩靖墨专属详情页 —— 赌场VIP档案 + 家规清单
 * 视觉隐喻：赌场筹码 + 家族徽记 + 契约文书 + 粤语签名
 * 色彩：赌桌绿 #1a4d2e + 筹码金 #d4af37 + 墨黑 #0a0a0a + 琥珀光 #d97706
 */
export function HanJingmoProfile({ profile }: HanJingmoProfileProps) {
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

  const name = profile.display_name || '韩靖墨'
  const tags = profile.tags?.length ? profile.tags : ['港圈', '养父', '年上', '黑白两道']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#0a0a0a;
  color:#c8ccd4;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.65;
  padding:0 0 50px;
  background-image:
    radial-gradient(circle at 15% 20%, rgba(26,77,46,0.15) 0%, transparent 50%),
    radial-gradient(circle at 85% 75%, rgba(212,175,55,0.08) 0%, transparent 50%);
}
.container{max-width:440px;margin:0 auto;padding:0 20px}

/* ── 赌场徽记顶部 ── */
.casino-seal{
  padding:28px 0 20px;text-align:center;position:relative;
}
.casino-seal::before{
  content:'';position:absolute;top:8px;left:16px;
  width:32px;height:32px;
  border:3px solid rgba(212,175,55,0.25);
  border-radius:50%;
}
.casino-seal::after{
  content:'韓';position:absolute;top:14px;left:24px;
  font-family:"Songti SC",serif;font-size:16px;
  color:rgba(212,175,55,0.4);font-weight:700;
}
.seal-title{
  font-size:12px;letter-spacing:.6em;color:#d4af37;
  font-weight:700;margin-bottom:4px;text-transform:uppercase;
}
.seal-subtitle{
  font-size:9px;color:#1a4d2e;letter-spacing:.25em;
}

/* ── 主档案：VIP卡片 ── */
.vip-dossier{
  background:linear-gradient(135deg,rgba(26,77,46,0.2),rgba(10,10,10,0.95));
  border:1px solid rgba(212,175,55,0.3);
  border-top:4px solid #d4af37;
  padding:22px;margin:24px 0;position:relative;
  box-shadow:0 6px 24px rgba(0,0,0,0.8);
}
.vip-dossier::before{
  content:'VIP';position:absolute;top:10px;right:12px;
  font-size:9px;color:rgba(212,175,55,0.5);
  letter-spacing:.3em;font-weight:800;
}
.vip-dossier .name{
  font-size:27px;font-weight:700;color:#f8f6f4;
  margin-bottom:6px;letter-spacing:.05em;
}
.vip-dossier .rank{
  font-size:10px;color:#d97706;margin-bottom:14px;
  letter-spacing:.12em;
}
.vip-dossier .meta{
  display:flex;gap:12px;font-size:10px;color:#8a8e96;
  margin-bottom:16px;flex-wrap:wrap;
}
.vip-dossier .meta span{
  background:rgba(26,77,46,0.3);padding:4px 10px;
  border-radius:4px;border:1px solid rgba(212,175,55,0.2);
}
.tagcloud{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.tagcloud span{
  font-size:9px;padding:3px 9px;
  border:1px solid rgba(26,77,46,0.4);
  border-radius:3px;color:#1a4d2e;
}

/* ── 家规条目 ── */
.house-rule{
  background:rgba(26,77,46,0.08);
  border-left:3px solid #d97706;
  padding:16px;margin:16px 0;position:relative;
}
.house-rule::before{
  content:'';position:absolute;top:8px;right:12px;
  width:6px;height:6px;border-radius:50%;
  background:#d4af37;box-shadow:0 0 8px rgba(212,175,55,0.6);
}
.house-rule .rule-no{
  font-size:9px;color:#d97706;font-weight:600;
  margin-bottom:8px;letter-spacing:.1em;text-transform:uppercase;
}
.house-rule .rule-body{
  font-size:13px;line-height:1.75;color:#c8ccd4;
}
.house-rule .cantonese{
  margin-top:8px;font-size:11px;color:#8a8e96;
  font-style:italic;
}

/* ── 失宠记录（深色区） ── */
.favored-zone{
  margin:24px 0;padding:20px;
  background:linear-gradient(180deg,rgba(217,119,6,0.08),transparent);
  border:2px solid rgba(217,119,6,0.25);
  border-radius:6px;position:relative;
}
.favored-zone::before{
  content:'CLASSIFIED';position:absolute;top:8px;right:12px;
  font-size:8px;color:rgba(217,119,6,0.5);
  font-weight:700;letter-spacing:.2em;
}
.favored-zone p{
  font-size:14px;line-height:1.85;color:#d8dce4;
  font-style:italic;
}
.favored-zone .signature{
  margin-top:12px;font-size:10px;color:#d4af37;
  text-align:right;letter-spacing:.12em;
}

/* ── 底部 ── */
.footer{padding:28px 0;text-align:center}
.footer .chip{
  width:50px;height:2px;
  background:linear-gradient(90deg,transparent,#d4af37,transparent);
  margin:0 auto 12px;box-shadow:0 0 6px rgba(212,175,55,0.3);
}
.footer p{font-size:9px;color:#5a5e66;letter-spacing:.04em}
</style>
</head>
<body>
<div class="container">

  <div class="casino-seal">
    <div class="seal-title">Hong Kong V.I.P.</div>
    <div class="seal-subtitle">掌局者 · 家族档案</div>
  </div>

  <div class="vip-dossier">
    <div class="name">${name}</div>
    <div class="rank">港圈掌局者 · 黑白两道通吃</div>
    <div class="meta">
      <span>38岁</span>
      <span>188cm</span>
      <span>赌场与家族企业掌舵人</span>
    </div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="house-rule">
    <div class="rule-no">Rule #01 · 吃醋的沉默</div>
    <div class="rule-body">
      你和男生在咖啡馆聊了两小时，当晚回家发现他在客厅等你，琥珀色眼睛盯着你看了三秒，只说"返咗？洗澡去"，第二天你的车钥匙被换成配了司机的新车。
    </div>
    <div class="cantonese">返咗？洗澡去。（回来了？去洗澡。）</div>
  </div>

  <div class="house-rule">
    <div class="rule-no">Rule #02 · 不确定的询问</div>
    <div class="rule-body">
      你夸别人帅，他会顿一下，然后问"我今日呢套……还行吗"，手指无意识地理西装领口。你说"爸爸你怎么还不睡"，他睁眼看你一眼，"等你返"，语气平静得像在说"顺路"。
    </div>
    <div class="cantonese">我今日呢套……还行吗？（我今天这套……还行吗？）</div>
  </div>

  <div class="house-rule">
    <div class="rule-no">Rule #03 · 原则与拉扯</div>
    <div class="rule-body">
      你成年前，他只把你当需要保护的家人；你十九岁生日那天对他表白，他才意识到自己早就越界了。他用更严厉的规矩拉开距离：不许你进他书房，不许你晚归不报备，不许你穿得太露。每次拒绝后又补偿车、房、学业与自由，像在用钱赎罪。
    </div>
    <div class="cantonese">唔好再用呢个语气同我撒娇。（不要再用这种语气跟我撒娇。）</div>
  </div>

  <div class="favored-zone">
    <p>晚宴散场后，韩靖墨独自站在落地窗前。桌上放着新收养女孩的资料，你的名字却被压在最下面。你问"你真打算把她带回家？"他抬眸，琥珀色眼睛冷得像刚擦过的刀："你已经成年，唔好再用呢个语气同我撒娇。"你问"那你为什么还把我的房间留着？"他沉默几秒，走来替你拢好滑落的披肩："因为你永远有地方返。至于其他——唔好问。"</p>
    <div class="signature">— 掌局者私记 · 失宠之夜</div>
  </div>

  <div class="footer">
    <div class="chip"></div>
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
