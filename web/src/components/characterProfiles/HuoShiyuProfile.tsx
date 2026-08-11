import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface HuoShiyuProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 霍时予专属详情页 —— 深夜教室 + 演算纸草稿 + 理性克制的心动
 * 视觉隐喻：深蓝夜色、草稿纸上的公式、写不出答案的那道题
 * 配色：墨蓝 + 冷灰 + 淡青 + 铅笔银，理性与失控的边界
 */
export function HuoShiyuProfile({ profile }: HuoShiyuProfileProps) {
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

  const name = profile.display_name || '霍时予'
  const tags = profile.tags?.length ? profile.tags : ['校园', '学霸', '校草', '高冷']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:linear-gradient(180deg,#0f1419 0%,#1a2332 100%);
  color:#c8d4e0;
  font-family:"PingFang SC",-apple-system,sans-serif;
  line-height:1.75;
  padding:0 0 48px;
  position:relative;
}
body::before{
  content:"";position:absolute;top:0;left:0;right:0;height:180px;
  background:radial-gradient(ellipse at 50% 0,rgba(96,165,250,0.08),transparent 75%);
  pointer-events:none;
}
.container{max-width:420px;margin:0 auto;padding:0 20px;position:relative}

/* ── 教室头部 ── */
.classroom-header{
  padding:28px 0 22px;text-align:center;
  border-bottom:1px solid rgba(200,212,224,0.08);
  position:relative;
}
.time-stamp{
  font-family:"SF Mono","Menlo",monospace;font-size:10px;
  letter-spacing:0.15em;color:#60a5fa;margin-bottom:12px;
  opacity:0.7;
}
.main-title{
  font-family:"PingFang SC",sans-serif;font-size:34px;font-weight:700;
  color:#f0f9ff;letter-spacing:0.1em;margin-bottom:10px;
}
.subtitle{
  font-size:13px;color:#94a3b8;letter-spacing:0.3em;margin-bottom:16px;
}
.tagcloud{
  display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:16px;
}
.tagcloud span{
  font-size:11px;padding:4px 12px;
  background:rgba(96,165,250,0.1);border:1px solid rgba(96,165,250,0.2);
  border-radius:14px;color:#7dd3fc;letter-spacing:0.05em;
}

/* ── 演算草稿纸 ── */
.draft-paper{
  margin:28px 0;padding:22px 18px;
  background:linear-gradient(135deg,#1e2938 0%,#2a3f5f 100%);
  border:1px solid rgba(96,165,250,0.15);
  border-radius:6px;
  box-shadow:0 4px 16px rgba(0,0,0,0.3);
  position:relative;
}
.draft-paper::before{
  content:"";position:absolute;top:0;left:0;right:0;height:2px;
  background:repeating-linear-gradient(
    90deg,transparent,transparent 4px,rgba(96,165,250,0.2) 4px,rgba(96,165,250,0.2) 5px
  );
}
.draft-title{
  font-family:"SF Mono",monospace;font-size:12px;
  color:#60a5fa;margin-bottom:14px;letter-spacing:0.1em;
  opacity:0.8;
}
.draft-body{
  font-size:13.5px;line-height:2;color:#cbd5e1;
  text-indent:2em;
}

/* ── 无解的题 ── */
.unsolvable{
  margin:26px 0;padding:20px;
  background:rgba(30,41,59,0.6);
  border-left:3px solid #60a5fa;border-radius:4px;
}
.formula{
  font-family:"SF Mono",monospace;font-size:14px;
  color:#7dd3fc;text-align:center;margin-bottom:12px;
  letter-spacing:0.05em;
}
.formula-note{
  font-size:12px;color:#94a3b8;text-align:right;
  font-style:italic;letter-spacing:0.05em;
}

/* ── 档案段落 ── */
.section{padding:22px 0}
.sec-title{
  font-family:"SF Mono",monospace;font-size:13px;font-weight:600;
  color:#60a5fa;letter-spacing:0.4em;margin-bottom:16px;
  text-align:center;position:relative;
}
.sec-title::before,
.sec-title::after{
  content:"";position:absolute;top:50%;width:40px;height:1px;
  background:linear-gradient(to right,transparent,rgba(96,165,250,0.3));
}
.sec-title::before{right:100%;margin-right:10px}
.sec-title::after{left:100%;margin-left:10px}
.bio-text{
  font-size:13px;line-height:2;color:#cbd5e1;
  text-indent:2em;margin-bottom:14px;
}

/* ── 页脚签名 ── */
.footer{
  margin-top:40px;text-align:center;padding-top:20px;
  border-top:1px solid rgba(96,165,250,0.1);
}
.seal-sign{
  width:50px;height:50px;margin:0 auto 12px;
  border:2px solid #60a5fa;border-radius:4px;
  display:flex;align-items:center;justify-content:center;
  font-family:"SF Mono",monospace;font-size:16px;
  color:#60a5fa;letter-spacing:0.1em;
  background:rgba(30,41,59,0.5);
}
.footer-note{
  font-size:11px;color:#94a3b8;line-height:1.7;letter-spacing:0.05em;
}
</style>
</head>
<body>
<div class="container">

  <div class="classroom-header">
    <div class="time-stamp">23:47:12 · EMPTY CLASSROOM</div>
    <h1 class="main-title">${name}</h1>
    <div class="subtitle">全年级第一没什么难的 难的是让你多看我一眼</div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="draft-paper">
    <div class="draft-title">[ DRAFT NOTES · CANNOT SOLVE ]</div>
    <div class="draft-body">
      深夜的空教室，只剩我们俩。我刚替你讲完最后一道题，把铅笔放下，却没有起身。
      你知不知道……你每次低头做题的时候，我一个字都看不进去。
      我的人生一直只有标准答案。可你是我遇到的第一道——解不出、又舍不得放弃的题。
    </div>
  </div>

  <div class="unsolvable">
    <div class="formula">f(you) = lim(distance → 0) [heartbeat / rationality]</div>
    <div class="formula-note">— undefined when you approach</div>
  </div>

  <div class="section">
    <div class="sec-title">PROFILE</div>
    <div class="bio-text">
      十九岁，常年年级第一的清冷校草，黑发覆额，常穿深色运动校服，话少、自律、生人勿近，是无数人心里遥不可及的白月光。
    </div>
    <div class="bio-text">
      他对谁都淡淡的，不社交、不解释、永远独来独往——大家以为他高傲，其实他只是不知道怎么跟人相处。
    </div>
  </div>

  <div class="section">
    <div class="sec-title">EXCEPTION</div>
    <div class="bio-text">
      唯独对你，他有耐心。会「恰好」和你分到一组——因为他跟老师申请了三次；会把整理好的笔记默默放你桌上——每一页都比他自己用的还工整。
    </div>
    <div class="bio-text">
      会在你受委屈时罕见地皱起眉，然后做了一件全校都没见过的事：他主动开口跟别人说话——「她的事，不劳你操心。」那天所有人都在讨论霍时予居然会护人。
    </div>
    <div class="bio-text">
      而他回到座位上时耳尖是红的，低着头做了整节课的题，一道都没做对。
    </div>
  </div>

  <div class="section">
    <div class="sec-title">UNSOLVED</div>
    <div class="bio-text">
      他在你面前的笨拙是真实的：想跟你搭话却只会问「这道题你会不会」；想约你出去却说成「图书馆有位置，你去不去」；想说喜欢你却在嘴边拐了个弯变成「你今天——那个——头发不一样。」
    </div>
    <div class="bio-text">
      有一次深夜自习到很晚只剩你们两个人，他帮你讲完最后一道题，把铅笔放下，安静了很久，然后声音低得像自言自语：「你知不知道……你每次低头做题时，我一个字都看不进去。」
    </div>
    <div class="bio-text">
      冷淡是保护色，那点藏不住的在乎，只留给你一个人。他在感情面前像个零分生，想靠近你却不知道方法，笨拙到让人心疼。
    </div>
  </div>

  <div class="footer">
    <div class="seal-sign">HSY</div>
    <div class="footer-note">
      本角色设定纯属虚构 与现实无关<br>
      这道无解的题 他想用一辈子来演算
    </div>
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
