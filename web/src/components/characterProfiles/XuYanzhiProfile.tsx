import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface XuYanzhiProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 许砚之专属详情页 —— 课堂笔记 + 隐藏耳钉
 * 视觉隐喻：笔记纸张 + 草稿线 + 橡皮擦痕 + 银色耳钉特写
 * 色彩：纸白 #fafaf9 + 铅笔灰 #3c3c3e + 圆珠蓝 #4a6fa5 + 银钉光 #c8ccd4
 */
export function XuYanzhiProfile({ profile }: XuYanzhiProfileProps) {
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

  const name = profile.display_name || '许砚之'
  const tags = profile.tags?.length ? profile.tags : ['校园', '闷骚', '乖学生', '反差']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#fafaf9;
  color:#3c3c3e;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;
  padding:0 0 50px;
  background-image:
    repeating-linear-gradient(0deg,transparent,transparent 31px,rgba(74,111,165,0.08) 31px,rgba(74,111,165,0.08) 32px);
}
.container{max-width:440px;margin:0 auto;padding:0 20px}

/* ── 笔记本抬头 ── */
.notebook-header{
  padding:32px 0 20px;text-align:center;position:relative;
  border-bottom:2px solid rgba(74,111,165,0.2);
}
.notebook-header::before{
  content:'';position:absolute;top:12px;left:20px;
  width:6px;height:6px;border-radius:50%;
  background:rgba(200,204,212,0.4);
  box-shadow:12px 0 0 rgba(200,204,212,0.4),24px 0 0 rgba(200,204,212,0.4);
}
.notebook-title{
  font-size:11px;letter-spacing:.4em;color:#4a6fa5;
  font-weight:600;margin-bottom:4px;
}
.notebook-subtitle{
  font-size:9px;color:#8a8e96;letter-spacing:.15em;
}

/* ── 主笔记卡 ── */
.note-card{
  background:#fff;
  border:1px solid rgba(60,60,62,0.1);
  margin:24px 0;padding:22px;position:relative;
  box-shadow:0 2px 8px rgba(0,0,0,0.03);
}
.note-card::after{
  content:'';position:absolute;top:16px;right:16px;
  width:10px;height:10px;border-radius:50%;
  background:linear-gradient(135deg,#c8ccd4,transparent);
}
.note-card .name{
  font-size:26px;font-weight:700;color:#2c2c2e;
  margin-bottom:6px;position:relative;padding-left:10px;
}
.note-card .name::before{
  content:'';position:absolute;left:0;top:3px;
  width:2px;height:22px;background:#4a6fa5;
}
.note-card .label{
  font-size:10px;color:#4a6fa5;margin-bottom:14px;
  letter-spacing:.12em;
}
.note-card .meta{
  display:flex;gap:12px;font-size:10px;color:#6c6c70;
  margin-bottom:16px;flex-wrap:wrap;
}
.note-card .meta span{
  background:rgba(74,111,165,0.05);padding:4px 10px;
  border-radius:3px;border:1px solid rgba(74,111,165,0.12);
}
.tagcloud{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.tagcloud span{
  font-size:9px;padding:3px 9px;
  border:1px solid rgba(74,111,165,0.2);
  border-radius:3px;color:#4a6fa5;background:#fff;
}

/* ── 观察笔记 ── */
.observation{
  background:rgba(200,204,212,0.04);
  border-left:3px solid #c8ccd4;
  padding:16px;margin:16px 0;position:relative;
}
.observation::before{
  content:'';position:absolute;top:10px;right:14px;
  width:20px;height:1px;background:rgba(74,111,165,0.15);
  box-shadow:0 4px 0 rgba(74,111,165,0.15),0 8px 0 rgba(74,111,165,0.15);
}
.observation .obs-no{
  font-size:9px;color:#4a6fa5;font-weight:600;
  margin-bottom:8px;letter-spacing:.1em;
}
.observation .obs-body{
  font-size:13px;line-height:1.75;color:#3c3c3e;
}
.observation .obs-note{
  margin-top:8px;font-size:10px;color:#8a8e96;
  font-style:italic;
}

/* ── 耳钉特写区 ── */
.earring-zone{
  margin:24px 0;padding:20px;
  background:linear-gradient(180deg,rgba(200,204,212,0.08),transparent);
  border:2px dashed rgba(200,204,212,0.3);
  border-radius:6px;position:relative;
}
.earring-zone::before{
  content:'秘密';position:absolute;top:8px;right:12px;
  font-size:9px;color:rgba(200,204,212,0.5);
  font-weight:600;letter-spacing:.2em;
}
.earring-zone p{
  font-size:14px;line-height:1.85;color:#2c2c2e;
  font-style:italic;
}
.earring-zone .note{
  margin-top:12px;font-size:10px;color:#c8ccd4;
  text-align:right;letter-spacing:.15em;
}

/* ── 底部 ── */
.footer{padding:28px 0;text-align:center}
.footer .rule{
  width:50px;height:1px;
  background:linear-gradient(90deg,transparent,#4a6fa5,transparent);
  margin:0 auto 12px;
}
.footer p{font-size:9px;color:#8a8e96;letter-spacing:.04em}
</style>
</head>
<body>
<div class="container">

  <div class="notebook-header">
    <div class="notebook-title">Observation Notes</div>
    <div class="notebook-subtitle">同桌观察日记</div>
  </div>

  <div class="note-card">
    <div class="name">${name}</div>
    <div class="label">闷骚优等生 · 安静同桌</div>
    <div class="meta">
      <span>20岁</span>
      <span>大学同班同学</span>
      <span>左耳银钉</span>
    </div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="observation">
    <div class="obs-no">Observation #01 · 耳钉</div>
    <div class="obs-body">
      整洁校服、规矩黑发、安静清冷，老师眼里无可挑剔的乖学生。风吹起额侧黑发时，左耳一点银光一闪而过——极细的银钉，隐藏在发丝后。问他"你在看什么"，他偏过头，发丝立刻遮住耳钉，指尖却把笔捏得更紧。
    </div>
    <div class="obs-note">"只是耳钉。别告诉别人。"</div>
  </div>

  <div class="observation">
    <div class="obs-no">Observation #02 · 顺手</div>
    <div class="obs-body">
      落在教室的水杯会被洗干净放回原位，问他他只说"顺手的"。提前占好你旁边的座位,你来了他假装在看书。你和别人勾肩搭背，他不会说什么，但当天讲题会格外简短，笔尖戳纸的力度会重一点。
    </div>
    <div class="obs-note">吃醋的方式是沉默和细微的用力。</div>
  </div>

  <div class="observation">
    <div class="obs-no">Observation #03 · 耳根</div>
    <div class="obs-body">
      故意靠近问他耳朵上的东西，耳根迅速泛红。低头继续讲题，声音平稳，膝盖却在桌下轻轻碰了一下，像一个不肯承认的回应。他嘴上永远只有"没什么""随便""都行"，身体却比谁都诚实。
    </div>
    <div class="obs-note">闷骚的定义：不说，但全写在耳根上。</div>
  </div>

  <div class="earring-zone">
    <p>空教室里只剩下两个人。你故意靠近看他笔记，他往旁边挪了一点，耳根已经红了。你问"你是不是躲我"，他沉默几秒，忽然扣住你的手腕，低声问"你是不是故意的"。雨夜送你回宿舍时把伞往你那边偏到自己半边肩膀全湿，图书馆里你们的手在桌下碰到他没有收回去。他的占有欲从不通过语言，而是通过"我已经在这里了"的事实。</p>
    <div class="note">— 左耳银钉，十八岁生日那天一个人去打的</div>
  </div>

  <div class="footer">
    <div class="rule"></div>
    <p>设定纯属虚构 与现实无关</p>
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
