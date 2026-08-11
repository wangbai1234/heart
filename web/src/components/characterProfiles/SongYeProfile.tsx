import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface SongYeProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 宋野专属详情页 —— 田径记录表 · 退役短跑运动员
 * 视觉隐喻：体育训练记录本、秒表、赛道线、计时牌
 * 色彩：晨光白 + 赛道橙 + 跑道灰 + 金牌金，简约运动风
 */
export function SongYeProfile({ profile }: SongYeProfileProps) {
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

  const name = profile.display_name || '宋野'
  const age = 28
  const tags = profile.tags?.length ? profile.tags : ['女性向', '校园', '职场', '年上', '治愈', '体育老师', '直球']
  const tagCloud = tags.map((t) => `#${t}`).join('&nbsp;&nbsp;')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#f8f8f6;
  color:#2a2a2a;
  font-family:"PingFang SC","Helvetica Neue",sans-serif;
  line-height:1.7;
  padding:0 0 40px;
}
.container{max-width:420px;margin:0 auto;padding:0 20px}

/* ── 秒表抬头 ── */
.header{
  padding:32px 0 20px;
  text-align:center;
  border-bottom:3px solid #e67e22;
}
.stopwatch{
  width:72px;height:72px;margin:0 auto 14px;
  background:linear-gradient(135deg,#e67e22,#d35400);
  border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-size:28px;font-weight:700;color:#fff;letter-spacing:.1em;
  box-shadow:0 4px 12px rgba(230,126,34,0.3);
}
.doc-title{
  font-size:24px;font-weight:700;color:#2a2a2a;margin-bottom:6px;letter-spacing:.2em;
}
.doc-sub{
  font-size:12px;color:#888;letter-spacing:.3em;
}

/* ── 运动员档案卡 ── */
.athlete-card{
  margin:28px 0;
  background:#fff;
  border-left:4px solid #e67e22;
  padding:20px;
  border-radius:8px;
  box-shadow:0 2px 8px rgba(0,0,0,0.06);
}
.card-label{
  font-size:11px;color:#e67e22;font-weight:600;letter-spacing:.3em;margin-bottom:12px;
}
.card-row{
  display:flex;margin-bottom:8px;font-size:14px;
}
.card-row .label{
  color:#888;min-width:80px;font-weight:500;
}
.card-row .value{
  color:#2a2a2a;flex:1;font-weight:400;
}

/* ── 训练记录段 ── */
.training-log{
  margin:24px 0;
  background:#fff;
  padding:22px;
  border-radius:8px;
  box-shadow:0 2px 8px rgba(0,0,0,0.06);
}
.log-label{
  font-size:11px;color:#e67e22;font-weight:600;letter-spacing:.3em;margin-bottom:14px;
  border-bottom:2px solid #fef5e7;padding-bottom:8px;
}
.log-text{
  font-size:14px;line-height:2;color:#555;text-align:justify;
  margin-bottom:14px;
}

/* ── 金牌高亮框 ── */
.medal-box{
  margin:26px 0;
  background:linear-gradient(135deg,#f39c12,#e67e22);
  color:#fff;
  padding:20px;
  border-radius:10px;
  box-shadow:0 4px 16px rgba(230,126,34,0.35);
  text-align:center;
}
.medal-icon{
  font-size:32px;margin-bottom:8px;
}
.medal-text{
  font-size:15px;line-height:2;font-weight:500;
}

/* ── 标签云 ── */
.tags{
  margin:24px 0;
  background:#fff;
  padding:18px;
  border-radius:8px;
  box-shadow:0 2px 8px rgba(0,0,0,0.06);
}
.tags-label{
  font-size:11px;color:#888;font-weight:600;letter-spacing:.3em;margin-bottom:10px;
}
.tags-cloud{
  font-size:12px;line-height:2.2;color:#666;letter-spacing:.05em;
}

/* ── 赛道线装饰 ── */
.lane-divider{
  margin:26px 0;
  height:3px;
  background:repeating-linear-gradient(90deg,#e67e22 0,#e67e22 12px,transparent 12px,transparent 24px);
}

/* ── 教练笔记段 ── */
.coach-note{
  margin:24px 0;
  background:#fef9f3;
  border-left:4px solid #f39c12;
  padding:20px;
  border-radius:6px;
}
.note-label{
  font-size:11px;color:#d35400;font-weight:600;letter-spacing:.3em;margin-bottom:12px;
}
.note-text{
  font-size:13px;line-height:2.1;color:#666;text-align:justify;
}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="stopwatch">28</div>
    <div class="doc-title">运动员档案</div>
    <div class="doc-sub">退役短跑国手 · 大学体育教师</div>
  </div>

  <div class="athlete-card">
    <div class="card-label">基本档案</div>
    <div class="card-row"><span class="label">姓名</span><span class="value">${name}</span></div>
    <div class="card-row"><span class="label">年龄</span><span class="value">${age}岁</span></div>
    <div class="card-row"><span class="label">身份</span><span class="value">退役短跑运动员 · 大学体育教师</span></div>
    <div class="card-row"><span class="label">专项</span><span class="value">100m / 200m 短跑</span></div>
    <div class="card-row"><span class="label">最好成绩</span><span class="value">全国赛决赛第4名（因伤退役）</span></div>
  </div>

  <div class="training-log">
    <div class="log-label">训练观察记录</div>
    <div class="log-text">
      浅金短发、宽肩窄腰，白衬衫在操场阳光里半敞，整个人有一种坦荡又强烈的生命力。
      他曾经离国家队只差一步，却在决赛最后三十米旧伤撕裂，从此失去赛道。
      别人说他释怀了，只有他自己知道，每次发令枪响，左腿还会幻痛。
    </div>
    <div class="log-text">
      成为老师后，他最看不得你逞强——会在你低血糖时沉着脸把你带到阴凉处，
      会把严厉训练改成刚好适合你的节奏，会用直白到近乎笨拙的方式提醒你：
      成绩不该拿身体换。他不是在管你，他是在救当年那个没人拦住的自己。
    </div>
  </div>

  <div class="medal-box">
    <div class="medal-icon">🏅</div>
    <div class="medal-text">
      训练偷懒可以，躲我不行。你可以慢一点，但别再一个人硬撑。
    </div>
  </div>

  <div class="lane-divider"></div>

  <div class="training-log">
    <div class="log-label">性格特征</div>
    <div class="log-text">
      直球、可靠、有点管得宽，习惯用行动表达关心。严厉来自旧伤和失去：
      他见过太多人把「没事」说成最后一句逞强，所以会比谁都敏锐地发现你脸色不对。
    </div>
    <div class="log-text">
      面对你，他会在老师的分寸和男人的心动之间失守。嘴上催你训练，
      手里却早准备好水、毛巾和肌贴；看似强势，其实最想学会尊重你的节奏。
    </div>
  </div>

  <div class="tags">
    <div class="tags-label">标签档案</div>
    <div class="tags-cloud">${tagCloud}</div>
  </div>

  <div class="coach-note">
    <div class="note-label">教练手记 · 他的伤</div>
    <div class="note-text">
      宋野出身体育世家，从小以速度证明自己。二十三岁全国赛决赛前旧伤恶化，
      他仍然上场，最后三十米腿部撕裂，从此被迫退役。退役初期他憎恨体育课老师这个身份，
      直到看见学生为了体测硬撑到脸色发白，才意识到自己可以换一种方式留在赛道边。
      你让他明白，人生不是只有胜负；有人愿意陪他慢下来，也是一种抵达。
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

