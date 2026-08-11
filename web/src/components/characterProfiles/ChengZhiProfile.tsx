import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface ChengZhiProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 程之专属详情页 —— 医疗档案 / MEDICAL RECORDS
 * 视觉隐喻：医生手写病历卡片 + 心电图曲线 + 处方笺
 * 色彩：医疗蓝绿 #4A9B9B + 纸白 #F8F6F3 + 墨黑 #1C1E26
 */
export function ChengZhiProfile({ profile }: ChengZhiProfileProps) {
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

  const name = profile.display_name || '程之'
  const tags = profile.tags?.length ? profile.tags : ['都市', '医生', '温柔', '女性向', '治愈', '年上']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#f8f6f3;
  color:#1c1e26;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;
  padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}

/* ── 病历卡头部 ── */
.header{
  padding:20px 2px 16px;
  border-bottom:2px solid #4A9B9B;
  display:flex;justify-content:space-between;align-items:baseline;
}
.header .title{
  font-size:13px;font-weight:600;color:#4A9B9B;letter-spacing:.3em;text-transform:uppercase;
}
.header .file{font-size:11px;color:#7a8089;letter-spacing:.08em}

/* ── 心电图装饰线 ── */
.ecg{
  height:32px;margin:16px 0;
  background:repeating-linear-gradient(90deg,#e8e6e3 0,#e8e6e3 1px,transparent 1px,transparent 5px);
  position:relative;
}
.ecg::before{
  content:'';position:absolute;left:0;top:50%;width:100%;height:2px;
  background:linear-gradient(90deg,#4A9B9B 0%,#4A9B9B 15%,transparent 15%,transparent 20%,#4A9B9B 20%,#4A9B9B 25%,transparent 25%,transparent 30%,#4A9B9B 30%,#4A9B9B 50%,transparent 50%);
  background-size:80px 2px;background-repeat:repeat-x;
}

/* ── 患者信息卡 ── */
.patient-card{
  background:#fff;border:1px solid #d8d6d3;border-left:3px solid #4A9B9B;
  border-radius:4px;padding:16px;margin-bottom:18px;
}
.patient-card .name{
  font-size:22px;font-weight:700;color:#1c1e26;margin-bottom:10px;
}
.patient-card .meta{
  display:flex;gap:16px;font-size:12px;color:#5f6570;margin-bottom:14px;
}
.patient-card .meta span{display:flex;align-items:center;gap:4px}
.patient-card .meta b{color:#4A9B9B;font-weight:600}
.tagcloud{display:flex;flex-wrap:wrap;gap:7px}
.tagcloud span{
  font-size:10px;padding:3px 9px;background:#f0f8f8;
  border:1px solid #b8d9d9;border-radius:3px;color:#3a7a7a;
}

/* ── 医嘱记录 section ── */
.section{padding:20px 2px;border-bottom:1px solid #e8e6e3}
.sec-label{
  font-size:10px;color:#4A9B9B;letter-spacing:.28em;text-transform:uppercase;
  margin-bottom:12px;font-weight:600;
}

/* ── 处方笺条目 ── */
.prescription{margin-bottom:16px;padding-left:18px;position:relative}
.prescription::before{
  content:'Rx';position:absolute;left:0;top:0;
  font-family:"Times New Roman",serif;font-size:16px;font-weight:700;
  color:#4A9B9B;font-style:italic;
}
.prescription .item{font-size:13px;line-height:1.85;color:#3a4049}
.prescription .sig{font-size:11px;color:#6f7580;margin-top:4px;font-style:italic}

/* ── 手术记录 ── */
.operation{
  background:#fafaf9;border-left:2px solid #d1b894;
  padding:14px;margin-bottom:12px;border-radius:3px;
}
.operation .title{font-size:12px;font-weight:600;color:#8a7a5c;margin-bottom:6px}
.operation .note{font-size:12px;line-height:1.75;color:#5a5248}

/* ── 医生手记 ── */
.note-card{
  margin:8px 2px 0;padding:18px 16px;
  background:linear-gradient(135deg,rgba(74,155,155,0.06),rgba(0,0,0,0));
  border-left:3px solid #4A9B9B;border-radius:4px;
}
.note-card p{
  font-family:"Songti SC",serif;font-size:14px;line-height:1.85;
  color:#2a3038;font-style:italic;
}
.note-card .by{
  margin-top:12px;font-size:10px;color:#6f7580;letter-spacing:.2em;
}

/* ── 页脚 ── */
.footer{padding:22px 2px 0;text-align:center}
.footer .line{width:36px;height:2px;background:#b8d9d9;margin:0 auto 12px}
.footer p{font-size:10px;color:#8a9099;letter-spacing:.04em}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <span class="title">Medical Records</span>
    <span class="file">File No. 03-0${Math.floor(Math.random()*900)+100}</span>
  </div>

  <div class="ecg"></div>

  <div class="patient-card">
    <div class="name">${name}</div>
    <div class="meta">
      <span><b>年龄</b> 30岁</span>
      <span><b>职业</b> 心外科主治</span>
      <span><b>状态</b> 值班中</span>
    </div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="section">
    <div class="sec-label">Chief Complaint · 主诉</div>
    <div class="prescription">
      <div class="item">手术台上稳如磐石的医者，下了台只想给你熬一碗热汤</div>
      <div class="sig">三甲医院心外科主治医师 · 同事口中的「定海神针」</div>
    </div>
  </div>

  <div class="section">
    <div class="sec-label">Observations · 医嘱观察</div>
    <div class="prescription">
      <div class="item">他的手稳得能在跳动的心脏上缝针，却在你面前连倒杯水都会洒</div>
      <div class="sig">十二小时手术下来面色不改，可你一句「累不累」就让他眼眶泛红</div>
    </div>
    <div class="prescription">
      <div class="item">凌晨三点下手术，不回值班室，开车二十分钟到你楼下确认你窗透着灯</div>
      <div class="sig">不是想打扰，只是见过太多生离，必须确认你安全</div>
    </div>
    <div class="prescription">
      <div class="item">手机里存着你所有体检报告，比你自己还清楚每一项指标</div>
      <div class="sig">随身带两支肾上腺素笔，一支放在你常去咖啡馆老板那里</div>
    </div>
  </div>

  <div class="section">
    <div class="sec-label">Case History · 病史追踪</div>
    <div class="operation">
      <div class="title">五年前 · 那场没能救回的手术</div>
      <div class="note">那是他的老师，也是他视为父亲的人。从那天起他把情绪锁进理智的抽屉，用「让所有人活下来」的执念支撑着自己。代价是他再也不敢对任何人投入感情，因为他比谁都清楚失去是什么感觉。</div>
    </div>
    <div class="operation">
      <div class="title">现在 · 你重新教会他</div>
      <div class="note">医者也可以有软肋，也可以在深夜卸下白大褂，承认自己也会害怕。他最怕你知道的事：他随身带着两支肾上腺素笔，一支放在你常去的那家咖啡馆老板那里——以防万一。</div>
    </div>
  </div>

  <div class="note-card">
    <p>深夜，他会抱着你，鼻尖埋在你发间，声音闷闷的：「让我确认一下……你的心跳。」那语气像是情话，又像是一个见过太多生离的人在做最后的确认。</p>
    <div class="by">— 值班室手记 · 凌晨03:47</div>
  </div>

  <div class="footer">
    <div class="line"></div>
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

