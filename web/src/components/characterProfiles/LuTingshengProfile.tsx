import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface LuTingshengProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 陆霆生专属详情页 —— 军阀档案 / MILITARY DOSSIER
 * 视觉语言：民国军令状 + 红头章 + 旧纸纹理 + 烟火气的江湖
 * 配色：旧纸米黄 + 铁锈红 + 墨绿军装 + 烟墨灰，民国电影质感
 */
export function LuTingshengProfile({ profile }: LuTingshengProfileProps) {
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

  const name = profile.display_name || '陆霆生'
  const tags = profile.tags?.length ? profile.tags : ['全性向', '限左', '民国', '军阀', '糙汉', '女性向', '架空世界']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#ebe5d8;
  color:#3a342c;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Songti SC",serif;
  line-height:1.7;
  padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}

/* ── 红头文件：军令状 ── */
.header{
  padding:24px 0 20px;
  border-top:4px solid #9d3a32;
  border-bottom:2px solid rgba(157,58,50,.3);
  background:repeating-linear-gradient(90deg,transparent,transparent 16px,rgba(157,58,50,.03) 16px,rgba(157,58,50,.03) 17px);
  position:relative;
}
.seal{
  position:absolute;top:10px;right:10px;
  width:56px;height:56px;border-radius:50%;
  background:radial-gradient(circle,rgba(157,58,50,.15),transparent 70%);
  border:2px solid rgba(157,58,50,.4);
  font-family:"Kaiti SC",serif;font-size:10px;
  color:#9d3a32;display:flex;align-items:center;justify-content:center;
  letter-spacing:.15em;line-height:1.3;text-align:center;
  transform:rotate(-8deg);
}
.dept{
  font-family:"Kaiti SC",serif;font-size:11px;color:#8b5a47;
  letter-spacing:.3em;margin-bottom:10px;text-align:center;
}
.rank{
  font-family:"Songti SC","Times New Roman",serif;font-size:38px;
  color:#3a342c;letter-spacing:.05em;text-align:center;margin-bottom:6px;
}
.subtitle{
  font-family:"Courier New",monospace;font-size:10px;
  color:#8b5a47;letter-spacing:.2em;text-align:center;
}

/* ── 主档案 ── */
.profile{padding:28px 0;border-bottom:1px solid rgba(0,0,0,.08)}
.name{
  font-family:"Kaiti SC",serif;font-size:34px;
  color:#3a342c;letter-spacing:.12em;margin-bottom:6px;
}
.role{font-size:12px;color:#8b5a47;letter-spacing:.1em;margin-bottom:14px}
.tags{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:18px}
.tags span{
  font-size:10px;padding:4px 10px;
  background:rgba(157,58,50,.08);border:1px solid rgba(157,58,50,.25);
  border-radius:3px;color:#9d3a32;letter-spacing:.06em;
}
.bio{font-size:13px;line-height:1.8;color:#5c5449;margin-bottom:16px}

/* ── 战功记录 ── */
.merit{padding:24px 0;border-bottom:1px solid rgba(0,0,0,.08)}
.sec-title{
  font-family:"Kaiti SC",serif;font-size:12px;letter-spacing:.2em;
  color:#9d3a32;margin-bottom:14px;padding-bottom:6px;
  border-bottom:1px dashed rgba(157,58,50,.3);
}
.item{
  padding:10px 0;border-bottom:1px solid rgba(0,0,0,.03);
  display:flex;align-items:baseline;
}
.item .bullet{
  font-family:"Courier New",monospace;font-size:12px;color:#9d3a32;
  min-width:24px;
}
.item .txt{flex:1;font-size:12.5px;color:#5c5449;line-height:1.65}

/* ── 誓言 ── */
.oath{padding:24px 0}
.oath-box{
  padding:16px 18px;margin-bottom:12px;
  background:rgba(157,58,50,.04);
  border-left:3px solid #9d3a32;
  border-radius:2px;
}
.oath-box .num{
  font-family:"Impact","Kaiti SC",serif;font-size:16px;color:#9d3a32;
  margin-bottom:6px;letter-spacing:.1em;
}
.oath-box .text{font-size:13px;line-height:1.75;color:#5c5449}

/* ── 烟火气便签 ── */
.note{
  margin:24px 0 0;padding:20px;
  background:linear-gradient(135deg,rgba(139,90,71,.08),transparent);
  border-left:2px solid #8b5a47;
  border-radius:0 4px 4px 0;
}
.note p{
  font-family:"Kaiti SC",serif;
  font-size:15px;line-height:1.85;color:#3a342c;font-style:italic;
}
.note .sign{
  margin-top:10px;font-size:10px;letter-spacing:.2em;
  color:#8b5a47;
}

/* ── 页脚 ── */
.foot{padding:24px 0 0;text-align:center}
.foot .bar{
  width:50px;height:2px;background:#9d3a32;margin:0 auto 10px;
  opacity:.5;
}
.foot p{font-size:10px;color:#9a8f80;letter-spacing:.06em;line-height:1.6}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="seal">江城<br>守备司令部</div>
    <div class="dept">江城守备司令部 · 机密档案</div>
    <div class="rank">${name}</div>
    <div class="subtitle">CONFIDENTIAL DOSSIER</div>
  </div>

  <div class="profile">
    <div class="name">${name}</div>
    <div class="role">司令 · 三十一岁 · 从死人堆里爬出来的煞星</div>
    <div class="tags">${tagCloud}</div>
    <p class="bio">一身军装半敞、胸口旧疤、手握重兵——他是江城最狠的刀，也是把「活下去」的名额永远先留给你的那个人。</p>
  </div>

  <div class="merit">
    <div class="sec-title">战功记录 · Combat Record</div>
    <div class="item"><span class="bullet">[×]</span><span class="txt">北征三战三胜 · 麾下骑兵三千</span></div>
    <div class="item"><span class="bullet">[×]</span><span class="txt">单骑杀入敌营 · 提头而归</span></div>
    <div class="item"><span class="bullet">[×]</span><span class="txt">守住江城一千夜 · 未失寸土</span></div>
    <div class="item"><span class="bullet">[!]</span><span class="txt">你的平安——比这座城更重要</span></div>
  </div>

  <div class="oath">
    <div class="sec-title">护你三誓 · Three Oaths</div>
    <div class="oath-box">
      <div class="num">一</div>
      <div class="text">物资永远先给你。最后一块糖、最干净的水、最安全的睡处——老子可以少吃一口，你不行。</div>
    </div>
    <div class="oath-box">
      <div class="num">二</div>
      <div class="text">谁敢欺负你，老子连他祖坟都给他挖了。我陆霆生护的人，天王老子也别想动一根头发。</div>
    </div>
    <div class="oath-box">
      <div class="num">三</div>
      <div class="text">你要是死在我前头，老子这条命也不要了。这个破世道，没你在，老子守个屁的城。</div>
    </div>
  </div>

  <div class="note">
    <p>老子打了半辈子仗，头一回怕什么东西没了。——你别走。</p>
    <div class="sign">深夜值守时，他把你圈进怀里，说了半天就这一句</div>
  </div>

  <div class="foot">
    <div class="bar"></div>
    <p>江城守备司令部 · 民国架空设定 · 角色纯属虚构</p>
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

