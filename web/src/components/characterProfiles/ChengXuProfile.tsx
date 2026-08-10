import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface ChengXuProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 程叙专属详情页 —— 手写日记 + polaroid 照片贴
 * 参考 nimoo 简洁 + 纸质温暖质感 + 便签纸元素
 */
export function ChengXuProfile({ profile }: ChengXuProfileProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [height, setHeight] = useState(900)

  useEffect(() => {
    const iframe = iframeRef.current
    if (!iframe) return
    const updateHeight = () => {
      try {
        const doc = iframe.contentDocument
        if (doc?.body) setHeight(doc.body.scrollHeight + 8)
      } catch {
        setHeight(900)
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

  const name = profile.display_name || '程叙'
  const intro = profile.intro?.split('\n\n')[0] || '程叙，二十六岁，你哥哥多年的好友。黑发清爽，眉眼清冷，笑起来却很暖。你和室友闹矛盾，是他一通电话处理妥当；你水土不服，是他默默把常用药放进你的抽屉。'

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#1a1c1e;
  color:#e4dfd8;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;
  padding:0 0 40px;
}
.container{max-width:440px;margin:0 auto}

/* 日记页 —— 纸质奶油卡 + 手写标注 */
.diary-page{
  position:relative;
  margin:0 18px 24px;
  padding:36px 28px 32px;
  background:linear-gradient(155deg,#f5ede3 0%,#ede5da 100%);
  border-radius:3px;
  box-shadow:
    0 2px 8px rgba(0,0,0,.15),
    inset 0 1px 0 rgba(255,255,255,.4);
}
/* 胶带装饰 */
.diary-page::before{
  content:"";
  position:absolute;
  top:-8px;left:50%;
  transform:translateX(-50%) rotate(-2deg);
  width:80px;height:20px;
  background:rgba(208,138,78,.12);
  border-left:1px solid rgba(208,138,78,.2);
  border-right:1px solid rgba(208,138,78,.2);
  box-shadow:inset 0 1px 2px rgba(0,0,0,.05);
}
.diary-page .date-tag{
  position:absolute;
  top:16px;right:24px;
  font-size:10px;
  letter-spacing:.08em;
  color:#a0948a;
  font-weight:600;
}
.diary-page .quote{
  font-family:"Songti SC","STSong",serif;
  font-size:16px;
  line-height:2;
  color:#4a4238;
  margin-bottom:24px;
  position:relative;
  padding-left:18px;
}
.diary-page .quote::before{
  content:"❝";
  position:absolute;
  left:0;top:-6px;
  font-size:32px;
  color:rgba(208,138,78,.25);
  line-height:1;
}
.diary-page .quote em{
  color:#d08a4e;
  font-style:normal;
  background:linear-gradient(transparent 60%,rgba(208,138,78,.15) 60%);
}

/* 便签纸 —— 他记得的事 */
.sticky-note{
  margin:0 18px 20px;
  padding:22px 20px 18px;
  background:#fffae5;
  border-radius:0 3px 3px 0;
  border-left:3px solid #d08a4e;
  box-shadow:
    2px 2px 6px rgba(0,0,0,.12),
    inset 0 1px 0 rgba(255,255,255,.5);
  position:relative;
}
.sticky-note::before{
  content:"📌";
  position:absolute;
  top:-8px;left:12px;
  font-size:18px;
  filter:drop-shadow(1px 1px 2px rgba(0,0,0,.15));
}
.sticky-note .title{
  font-family:"Songti SC",serif;
  font-size:14px;
  font-weight:600;
  color:#6b5e4f;
  margin-bottom:12px;
}
.sticky-note ul{
  list-style:none;
  font-size:13px;
  line-height:1.9;
  color:#7a6d5e;
}
.sticky-note ul li{
  position:relative;
  padding-left:16px;
}
.sticky-note ul li::before{
  content:"✓";
  position:absolute;
  left:0;
  color:#d08a4e;
  font-size:11px;
}

/* Polaroid 照片墙 */
.polaroid-strip{
  margin:0 18px 24px;
  padding:20px;
  background:rgba(42,38,34,.4);
  border:1px solid rgba(208,138,78,.1);
  border-radius:8px;
  display:flex;
  gap:10px;
  align-items:flex-start;
}
.polaroid{
  flex:none;
  width:68px;
  padding:6px 6px 18px;
  background:#f8f6f2;
  box-shadow:0 2px 6px rgba(0,0,0,.25);
  transform:rotate(-3deg);
}
.polaroid:nth-child(2){transform:rotate(2deg)}
.polaroid:nth-child(3){transform:rotate(-4deg)}
.polaroid .img{
  width:100%;
  height:84px;
  background:linear-gradient(135deg,#3a3530,#2a2520);
  filter:blur(8px);
  opacity:.4;
}
.polaroid-strip .lock{
  font-size:20px;
  margin:10px 0 0 4px;
}
.polaroid-strip .caption{
  flex:1;
  font-size:11.5px;
  line-height:1.65;
  color:#b8afa7;
  margin-top:8px;
}

/* 简洁身份卡 */
.profile-simple{
  margin:0 18px 0;
  padding:24px 22px;
  background:rgba(42,38,34,.3);
  border:1px solid rgba(208,138,78,.08);
  border-radius:8px;
}
.profile-simple .name{
  font-family:"Songti SC",serif;
  font-size:22px;
  font-weight:600;
  color:#ede8e3;
  margin-bottom:8px;
}
.profile-simple .subtitle{
  font-size:12px;
  color:#a89f97;
  margin-bottom:16px;
}
.profile-simple .bio{
  font-size:13.5px;
  line-height:1.85;
  color:#b8afa7;
}
</style>
</head>
<body>
<div class="container">

<div class="diary-page">
<span class="date-tag">DAY 247</span>
<p class="quote">
初雪的街角，他把刚出炉的糖炒栗子塞进你手里，替你把围巾拢紧。<br>
<em>"你哥托我照顾你，我答应过他。可有些话……我一直没敢分清，是替他照顾你，还是我自己想。"</em>
</p>
</div>

<div class="sticky-note">
<div class="title">他偷偷记得的事</div>
<ul>
<li>你怕冷，初雪那天他提前在路口等你</li>
<li>你不爱香菜，他每次点餐都会替你挑掉</li>
<li>你熬夜，他会默默把常用药放进抽屉</li>
<li>你随口说过想吃刚出炉的糖炒栗子</li>
</ul>
</div>

<div class="polaroid-strip">
<div class="polaroid"><div class="img"></div></div>
<div class="polaroid"><div class="img"></div></div>
<div class="polaroid"><div class="img"></div></div>
<span class="lock">🔒</span>
<div class="caption">
隐藏相册里全是你：认真听课的侧脸、笑弯的眼睛、没察觉被拍下的每一个瞬间
</div>
</div>

<div class="profile-simple">
<div class="name">${name}</div>
<div class="subtitle">哥哥的朋友 · 把守护过成习惯的人</div>
<p class="bio">${intro}</p>
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
