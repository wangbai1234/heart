import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface YinCiProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 殷辞专属详情页 —— 血族审判庭·事件报告 / INCIDENT REPORT
 * 蒙眼血族，在人类女孩设下的猎局里甘愿被捕。
 * 视觉语言：焦黑底+血红+铬银，事件报告/监控日志格式，
 * 等宽字体时间戳+手写批注反差，冷硬档案 vs 情感泄漏。
 */
export function YinCiProfile({ profile }: YinCiProfileProps) {
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

  const name = profile.display_name || '殷辞'
  const tags = profile.tags?.length ? profile.tags : ['血族', '暗黑', '校园', '初拥']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#0b0909;
  color:#d0c8c4;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}
.mono{font-family:"SF Mono","Menlo",monospace}
.serif{font-family:"Times New Roman","Songti SC",serif}

/* ── 报告抬头 ── */
.header{
  padding:22px 0 16px;
  border-bottom:2px solid rgba(184,48,48,.35);
}
.header .stamp{
  font-size:9px;letter-spacing:.35em;color:#b83030;
  text-transform:uppercase;font-weight:700;margin-bottom:4px;
}
.header .file-no{
  font-family:"SF Mono","Menlo",monospace;
  font-size:22px;font-weight:700;color:#e0d4d0;
  letter-spacing:.08em;margin-bottom:6px;
}
.header .meta{
  font-size:11px;color:#6a6260;letter-spacing:.06em;
}

/* ── 对象档案 ── */
.subject{
  margin-top:20px;padding:20px 18px;border-radius:4px;
  background:rgba(20,16,15,.8);border:1px solid rgba(184,48,48,.2);
  position:relative;overflow:hidden;
}
.subject::before{
  content:"CLASSIFIED";position:absolute;top:12px;right:-28px;
  transform:rotate(38deg);font-size:8px;letter-spacing:.2em;
  color:rgba(184,48,48,.35);border:1px solid rgba(184,48,48,.25);
  padding:2px 30px;
}
.subject .h{
  font-size:10px;letter-spacing:.3em;color:#b83030;
  text-transform:uppercase;margin-bottom:14px;font-weight:600;
}
.s-row{
  display:flex;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:13px;
}
.s-row:last-child{border-bottom:none}
.s-row .k{min-width:56px;color:#6a6260;letter-spacing:.06em}
.s-row .v{color:#c8beb8;flex:1}

/* ── 事件时间线 ── */
.timeline{margin-top:22px}
.timeline .h{
  font-size:10px;letter-spacing:.3em;color:#888c90;
  text-transform:uppercase;margin-bottom:16px;font-weight:600;
}
.event{
  display:flex;gap:14px;padding:14px 0;
  border-bottom:1px solid rgba(255,255,255,.04);
}
.event:last-child{border-bottom:none}
.event .ts{
  font-family:"SF Mono","Menlo",monospace;
  font-size:12px;color:#b83030;min-width:48px;font-weight:600;
}
.event .desc{font-size:13px;line-height:1.75;color:#a8a0a0}
.event .desc b{color:#d8ccc8;font-weight:600}

/* ── 证据项 ── */
.evidence{
  margin-top:22px;padding:20px 18px;border-radius:4px;
  background:rgba(16,12,12,.7);border:1px solid rgba(255,255,255,.06);
}
.evidence .h{
  font-size:10px;letter-spacing:.3em;color:#888c90;
  text-transform:uppercase;margin-bottom:14px;font-weight:600;
}
.ev-item{
  padding:10px 0;border-bottom:1px solid rgba(255,255,255,.04);
  font-size:12.5px;line-height:1.7;color:#a09898;
  padding-left:16px;position:relative;
}
.ev-item:last-child{border-bottom:none}
.ev-item::before{
  content:"";position:absolute;left:0;top:18px;
  width:6px;height:6px;border-radius:50%;
  background:#b83030;
}

/* ── 手写批注（情感泄漏） ── */
.annotation{
  margin:24px 0;padding:20px 18px;
  border-top:1px dashed rgba(184,48,48,.2);
  background:linear-gradient(180deg,rgba(184,48,48,.04),transparent);
}
.annotation .label{
  font-family:"Kaiti SC",cursive;
  font-size:12px;color:#b83030;font-style:italic;
  margin-bottom:12px;letter-spacing:.1em;
}
.annotation p{
  font-family:"Kaiti SC",cursive;
  font-size:13px;line-height:2;color:#c0a8a8;font-style:italic;
  margin-bottom:8px;
}

/* ── 结尾 pull-quote ── */
.pullquote{
  margin:20px 2px 0;padding:24px 20px;
  background:linear-gradient(145deg,rgba(184,48,48,.08),transparent);
  border-left:2px solid #b83030;border-radius:4px;
}
.pullquote p{
  font-family:"Times New Roman","Songti SC",serif;
  font-size:16px;line-height:1.8;color:#e0d4d0;font-style:italic;
}
.pullquote .by{
  margin-top:12px;font-size:9px;letter-spacing:.25em;color:#6a6260;text-align:right;
}

/* ── 标签+页脚 ── */
.tagcloud{margin-top:18px;display:flex;flex-wrap:wrap;gap:8px}
.tagcloud span{
  font-size:11px;padding:4px 10px;
  border:1px solid rgba(184,48,48,.3);border-radius:2px;
  color:#b0a4a0;letter-spacing:.05em;
}
.foot{padding:24px 2px 0;text-align:center}
.foot .line{width:40px;height:1px;background:rgba(184,48,48,.35);margin:0 auto 12px}
.foot p{font-size:10px;color:#5a5250;letter-spacing:.04em}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="stamp">Vampire Tribunal · Incident Report</div>
    <div class="file-no">X-0091</div>
    <div class="meta">血族审判庭 · 人类介入事件 · 等级：未定</div>
  </div>

  <div class="subject">
    <div class="h">Subject Profile · 对象档案</div>
    <div class="s-row"><span class="k">真名</span><span class="v">${name}</span></div>
    <div class="s-row"><span class="k">血统</span><span class="v">未标注 · 档案已被最高议会封存</span></div>
    <div class="s-row"><span class="k">外形</span><span class="v">红银双色发 · 绷带覆眼 · 颈侧星月纹 · 唇钉</span></div>
    <div class="s-row"><span class="k">特征</span><span class="v">气场压制 · 高年级血族本能后退</span></div>
    <div class="s-row"><span class="k">食性</span><span class="v">合成血 · 从未猎食人类（记录内）</span></div>
  </div>

  <div class="timeline">
    <div class="h">Incident Timeline · 事件时间线</div>
    <div class="event">
      <span class="ts">D+01</span>
      <div class="desc"><b>人类转学生入学。</b>入校第一天选择坐在血族女生团体正对面，目光直视，心跳平稳。异常。</div>
    </div>
    <div class="event">
      <span class="ts">D+07</span>
      <div class="desc">转学生多次在走廊<b>故意露出颈侧脉搏</b>，经过对象常驻区域时步伐放慢。对象首次出现追踪行为。</div>
    </div>
    <div class="event">
      <span class="ts">D+14</span>
      <div class="desc">转学生<b>刻意招惹血族女生团体</b>，挑衅动作经计算、非冲动。推测目的：制造需要对象介入的场景。</div>
    </div>
    <div class="event">
      <span class="ts">D+21</span>
      <div class="desc">血族女生将转学生堵至废弃车站B2月台。<b>对象介入，释放气场，三名血族逃离。</b>转学生向对象伸出双手，要求"初拥"。</div>
    </div>
  </div>

  <div class="evidence">
    <div class="h">Evidence Notes · 证据备注</div>
    <div class="ev-item">她的心跳从入学第一天起就没有恐惧波动。她知道自己在做什么。</div>
    <div class="ev-item">她的血液气味异常——不是"好闻"能概括的，是让他在百米外就能锁定的特殊频率。</div>
    <div class="ev-item">她每次经过废弃车站都会故意停留三秒。她知道他在那里。</div>
    <div class="ev-item">对象蒙眼绷带为自愿行为，非伤残。其血族视觉能力远超常规，绷带是自我克制手段。</div>
  </div>

  <div class="annotation">
    <div class="label">── 非公开批注 · 手写 ──</div>
    <p>她朝我伸手的时候，心跳终于快了。不是因为害怕。</p>
    <p>初拥意味着绑定、永远、不可撤回。她把这句话说得像念了一万遍——她真的练过一万遍。</p>
    <p>我看不见她的表情。但我闻得到她在笑。从第一天开始，她就在笑。</p>
  </div>

  <div class="pullquote">
    <p>「你确定要把自己交给一个连自己长什么样都不知道的怪物？」</p>
    <div class="by">── ${name} · 废弃车站 B2 月台</div>
  </div>

  <div class="tagcloud">${tagCloud}</div>
  <div class="foot">
    <div class="line"></div>
    <p>本报告角色设定纯属虚构 与现实无关</p>
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
