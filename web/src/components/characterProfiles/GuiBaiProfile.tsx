import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface GuiBaiProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 归白专属详情页 —— 灵契仙卷 / SPIRIT PACT SCROLL
 * 千年白狐灵，以狐形伴公主七年，化形只为一句"选我"。
 * 视觉语言：雾墨底+古金+翠玉，灵兽密录卷轴质感，
 * 玉印章+竖排注文+宣纸渐变，衬线体为主，仙气克制不浮华。
 */
export function GuiBaiProfile({ profile }: GuiBaiProfileProps) {
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

  const name = profile.display_name || '归白'
  const tags = profile.tags?.length ? profile.tags : ['玄幻', '狐妖', '暗恋', '古风']
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
    radial-gradient(ellipse 100% 50% at 50% 0%,rgba(120,150,130,.08),transparent 60%),
    #0c1012;
  color:#e0d8cc;
  font-family:"Songti SC","STSong","SimSun",serif;
  line-height:1.9;
  padding:0 0 48px;
}
.container{max-width:420px;margin:0 auto;padding:0 20px}
.sans{font-family:-apple-system,"PingFang SC",sans-serif}

/* ── 卷首 ── */
.header{
  padding:28px 0 20px;text-align:center;
  border-bottom:1px solid rgba(168,176,152,.25);
}
.seal{
  width:56px;height:56px;margin:0 auto 14px;
  border-radius:50%;
  background:radial-gradient(circle at 40% 38%,rgba(168,176,152,.2),transparent 70%);
  border:1.5px solid rgba(168,176,152,.5);
  display:flex;align-items:center;justify-content:center;
  font-size:20px;font-weight:700;color:#a8b098;letter-spacing:.2em;
}
.vol{
  font-size:10px;letter-spacing:.45em;color:#8a9880;
  text-transform:uppercase;margin-bottom:6px;
}
.title{
  font-size:20px;letter-spacing:.7em;color:#c4b898;margin-bottom:4px;
}
.sub{
  font-size:11px;color:#7a8870;letter-spacing:.35em;
}

/* ── 灵兽档 ── */
.scroll{
  padding:28px 0;
  border-bottom:1px solid rgba(255,255,255,.05);
}
.scroll-label{
  font-size:11px;color:#a8b098;letter-spacing:.3em;
  margin-bottom:10px;border-left:3px solid #a8b098;padding-left:10px;
}
.s-row{
  display:flex;margin-bottom:9px;font-size:13px;
}
.s-row .k{
  color:#8a9880;min-width:64px;letter-spacing:.15em;
}
.s-row .v{
  color:#d4ccbc;flex:1;
}

/* ── 七年之约（核心段落） ── */
.pact{
  padding:28px 0;
  border-bottom:1px solid rgba(255,255,255,.05);
}
.pact-head{
  font-size:12px;color:#c4b898;letter-spacing:.4em;margin-bottom:18px;
  text-align:center;
}
.pact-text{
  font-size:14px;line-height:2.2;color:#c8c0b0;
  text-indent:2em;margin-bottom:16px;
  text-align:justify;
}

/* ── 化形之后（反差段） ── */
.transform{
  padding:26px 0;
  border-bottom:1px solid rgba(255,255,255,.05);
}
.tf-label{
  font-size:11px;color:#a8b098;letter-spacing:.3em;
  margin-bottom:14px;text-align:center;
}
.tf-item{
  display:flex;gap:14px;padding:11px 0;
  border-bottom:1px solid rgba(255,255,255,.04);
  font-size:13px;
}
.tf-item:last-child{border-bottom:none}
.tf-item .before{
  color:#7a8870;min-width:90px;
}
.tf-item .after{
  color:#d4c8a8;flex:1;font-style:italic;
}

/* ── 竖排侧注 ── */
.side-note{
  margin:22px 0;padding:18px 16px;
  background:linear-gradient(145deg,rgba(168,176,152,.06),transparent);
  border-left:2px solid rgba(168,176,152,.35);
  border-radius:4px;
}
.side-note p{
  font-size:13px;line-height:2;color:#b0a890;font-style:italic;
}

/* ── 结尾 pull-quote ── */
.pullquote{
  margin:24px 2px 0;padding:26px 20px;
  background:linear-gradient(155deg,rgba(196,184,152,.08),transparent);
  border-left:2px solid #c4b898;
  border-radius:4px;
}
.pullquote p{
  font-size:17px;line-height:1.8;color:#e8dcd0;
}
.pullquote .by{
  margin-top:14px;font-size:10px;letter-spacing:.25em;color:#8a9880;text-align:right;
}

/* ── 标签+页脚 ── */
.tagcloud{margin-top:20px;display:flex;flex-wrap:wrap;gap:8px}
.tagcloud span{
  font-size:11px;padding:4px 10px;
  border:1px solid rgba(168,176,152,.3);border-radius:2px;
  color:#b0a890;letter-spacing:.06em;
}
.foot{padding:24px 2px 0;text-align:center}
.foot .line{width:40px;height:1px;background:rgba(168,176,152,.35);margin:0 auto 12px}
.foot p{font-size:10px;color:#6a7060;letter-spacing:.04em}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="seal">狐</div>
    <div class="vol">Spirit Archive · Vol. IX</div>
    <div class="title">灵兽密录</div>
    <div class="sub">第九卷 · 白狐灵 · 极密</div>
  </div>

  <div class="scroll">
    <div class="scroll-label">灵兽卷宗</div>
    <div class="s-row"><span class="k">真名</span><span class="v">${name}</span></div>
    <div class="s-row"><span class="k">修行</span><span class="v">千年 · 深山灵狐一脉</span></div>
    <div class="s-row"><span class="k">化形</span><span class="v">白发琥珀眸 · 耳尖未完全收敛 · 尾巴忍不住时会露</span></div>
    <div class="s-row"><span class="k">契主</span><span class="v">夏朝公主 · 秋猎救命之恩</span></div>
    <div class="s-row"><span class="k">弱点</span><span class="v">被叫名字时下意识摇尾巴</span></div>
  </div>

  <div class="pact">
    <div class="pact-head">七年之约</div>
    <div class="pact-text">
      他以狐的身份陪伴了你七年。你读书时趴在案头假寐，实则竖着耳朵听你翻页的声音。
      你入睡时蜷在枕边，用蓬松的尾巴替你掖好被角。你难过时把温热的脑袋拱进你的手心，
      湿润的鼻尖蹭过你的指缝——你以为那是小狐狸在安慰你，他知道那是自己在亲你。
    </div>
    <div class="pact-text">
      整个东宫以为公主养了一只不寻常的灵兽，没人知道他早已能化人形。
      他不敢。怕你知道他是妖会害怕，更怕你知道他是男人会赶他走。
      于是他甘愿做一辈子枕边的小狐狸——直到你在温泉里叹气问该选谁。
    </div>
  </div>

  <div class="transform">
    <div class="tf-label">化形之后 · 判若两兽</div>
    <div class="tf-item"><span class="before">狐形 · 从容懒散</span><span class="after">人形 · 局促耳红、说话结巴</span></div>
    <div class="tf-item"><span class="before">狐形 · 蹭你手心</span><span class="after">人形 · 伸手又缩回，不知该怎么碰你</span></div>
    <div class="tf-item"><span class="before">狐形 · 高兴摇尾巴</span><span class="after">人形 · 高兴也摇……然后手忙脚乱藏起来</span></div>
    <div class="tf-item"><span class="before">狐形 · 被摸耳朵就翻肚皮</span><span class="after">人形 · 被碰耳朵整个人僵住、耳尖烧红</span></div>
  </div>

  <div class="side-note">
    <p>他不贪心。不求功名，不求封地，连人形都是今夜才敢给你看。他只想你知道一件事：他摇尾巴，不是因为你是主人——是因为你是你。</p>
  </div>

  <div class="pullquote">
    <p>「你叫我名字时我会摇尾巴。这件事……我瞒了你很久。」</p>
    <div class="by">── ${name} · 温泉夜</div>
  </div>

  <div class="tagcloud">${tagCloud}</div>
  <div class="foot">
    <div class="line"></div>
    <p>本卷角色设定纯属虚构 与现实无关</p>
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
