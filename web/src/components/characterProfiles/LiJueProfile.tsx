import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface LiJueProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 厉决专属详情页 —— 港城黑白影像 · 英文 hero quote + 档案 / 过往 / 这双手
 * 参考 nimoo「谢寒」英文 slogan + tab 分区档案模板
 * 视觉语言：港城夜雨黑金 + 冷银 + 锈血红，硬边影调，核心意象「他的手」，无 emoji
 */
export function LiJueProfile({ profile }: LiJueProfileProps) {
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

  const name = profile.display_name || '厉决'
  const tags = profile.tags?.length ? profile.tags : ['黑道', '强制爱', '冷酷', '占有欲']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#0a0a0b;
  color:#cbc7c2;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}
.serif{font-family:"Times New Roman",serif}

/* ── hero 英文 slogan ── */
.hero{padding:38px 2px 26px;border-bottom:1px solid rgba(160,40,40,.28)}
.hero .en{
  font-family:"Times New Roman",serif;font-size:34px;line-height:1.15;font-weight:700;
  color:#eae6e1;letter-spacing:-.01em;
}
.hero .en b{color:#a83232;font-weight:700}
.hero .zh{margin-top:18px;font-size:22px;letter-spacing:.34em;color:#e8e4df;font-weight:700}
.hero .role{margin-top:8px;font-size:12px;letter-spacing:.2em;color:#7a726c;text-transform:uppercase}

/* ── tab 导航 ── */
.tabs{display:flex;gap:0;margin-top:22px;border-bottom:1px solid rgba(255,255,255,.08)}
.tabs .t{
  flex:1;text-align:center;padding:12px 0;font-size:12px;letter-spacing:.14em;
  color:#7a726c;cursor:default;position:relative;
}
.tabs .t.on{color:#cb8a4a}
.tabs .t.on::after{content:"";position:absolute;left:20%;right:20%;bottom:-1px;height:2px;background:#cb8a4a}

/* ── section ── */
.sec{padding:26px 2px}
.sec+.sec{border-top:1px solid rgba(255,255,255,.06)}
.sec .h{font-size:11px;letter-spacing:.28em;color:#cb8a4a;text-transform:uppercase;margin-bottom:16px}
.sec .h .zh{color:#9a928c;letter-spacing:.14em;margin-left:8px}

/* 档案行 */
.d-row{display:flex;padding:9px 0;border-bottom:1px solid rgba(255,255,255,.05);font-size:13px}
.d-row:last-child{border-bottom:none}
.d-row .k{min-width:60px;color:#6f655f}
.d-row .v{color:#cbc1b9;flex:1}

/* 过往时间线 */
.tl{position:relative;padding-left:20px}
.tl::before{content:"";position:absolute;left:4px;top:4px;bottom:4px;width:1px;background:rgba(160,40,40,.4)}
.tl .node{position:relative;margin-bottom:16px}
.tl .node::before{content:"";position:absolute;left:-19px;top:5px;width:7px;height:7px;border-radius:50%;background:#a83232}
.tl .age{font-family:"Times New Roman",serif;font-size:14px;font-weight:700;color:#cb8a4a}
.tl .txt{font-size:12.5px;line-height:1.7;color:#a89e96;margin-top:3px}

/* 这双手 */
.hands{padding:22px 20px;border-radius:4px;background:linear-gradient(160deg,rgba(160,40,40,.1),transparent);border:1px solid rgba(160,40,40,.2)}
.hands p{font-size:14px;line-height:1.95;color:#c4bab2}
.hands p em{color:#e6d0c8;font-style:normal}
.hands .q{margin-top:16px;font-family:"Times New Roman","Songti SC",serif;font-size:18px;font-style:italic;line-height:1.7;color:#eadfd8}

.tagcloud{margin-top:22px;display:flex;flex-wrap:wrap;gap:8px}
.tagcloud span{font-size:11px;padding:4px 11px;border:1px solid rgba(203,138,74,.32);border-radius:2px;color:#c9beb3;letter-spacing:.06em}
.foot{margin-top:24px;text-align:center;font-size:11px;color:#5a524c;letter-spacing:.06em}
</style>
</head>
<body>
<div class="container">

  <div class="hero">
    <div class="en">I've done things<br>you'd fear. <b>These hands</b><br>will only guard you.</div>
    <div class="zh">${name}</div>
    <div class="role">Lord of the Underground · 港城地下之王</div>
  </div>

  <div class="tabs"><span class="t on">档案</span><span class="t">过往</span><span class="t">这双手</span></div>

  <div class="sec">
    <div class="h">Profile<span class="zh">档案</span></div>
    <div class="d-row"><span class="k">姓名</span><span class="v">${name} · 港城人称「煞」</span></div>
    <div class="d-row"><span class="k">年龄</span><span class="v">32 · 银白短发，黑白外套下是旧伤</span></div>
    <div class="d-row"><span class="k">地位</span><span class="v">地下势力掌权者，谈判桌一个眼神让人签字</span></div>
    <div class="d-row"><span class="k">对你</span><span class="v">让整座港城颤抖的人，在你面前是不会撒娇的大型犬</span></div>
    <div class="d-row"><span class="k">占有</span><span class="v">对你搭话的人，第二天从这座城消失</span></div>
  </div>

  <div class="sec">
    <div class="h">Past<span class="zh">过往</span></div>
    <div class="tl">
      <div class="node"><div class="age">六岁</div><div class="txt">孤儿，开始在街头讨生活</div></div>
      <div class="node"><div class="age">十二岁</div><div class="txt">第一次见血。十五岁那年做过的事，成了他这辈子唯一的耻辱</div></div>
      <div class="node"><div class="age">十八岁</div><div class="txt">已是这条街的王。信奉弱肉强食，不信有人会无条件对他好</div></div>
      <div class="node"><div class="age">此刻</div><div class="txt">你是唯一的反例——他觉得自己配不上你，却无法放手</div></div>
    </div>
  </div>

  <div class="sec">
    <div class="h">These Hands<span class="zh">这双手</span></div>
    <div class="hands">
      <p>你随口说那家店的蛋糕不错，第二天那店就多了个固定包场的 VIP 位；你说怕黑，<em>他把你住的整条街路灯全换成暖光</em>。做完一场让人不寒而栗的「谈判」，他沉默走到你面前，把带血腥气的手举在半空——不敢碰你，像个等着被原谅的孩子。</p>
      <div class="q">“脏不脏……你觉得我脏不脏？<br>如果你觉得脏，我明天就不做了。我什么都可以不要。”</div>
    </div>
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