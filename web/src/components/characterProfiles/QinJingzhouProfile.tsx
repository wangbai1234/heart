import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface QinJingzhouProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 秦景舟专属详情页 —— 婚纱工作室档案
 * 视觉隐喻：设计稿草图 + 试衣间镜子 + 尺寸标注 + 面料样本
 * 色彩：工作室白 #f8f6f4 + 石墨灰 #2c2c2e + 钢笔蓝 #4a6fa5 + 线稿金 #c9a24b
 */
export function QinJingzhouProfile({ profile }: QinJingzhouProfileProps) {
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

  const name = profile.display_name || '秦景舟'
  const tags = profile.tags?.length ? profile.tags : ['婚服设计师', '前任', '破镜重圆']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#f8f6f4;
  color:#2c2c2e;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;
  padding:0 0 50px;
  background-image:
    repeating-linear-gradient(90deg,transparent,transparent 19px,rgba(74,111,165,0.03) 19px,rgba(74,111,165,0.03) 20px),
    repeating-linear-gradient(0deg,transparent,transparent 19px,rgba(74,111,165,0.03) 19px,rgba(74,111,165,0.03) 20px);
}
.container{max-width:440px;margin:0 auto;padding:0 20px}

/* ── 工作室抬头 ── */
.studio-header{
  padding:32px 0 24px;text-align:center;position:relative;
  border-bottom:2px solid #4a6fa5;
}
.studio-header::before{
  content:'';position:absolute;top:8px;right:16px;
  width:60px;height:60px;
  border:1px dashed rgba(74,111,165,0.25);
  border-radius:50%;
}
.studio-name{
  font-family:"Songti SC",serif;font-size:13px;letter-spacing:.5em;
  color:#4a6fa5;font-weight:400;margin-bottom:4px;
}
.studio-title{
  font-size:10px;color:#8a8e96;letter-spacing:.3em;text-transform:uppercase;
}

/* ── 主档案卡：设计稿风格 ── */
.design-sheet{
  background:#fff;
  border:1px solid rgba(44,44,46,0.12);
  margin:24px 0;padding:24px;position:relative;
  box-shadow:0 2px 12px rgba(0,0,0,0.04);
}
.design-sheet::after{
  content:'';position:absolute;top:12px;right:12px;
  width:8px;height:8px;border-radius:50%;
  background:linear-gradient(135deg,#c9a24b,transparent);
}
.design-sheet .name{
  font-size:28px;font-weight:700;color:#2c2c2e;
  margin-bottom:6px;position:relative;padding-left:12px;
}
.design-sheet .name::before{
  content:'';position:absolute;left:0;top:4px;
  width:3px;height:24px;background:#4a6fa5;
}
.design-sheet .label{
  font-size:11px;color:#4a6fa5;margin-bottom:14px;
  letter-spacing:.08em;
}
.design-sheet .meta{
  display:flex;gap:14px;font-size:10px;color:#6c6c70;
  margin-bottom:16px;flex-wrap:wrap;
}
.design-sheet .meta span{background:rgba(74,111,165,0.06);padding:4px 10px;border-radius:3px}
.tagcloud{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.tagcloud span{
  font-size:9px;padding:3px 9px;border:1px solid rgba(74,111,165,0.2);
  border-radius:3px;color:#4a6fa5;background:#fff;
}

/* ── 尺寸标注块 ── */
.measurement{
  background:rgba(201,162,75,0.04);
  border-left:3px solid #c9a24b;
  padding:16px;margin:16px 0;border-radius:4px;
}
.measurement .dim-label{
  font-size:9px;color:#c9a24b;font-weight:600;
  letter-spacing:.2em;text-transform:uppercase;margin-bottom:10px;
}
.measurement .dim-text{
  font-size:13px;line-height:1.8;color:#3c3c3e;
}

/* ── 试衣间记录 ── */
.fitting-note{
  background:#fff;border:1px dashed rgba(74,111,165,0.3);
  padding:18px;margin:16px 0;position:relative;
}
.fitting-note::before{
  content:'✂';position:absolute;top:8px;right:12px;
  font-size:16px;color:rgba(201,162,75,0.3);
}
.fitting-note .note-no{
  font-size:9px;color:#4a6fa5;font-weight:600;
  margin-bottom:8px;letter-spacing:.1em;
}
.fitting-note .note-body{
  font-size:13px;line-height:1.75;color:#3c3c3e;
}

/* ── 面料样本（私语区） ── */
.fabric-sample{
  margin:20px 0;padding:20px;
  background:linear-gradient(135deg,rgba(74,111,165,0.05),transparent);
  border-top:2px solid #4a6fa5;border-bottom:2px solid #4a6fa5;
}
.fabric-sample p{
  font-family:"Songti SC",serif;font-size:14px;line-height:1.85;
  color:#2c2c2e;font-style:italic;
}
.fabric-sample .annotation{
  margin-top:12px;font-size:10px;color:#c9a24b;
  text-align:right;letter-spacing:.15em;font-style:normal;
}

/* ── 底部签名 ── */
.footer{padding:28px 0;text-align:center}
.footer .rule{
  width:60px;height:1px;background:linear-gradient(90deg,transparent,#4a6fa5,transparent);
  margin:0 auto 12px;
}
.footer p{font-size:9px;color:#8a8e96;letter-spacing:.04em}
</style>
</head>
<body>
<div class="container">

  <div class="studio-header">
    <div class="studio-name">秦氏定制工作室</div>
    <div class="studio-title">Bespoke Atelier · Client File</div>
  </div>

  <div class="design-sheet">
    <div class="name">${name}</div>
    <div class="label">婚服设计师 · 冷静前任</div>
    <div class="meta">
      <span>30岁</span>
      <span>秦氏集团继承人</span>
      <span>五年前因贫分手</span>
    </div>
    <div class="tagcloud">${tagCloud}</div>
  </div>

  <div class="measurement">
    <div class="dim-label">Measurement · 关键尺寸</div>
    <div class="dim-text">
      他穿着尚未完成的黑色礼服站在镜前，领口别着你亲手挑的银色领针。袖口为什么改了三次？因为新郎肩线不标准——也因为你每次量尺寸，他都会握住你的手腕。
    </div>
  </div>

  <div class="fitting-note">
    <div class="note-no">试衣记录 #01</div>
    <div class="note-body">
      试衣时你蹲下量裤长，他的手会无意识地放在你肩上，像五年前每次你加班他来接你那样——但你站起来的瞬间他会立刻收回，假装在看镜子里的衣服。
    </div>
  </div>

  <div class="fitting-note">
    <div class="note-no">试衣记录 #02</div>
    <div class="note-body">
      你说"祝您新婚快乐"，他会握住你的手腕把你拉进试衣间，抵着你的额头问"你真的说得出口？"你躲他的电话，他会直接来工作室堵你，把车钥匙从你手里拿走。
    </div>
  </div>

  <div class="fitting-note">
    <div class="note-no">试衣记录 #03</div>
    <div class="note-body">
      你哭着说"五年了你还要我怎么样"，他会吻你，吻到你推不开为止，然后低声说"我要你告诉我，你还爱不爱我"。他的爱不是"我变有钱所以你必须回来"，而是终于有能力把选择权交给你。
    </div>
  </div>

  <div class="fabric-sample">
    <p>婚礼前一周，工作室只开着一盏灯。他俯身吻住你，像是要把五年的沉默一起讨回来。你推开他，他却抵着你的额头，呼吸凌乱："婚礼还没开始。你现在反悔，还来得及。"</p>
    <div class="annotation">— 面料备注 · 黑色礼服内袋绣字"林悦 2021.03.14"</div>
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
