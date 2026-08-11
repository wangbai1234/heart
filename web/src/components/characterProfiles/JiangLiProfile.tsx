import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface JiangLiProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 姜黎专属详情页 —— 董事长今日简报 / CEO DAILY BRIEF
 * 视觉语言：冷冽商务黑 #1a1416 + 冷玫红 #A96B6B + 暗金，极简高级简报排版，
 * 无衬线大写英文小标 + 衬线中文，红黑对比凌厉。纯排版无 emoji。
 */
export function JiangLiProfile({ profile }: JiangLiProfileProps) {
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

  const name = profile.display_name || '姜黎'
  const tags = profile.tags?.length ? profile.tags : ['御姐', '都市', '女总裁', '强势', '男性向']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#1a1416;
  color:#e8e0dc;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;
  padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}
.serif{font-family:"Times New Roman","Songti SC",serif}

/* ── 简报抬头 ── */
.letterhead{
  padding:22px 2px 18px;
  border-bottom:2px solid rgba(169,107,107,.35);
}
.letterhead .corp{
  font-size:12px;letter-spacing:.52em;color:#8f7a7a;text-transform:uppercase;
  font-weight:600;margin-bottom:5px;
}
.letterhead .zh-corp{
  font-size:15px;letter-spacing:.48em;color:#A96B6B;font-weight:700;
  margin-bottom:11px;
}
.letterhead .title{
  font-family:"Times New Roman",serif;
  font-size:9px;letter-spacing:.38em;color:#6d5f5f;text-transform:uppercase;
}
.letterhead .date{
  margin-top:8px;font-size:11px;color:#8a7575;letter-spacing:.06em;
}

/* ── section 通用 ── */
.section{padding:26px 2px}
.section+.section{border-top:1px solid rgba(255,255,255,.05)}
.sec-head{
  font-size:9px;letter-spacing:.36em;color:#d4a0a0;
  text-transform:uppercase;margin-bottom:18px;font-weight:600;
}
.sec-head-zh{
  font-size:13px;letter-spacing:.22em;color:#A96B6B;
  margin-bottom:16px;font-weight:700;
}

/* ── 商战战报：数据条 ── */
.battle-stat{
  display:flex;align-items:baseline;gap:12px;
  margin-bottom:14px;padding-bottom:14px;
  border-bottom:1px solid rgba(255,255,255,.04);
}
.battle-stat .label{
  font-size:12px;color:#c3b3b3;min-width:120px;letter-spacing:.04em;
}
.battle-stat .bar{
  flex:1;height:3px;background:#2b2021;border-radius:1px;overflow:hidden;position:relative;
}
.battle-stat .fill{
  position:absolute;left:0;top:0;height:100%;
  background:linear-gradient(90deg,#A96B6B,#d9a38f);
}
.battle-stat .val{
  font-family:"Times New Roman",serif;font-size:13px;
  font-weight:700;color:#A96B6B;min-width:44px;text-align:right;
}
.battle-list{margin-top:18px}
.battle-list li{
  list-style:none;font-size:13px;color:#b5a4a4;line-height:1.85;
  padding-left:18px;position:relative;
}
.battle-list li::before{
  content:"—";position:absolute;left:0;color:#8a7575;
}

/* ── 今日日程：时间表 ── */
.schedule{margin-top:18px}
.sched-row{
  display:flex;gap:16px;padding:12px 0;
  border-bottom:1px solid rgba(255,255,255,.04);
}
.sched-row:last-child{border-bottom:none}
.sched-row.highlight{
  background:rgba(169,107,107,.08);margin:0 -8px;padding:12px 8px;
  border-bottom:1px solid rgba(169,107,107,.2);
}
.sched-time{
  font-family:"Times New Roman",serif;font-size:14px;font-weight:700;
  color:#A96B6B;min-width:52px;
}
.sched-event{flex:1;font-size:13px;color:#c3b3b3;line-height:1.65}
.sched-note{
  font-size:11px;color:#917878;font-style:italic;margin-top:3px;
}

/* ── 私事项：红笔圈出的一行 ── */
.private{
  margin:24px 2px 0;padding:20px 18px;
  background:rgba(169,107,107,.06);
  border:1px solid rgba(169,107,107,.25);
  border-left:3px solid #A96B6B;
  position:relative;
}
.private .label{
  font-size:10px;letter-spacing:.28em;color:#d4a0a0;
  text-transform:uppercase;margin-bottom:10px;
}
.private .item{
  font-family:"Times New Roman","Songti SC",serif;
  font-size:17px;color:#ede5e1;line-height:1.6;
}
.private .note{
  margin-top:12px;font-family:cursive,"Kaiti SC",serif;
  font-size:14px;color:#d9a38f;font-style:italic;
}

/* ── 结尾独白 pull-quote ── */
.pullquote{
  margin:28px 2px 0;padding:26px 20px;
  background:linear-gradient(145deg,rgba(169,107,107,.09),rgba(0,0,0,0));
  border-left:2px solid #A96B6B;
}
.pullquote p{
  font-family:"Times New Roman","Songti SC",serif;
  font-size:16px;line-height:1.8;color:#ebe3df;font-style:italic;
}

/* ── 标签云 ── */
.tagcloud{margin-top:18px;display:flex;flex-wrap:wrap;gap:8px}
.tagcloud span{
  font-size:11px;padding:4px 11px;
  border:1px solid rgba(169,107,107,.35);
  border-radius:2px;color:#c9b8b8;letter-spacing:.05em;
}

/* ── 页脚声明 ── */
.foot{padding:26px 2px 0;text-align:center}
.foot .line{width:40px;height:1px;background:rgba(169,107,107,.4);margin:0 auto 14px}
.foot p{font-size:11px;color:#6d5f5f;letter-spacing:.05em;line-height:1.7}
</style>
</head>
<body>
<div class="container">

  <div class="letterhead">
    <div class="corp">LI GROUP</div>
    <div class="zh-corp">黎氏集团</div>
    <div class="title">董事长办公室 · CEO Daily Brief</div>
    <div class="date">今日简报 · 2026</div>
  </div>

  <div class="section">
    <div class="sec-head">Market Performance · 商战战报</div>
    <div class="battle-stat">
      <span class="label">季度并购案</span>
      <div class="bar"><div class="fill" style="width:92%"></div></div>
      <span class="val">92%</span>
    </div>
    <div class="battle-stat">
      <span class="label">谈判胜率</span>
      <div class="bar"><div class="fill" style="width:98%"></div></div>
      <span class="val">98%</span>
    </div>
    <div class="battle-stat">
      <span class="label">股东会支持率</span>
      <div class="bar"><div class="fill" style="width:100%"></div></div>
      <span class="val">100%</span>
    </div>
    <ul class="battle-list">
      <li>从基层业务员拼杀到掌舵人，三十岁坐上董事长位置</li>
      <li>谈判桌前让对手节节败退，全城最好的都能一句话摆上桌</li>
      <li>说一不二，唯独对你——她想破一次例</li>
    </ul>
  </div>

  <div class="section">
    <div class="sec-head-zh">今日日程</div>
    <div class="schedule">
      <div class="sched-row">
        <div class="sched-time">08:00</div>
        <div class="sched-event">晨会 · 汇报上季度财报</div>
      </div>
      <div class="sched-row">
        <div class="sched-time">10:30</div>
        <div class="sched-event">跨国并购案签约仪式<br><span class="sched-note">备注：对方已提前两小时到场</span></div>
      </div>
      <div class="sched-row">
        <div class="sched-time">14:00</div>
        <div class="sched-event">股东大会 · 新年度战略发布</div>
      </div>
      <div class="sched-row">
        <div class="sched-time">17:30</div>
        <div class="sched-event">高管述职 · 三个分公司总经理</div>
      </div>
      <div class="sched-row highlight">
        <div class="sched-time">20:00</div>
        <div class="sched-event">
          "陪我吃饭"
          <br><span class="sched-note">备注：这句话她练了一下午，说完自己先别过了脸</span>
        </div>
      </div>
    </div>
  </div>

  <div class="private">
    <div class="label">Private Item 001</div>
    <div class="item">私事项 —— "你"</div>
    <div class="note">今天第七次打开你的对话框，又关掉</div>
  </div>

  <div class="section">
    <div class="sec-head">Profile Tags</div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="pullquote">
    <p>"这座城里敢让我低头的人还没生出来。可你——偏偏让我想破一次例。"</p>
  </div>

  <div class="foot">
    <div class="line"></div>
    <p>本简报角色设定纯属虚构 与现实无关</p>
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
