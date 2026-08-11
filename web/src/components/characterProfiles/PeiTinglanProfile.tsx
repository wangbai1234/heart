import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface PeiTinglanProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 裴听澜专属详情页 —— 午夜独奏会「节目单 / PROGRAMME」
 * 视觉语言：午夜紫黑 + 浅粉银灰 + 雾紫，衬线优雅体，五线谱横线做装饰分隔
 * 24岁天才钢琴师 · 浅粉银发 · 破碎依赖 · 只想被你听见琴声之外的疼
 */
export function PeiTinglanProfile({ profile }: PeiTinglanProfileProps) {
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

  const name = profile.display_name || '裴听澜'
  const tags = profile.tags?.length ? profile.tags : ['音乐家', '天才', '破碎感', '救赎', '女性向']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#16121c;
  color:#dcd6df;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;
  padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}
.serif{font-family:"Times New Roman","Songti SC",serif}

/* ── 音乐会刊头 ── */
.recital-head{
  padding:26px 2px 18px;
  border-bottom:1px solid rgba(220,214,223,.18);
}
.recital-head .venue{
  font-size:10px;letter-spacing:.38em;color:#8c7a9b;
  text-transform:uppercase;margin-bottom:8px;
}
.recital-head .title{
  font-family:"Times New Roman",serif;
  font-size:40px;line-height:1.1;font-weight:700;
  letter-spacing:.02em;color:#f0eaef;margin-bottom:6px;
}
.recital-head .sub{
  font-size:11px;letter-spacing:.26em;color:#a297a8;
}

/* ── 艺术家名 ── */
.artist{
  padding:22px 2px;
  border-bottom:1px solid rgba(255,255,255,.06);
}
.artist .label{
  font-size:10px;letter-spacing:.32em;color:#8c7a9b;
  text-transform:uppercase;margin-bottom:10px;
}
.artist .name{
  font-family:"Times New Roman","Songti SC",serif;
  font-size:30px;letter-spacing:.08em;color:#e7e0eb;
  font-weight:600;margin-bottom:8px;
}
.artist .desc{
  font-size:12.5px;line-height:1.75;color:#b2a7bb;margin-bottom:14px;
}
.tagcloud{display:flex;flex-wrap:wrap;gap:7px}
.tagcloud span{
  font-size:10.5px;padding:3px 10px;
  border:1px solid rgba(140,122,155,.35);
  border-radius:2px;color:#c5bad0;letter-spacing:.06em;
}

/* ── 五线谱装饰分隔 ── */
.staff-divider{
  height:20px;
  background:repeating-linear-gradient(
    to bottom,
    transparent,transparent 3px,
    rgba(140,122,155,.15) 3px,rgba(140,122,155,.15) 4px
  );
  background-size:100% 5px;
  background-position:0 0;
  margin:20px 0;
}

/* ── section 通用 ── */
.section{padding:28px 2px}
.section+.section{border-top:1px solid rgba(255,255,255,.06)}
.sec-head{
  font-size:10px;letter-spacing:.34em;color:#8c7a9b;
  text-transform:uppercase;margin-bottom:18px;
}

/* ── 节目单曲目 ── */
.piece{margin-bottom:26px}
.piece .num{
  font-family:"Times New Roman",serif;font-size:11px;
  color:#7d6e8a;letter-spacing:.08em;margin-bottom:6px;
}
.piece .title{
  font-family:"Times New Roman","Songti SC",serif;
  font-size:18px;line-height:1.5;color:#ebe5f0;
  margin-bottom:5px;font-weight:600;
}
.piece .note{
  font-size:12px;line-height:1.8;color:#9d91a7;
  font-style:italic;padding-left:14px;
  border-left:2px solid rgba(140,122,155,.25);
}

/* ── 掌声之外 时间线 ── */
.timeline{margin:6px 0}
.timeline .item{
  padding:12px 0 12px 18px;
  border-left:1px solid rgba(140,122,155,.22);
  position:relative;margin-bottom:10px;
}
.timeline .item::before{
  content:"";position:absolute;left:-3px;top:16px;
  width:5px;height:5px;border-radius:50%;
  background:#8c7a9b;
}
.timeline .age{
  font-size:10px;color:#8c7a9b;letter-spacing:.1em;
  font-weight:600;margin-bottom:4px;
}
.timeline .txt{
  font-size:13px;line-height:1.75;color:#b8adc1;
}

/* ── 未完成安可 留白五线谱 ── */
.encore{
  margin:14px 2px 0;padding:32px 20px;
  background:linear-gradient(150deg,rgba(140,122,155,.06),rgba(0,0,0,0));
  border:1px dashed rgba(140,122,155,.25);
  border-radius:4px;
}
.encore .head{
  font-family:"Times New Roman",serif;
  font-size:15px;color:#d4cad9;font-style:italic;
  margin-bottom:16px;
}
.encore .staff{
  height:50px;
  background:repeating-linear-gradient(
    to bottom,
    transparent,transparent 9px,
    rgba(140,122,155,.18) 9px,rgba(140,122,155,.18) 10px
  );
  background-size:100% 12.5px;
  margin-bottom:12px;
}
.encore .txt{
  font-size:12px;line-height:1.9;color:#9d91a7;
  font-style:italic;
}

/* ── 深夜告白 pull-quote ── */
.finale{
  margin:14px 2px 0;padding:28px 22px;
  background:linear-gradient(155deg,rgba(140,122,155,.08),rgba(0,0,0,0));
  border-left:2px solid #8c7a9b;
}
.finale p{
  font-family:"Times New Roman","Songti SC",serif;
  font-size:17px;line-height:1.85;color:#e8e2ed;
  font-style:italic;
}
.finale .by{
  margin-top:12px;font-size:10px;letter-spacing:.26em;
  color:#8d7f9a;
}

/* ── 页脚声明 ── */
.foot{padding:26px 2px 0;text-align:center}
.foot .line{
  width:36px;height:1px;background:rgba(140,122,155,.4);
  margin:0 auto 14px;
}
.foot p{
  font-size:10.5px;color:#716679;letter-spacing:.06em;
  line-height:1.7;
}
</style>
</head>
<body>
<div class="container">

  <div class="recital-head">
    <div class="venue">Atelier Theatre · 今夜独奏</div>
    <div class="title">RECITAL</div>
    <div class="sub">for an audience of one</div>
  </div>

  <div class="artist">
    <div class="label">Pianist</div>
    <div class="name">${name}</div>
    <p class="desc">24岁钢琴师 · 浅粉银发 · 三岁复现旋律 · 只想被你听见琴声之外的疼</p>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="staff-divider"></div>

  <div class="section">
    <div class="sec-head">Programme · 今夜曲目</div>

    <div class="piece">
      <div class="num">I.</div>
      <div class="title">神童序曲 · Prodigy Overture</div>
      <div class="note">三岁复现听过的旋律，五岁登台，八岁被誉神童。掌声再热烈，没人问过他是否真的快乐。</div>
    </div>

    <div class="piece">
      <div class="num">II.</div>
      <div class="title">高烧安魂曲 · Feverish Requiem</div>
      <div class="note">十二岁，三十九度高烧仍登台，完美无缺。所有人只夸专业，没人关心他的疼。</div>
    </div>

    <div class="piece">
      <div class="num">III.</div>
      <div class="title">破碎变奏 · Shattered Variations</div>
      <div class="note">此处他在忍痛，全场只有你听出来了。十六岁练习室的崩溃被偷录卖给媒体，从那之后他学会了在镜头前永远微笑。</div>
    </div>

    <div class="piece">
      <div class="num">IV.</div>
      <div class="title">为唯一听众而作 · Solus Ad Te</div>
      <div class="note">在最后一个音符处，他停顿了，眼神在寻找你——只要你还在那里，这首曲子就有了完整的结尾。</div>
    </div>
  </div>

  <div class="staff-divider"></div>

  <div class="section">
    <div class="sec-head">掌声之外 · Behind the Applause</div>
    <div class="timeline">
      <div class="item">
        <div class="age">3 岁</div>
        <div class="txt">复现听过的旋律，所有人惊叹「天才」，没人问他想不想一直弹下去。</div>
      </div>
      <div class="item">
        <div class="age">5 岁</div>
        <div class="txt">第一次登台，聚光灯太烫，他不敢说，怕被骂不够专业。</div>
      </div>
      <div class="item">
        <div class="age">8 岁</div>
        <div class="txt">被称为神童，开始全球巡演，手指练到破皮，绷带缠完继续弹。</div>
      </div>
      <div class="item">
        <div class="age">12 岁</div>
        <div class="txt">高烧三十九度登台，完美谢幕，事后所有人只关心演出效果，没人给他一杯热水。</div>
      </div>
      <div class="item">
        <div class="age">16 岁</div>
        <div class="txt">练习室的一次崩溃被偷录，视频卖给媒体。从那天起，他学会了把所有疼痛藏进琴声里。</div>
      </div>
      <div class="item">
        <div class="age">24 岁</div>
        <div class="txt">浅粉银发像快折断的玫瑰，只想有一个人愿意听懂他琴声之外的疼。</div>
      </div>
    </div>
  </div>

  <div class="staff-divider"></div>

  <div class="section">
    <div class="sec-head">未写完的安可 · Unfinished Encore</div>
    <div class="encore">
      <div class="head">for you, only</div>
      <div class="staff"></div>
      <p class="txt">这首曲子他藏在没有观众的夜晚，把缺失的乐章一句句藏进发给你的消息里。<br>只有你愿意读，才能替他完成这个结尾。</p>
    </div>
  </div>

  <div class="finale">
    <p>"这么多年所有人都爱我的天赋。别走……今晚，只为你一个人弹。"</p>
    <div class="by">— 散场后，他坐在钢琴前等你，灯灭了也不离开</div>
  </div>

  <div class="foot">
    <div class="line"></div>
    <p>本刊角色设定纯属虚构 与现实无关</p>
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




