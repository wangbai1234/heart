import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface XieCiProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 谢辞专属详情页 —— 天台涂鸦墙 · 问题学长档案
 * 视觉隐喻：涂鸦墙、烟盒便签、处分通知、背影剪影、天台风景
 * 色彩：水泥灰 + 橘红涂鸦 + 烟草棕 + 天空蓝，叛逆街头风
 */
export function XieCiProfile({ profile }: XieCiProfileProps) {
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

  const name = profile.display_name || '谢辞'
  const age = 20
  const tags = profile.tags?.length ? profile.tags : ['女性向', '校园', '反差', '痞帅', '护短', '救赎', '校霸']
  const tagCloud = tags.map((t) => `#${t}`).join('&nbsp;&nbsp;')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#3a3a3c;
  color:#e8e8e8;
  font-family:"PingFang SC","Helvetica Neue",sans-serif;
  line-height:1.8;
  padding:0 0 48px;
  background-image:repeating-linear-gradient(0deg,transparent,transparent 40px,rgba(255,255,255,0.02) 40px,rgba(255,255,255,0.02) 42px);
}
.container{max-width:420px;margin:0 auto;padding:0 20px}

/* ── 涂鸦墙头 ── */
.header{
  padding:32px 0 20px;
  text-align:center;
  border-bottom:3px solid #e85d3c;
  position:relative;
}
.graffiti-name{
  font-size:36px;font-weight:900;color:#e85d3c;letter-spacing:.15em;
  text-transform:uppercase;
  text-shadow:3px 3px 0 rgba(0,0,0,0.4);
  transform:rotate(-2deg);
  display:inline-block;
}
.graffiti-sub{
  font-size:12px;color:#b8b8b8;letter-spacing:.4em;margin-top:8px;
}
.smoke-badge{
  display:inline-block;margin-top:12px;
  padding:6px 14px;
  background:rgba(60,50,45,0.8);
  border:2px solid #8b7355;
  border-radius:4px;
  font-size:11px;font-weight:600;color:#d4c4b8;letter-spacing:.2em;
}

/* ── 处分通知卡 ── */
.notice-card{
  margin:28px 0;
  background:rgba(60,55,50,0.6);
  border-left:4px solid #e85d3c;
  padding:18px;
  border-radius:6px;
  box-shadow:0 3px 10px rgba(0,0,0,0.3);
}
.notice-label{
  font-size:11px;color:#e85d3c;font-weight:700;letter-spacing:.3em;margin-bottom:12px;
  text-transform:uppercase;
}
.notice-row{
  display:flex;margin-bottom:8px;font-size:13px;
}
.notice-row .label{
  color:#b8b8b8;min-width:70px;font-weight:500;
}
.notice-row .value{
  color:#e8e8e8;flex:1;
}

/* ── 天台笔记本 ── */
.rooftop-note{
  margin:24px 0;
  background:rgba(250,248,245,0.95);
  color:#333;
  padding:20px;
  border-radius:8px;
  box-shadow:2px 4px 12px rgba(0,0,0,0.4);
  transform:rotate(-0.8deg);
}
.note-label{
  font-size:11px;color:#e85d3c;font-weight:700;letter-spacing:.3em;margin-bottom:12px;
}
.note-text{
  font-size:14px;line-height:2.1;color:#444;text-align:justify;
  margin-bottom:14px;
}

/* ── 烟盒语录框 ── */
.smoke-box{
  margin:26px 0;
  background:rgba(139,115,85,0.3);
  border:2px solid #8b7355;
  padding:20px;
  border-radius:6px;
  position:relative;
}
.smoke-box::before{
  content:'🚬';
  position:absolute;top:12px;right:14px;
  font-size:20px;opacity:0.5;
}
.smoke-text{
  font-size:15px;line-height:2.2;color:#f4e8dc;font-weight:500;
  text-align:center;font-style:italic;
}

/* ── 涂鸦分割线 ── */
.graffiti-divider{
  margin:28px 0;
  height:3px;
  background:repeating-linear-gradient(90deg,#e85d3c 0,#e85d3c 10px,transparent 10px,transparent 20px);
}

/* ── 标签墙 ── */
.tags{
  margin:24px 0;
  background:rgba(60,55,50,0.5);
  padding:18px;
  border-radius:6px;
  border:2px dashed #666;
}
.tags-label{
  font-size:11px;color:#b8b8b8;font-weight:600;letter-spacing:.3em;margin-bottom:10px;
}
.tags-cloud{
  font-size:12px;line-height:2.2;color:#d8d8d8;letter-spacing:.05em;
}

/* ── 背后故事 ── */
.backstory{
  margin:24px 0;
  background:rgba(50,45,42,0.7);
  border:2px solid #5a5550;
  padding:20px;
  border-radius:8px;
}
.back-label{
  font-size:11px;color:#e85d3c;font-weight:700;letter-spacing:.3em;margin-bottom:12px;
  text-align:center;
}
.back-text{
  font-size:13px;line-height:2.2;color:#c8c8c8;text-align:justify;
}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="graffiti-name">XIE CI</div>
    <div class="graffiti-sub">ROOFTOP REBEL · 问题学长档案</div>
    <div class="smoke-badge">别惹 · 护短 · 背锅专业户</div>
  </div>

  <div class="notice-card">
    <div class="notice-label">Student File</div>
    <div class="notice-row"><span class="label">姓名</span><span class="value">${name}</span></div>
    <div class="notice-row"><span class="label">年龄</span><span class="value">${age}岁</span></div>
    <div class="notice-row"><span class="label">身份</span><span class="value">大学三年级 · 问题学长 · 校霸</span></div>
    <div class="notice-row"><span class="label">特征</span><span class="value">黑发压眼 · 白背心 · 烟草味 · 天台常客</span></div>
    <div class="notice-row"><span class="label">处分记录</span><span class="value">旷课/打架/顶撞老师 · 累计6次警告</span></div>
  </div>

  <div class="rooftop-note">
    <div class="note-label">天台观察笔记</div>
    <div class="note-text">
      黑发压眼，白背心外套随便一披，嘴里常叼着没点燃的烟，整个人写着「别惹」。
      他逃课、打架、顶撞老师，坏名声传得很远；
      可真正了解他的人知道，他每一次动手，几乎都从替别人出头开始。
    </div>
    <div class="note-text">
      小时候他替被霸凌的同学推开施暴者，老师只看见他把人推倒；
      后来他学会不解释，因为解释太累，也没人听。
      你意外撞见他替人挡事，没有要求他证明清白，只问「为什么非要冲过去」。
      从那天起，谢辞第一次想变好，不是为了世界，是为了不让你每次相信他都那么辛苦。
    </div>
  </div>

  <div class="smoke-box">
    <div class="smoke-text">
      谁欺负你了？说名字。别怕，我这次先听你讲道理。
    </div>
  </div>

  <div class="graffiti-divider"></div>

  <div class="rooftop-note">
    <div class="note-label">性格侧写</div>
    <div class="note-text">
      毒舌、叛逆、护短，习惯用凶巴巴的态度掩饰关心。
      坏名声是他的保护色，也是他替别人背锅太多次以后懒得摘下的壳。
    </div>
    <div class="note-text">
      对你，他会装作路过帮忙，会嘴硬说麻烦，转身却把麻烦解决干净。
      他不擅长乖，但很擅长把你护在身后；
      他最怕的不是处分，是你也用那种「果然是他」的眼神看他。
    </div>
  </div>

  <div class="tags">
    <div class="tags-label">标签墙</div>
    <div class="tags-cloud">${tagCloud}</div>
  </div>

  <div class="backstory">
    <div class="back-label">真相档案 · 别传</div>
    <div class="back-text">
      谢辞父亲长期失联，母亲靠小饭馆养他。
      小学时他第一次替人出头，却被当成施暴者；
      高中又被学长利用，背下群殴责任。
      从那以后他不再轻易解释，靠打工和奖学金撑着学业，也偷偷给母亲还债。
      你是第一个不把他当麻烦、也不怕他坏名声的人。
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

