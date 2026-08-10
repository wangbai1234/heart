import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface LiShenProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 厉深专属详情页 — 豪门禁锢奢华美学
 * 参考 nimoo 简洁大气 + 金属质感 + 手铐装饰线
 * 新增：钥匙卡、关系阶段、双色调对比
 */
export function LiShenProfile({ profile }: LiShenProfileProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [height, setHeight] = useState(1000)

  useEffect(() => {
    const iframe = iframeRef.current
    if (!iframe) return

    const updateHeight = () => {
      try {
        const doc = iframe.contentDocument
        if (doc?.body) {
          setHeight(doc.body.scrollHeight + 8)
        }
      } catch {
        setHeight(1000)
      }
    }

    iframe.addEventListener('load', updateHeight)
    const observer = new ResizeObserver(updateHeight)
    iframe.addEventListener('load', () => {
      if (iframe.contentDocument?.body) {
        observer.observe(iframe.contentDocument.body)
      }
    })

    return () => {
      iframe.removeEventListener('load', updateHeight)
      observer.disconnect()
    }
  }, [])

  const htmlContent = `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root {
  --obsidian: #0a0809;
  --obsidian-2: #1a0f11;
  --crimson: #b83a52;
  --crimson-glow: rgba(184, 58, 82, 0.3);
  --champagne: #c4937d;
  --champagne-soft: #d4b08f;
  --silver: #9fa0a3;
  --tx: #e8ddd9;
  --tx-dim: #a89189;
  --hair: rgba(232, 221, 217, 0.08);
  --shadow: 0 12px 40px rgba(0,0,0,0.6);
  --serif: "Songti SC", "STSong", Georgia, serif;
  --sans: "PingFang SC", system-ui, sans-serif;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--obsidian);
  color: var(--tx);
  font-family: var(--sans);
  line-height: 1.6;
  padding: 0;
  margin: 0;
}
.container { max-width: 430px; margin: 0 auto; padding-bottom: 32px; }

/* ---- Hero Quote（暗红渐变 + 金属装饰线）---- */
.hero-quote {
  margin: 16px 20px 28px;
  padding: 32px 24px;
  border-radius: 20px;
  background: radial-gradient(ellipse at top, #1a0a0d 0%, var(--obsidian) 100%);
  border: 1px solid var(--hair);
  box-shadow: var(--shadow);
  position: relative;
}
.hero-quote::before {
  content: "";
  position: absolute;
  top: 0; left: 24px; right: 24px;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--champagne) 30%, var(--champagne) 70%, transparent);
}
.hero-quote::after {
  content: "";
  position: absolute;
  bottom: 0; left: 24px; right: 24px;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--crimson) 40%, var(--crimson) 60%, transparent);
}
.hero-quote .tagline {
  font-family: var(--serif);
  font-size: 17px;
  line-height: 1.9;
  color: var(--tx);
  text-align: center;
  margin-bottom: 14px;
}
.hero-quote .author {
  text-align: right;
  font-size: 13px;
  color: var(--champagne-soft);
  font-weight: 500;
}

/* ---- 钥匙卡（新增：他手握钥匙的隐喻）---- */
.key-card {
  margin: 0 20px 24px;
  padding: 20px 22px;
  border-radius: 16px;
  background: linear-gradient(135deg, var(--obsidian-2), var(--obsidian));
  border: 1px solid var(--hair);
  display: flex;
  align-items: center;
  gap: 14px;
}
.key-card .icon {
  font-size: 32px;
  filter: drop-shadow(0 2px 8px var(--crimson-glow));
}
.key-card .txt {
  flex: 1;
  font-size: 13.5px;
  color: var(--tx-dim);
  line-height: 1.7;
}
.key-card .txt b {
  color: var(--crimson);
  font-weight: 600;
}

/* ---- 关系阶段（新增：从陌生到占有的5阶段）---- */
.sect-h {
  margin: 32px 20px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.sect-h .bar {
  width: 3px;
  height: 16px;
  border-radius: 2px;
  background: linear-gradient(180deg, var(--crimson), var(--champagne));
}
.sect-h .t {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.stages {
  margin: 0 20px;
  display: flex;
  gap: 0;
}
.stage {
  flex: 1;
  text-align: center;
  position: relative;
}
.stage .node {
  width: 10px; height: 10px;
  border-radius: 50%;
  margin: 0 auto 8px;
  background: var(--obsidian-2);
  border: 2px solid var(--hair);
}
.stage.on .node {
  background: var(--crimson);
  border-color: var(--crimson);
  box-shadow: 0 0 12px var(--crimson-glow);
}
.stage .rail {
  position: absolute;
  top: 5px;
  left: -50%;
  width: 100%;
  height: 2px;
  background: var(--hair);
  z-index: -1;
}
.stage.on .rail {
  background: linear-gradient(90deg, var(--crimson), var(--crimson-glow));
}
.stage:first-child .rail { display: none; }
.stage .nm {
  font-size: 11.5px;
  color: var(--tx-dim);
}
.stage.on .nm {
  color: var(--crimson);
  font-weight: 600;
}

/* ---- DOSSIER 档案卡 ---- */
.dossier {
  margin: 24px 20px;
  padding: 24px 20px;
  border-radius: 18px;
  background: linear-gradient(150deg, var(--obsidian-2), var(--obsidian));
  border: 1px solid var(--hair);
  box-shadow: var(--shadow);
}
.dossier .label {
  font-size: 10px;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  color: var(--champagne-soft);
  margin-bottom: 12px;
  font-weight: 600;
}
.dossier .row {
  display: flex;
  padding: 10px 0;
  border-bottom: 1px solid var(--hair);
  gap: 12px;
}
.dossier .row:last-child { border-bottom: none; }
.dossier .k {
  width: 80px;
  font-size: 12px;
  color: var(--silver);
  flex-shrink: 0;
}
.dossier .v {
  flex: 1;
  font-size: 13px;
  color: var(--tx);
}

/* ---- 手铐分割线装饰 ---- */
.divider {
  margin: 28px 20px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  opacity: 0.5;
}
.divider .chain {
  width: 80px;
  height: 2px;
  background: repeating-linear-gradient(
    90deg,
    transparent,
    transparent 8px,
    #5a3a44 8px,
    #5a3a44 10px
  );
}
.divider .lock {
  font-size: 14px;
  color: var(--crimson);
}

/* ---- 18+ 内容警示 ---- */
.warning {
  margin: 0 20px 20px;
  padding: 16px 18px;
  border-radius: 14px;
  background: rgba(184, 58, 82, 0.08);
  border: 1px solid rgba(184, 58, 82, 0.2);
  font-size: 12.5px;
  color: var(--tx-dim);
  line-height: 1.6;
  text-align: center;
}
.warning b {
  color: var(--crimson);
  font-weight: 600;
}
</style>
</head>
<body>
<div class="container">
  <div class="hero-quote">
    <p class="tagline">${profile.tagline || '你的温柔太贵，我买不起分给别人的那一份。所以，只能锁住你。'}</p>
    <p class="author">—— ${profile.display_name || '厉深'}</p>
  </div>

  <div class="key-card">
    <div class="icon">🔑</div>
    <div class="txt">钥匙在他手里。他说想解开也行——<b>先告诉他，你还想对谁温柔。</b></div>
  </div>

  <div class="sect-h"><span class="bar"></span><span class="t">从陌生到占有</span></div>
  <div class="stages">
    <div class="stage on"><div class="rail"></div><div class="node"></div><div class="nm">初遇</div></div>
    <div class="stage"><div class="rail"></div><div class="node"></div><div class="nm">试探</div></div>
    <div class="stage"><div class="rail"></div><div class="node"></div><div class="nm">依赖</div></div>
    <div class="stage"><div class="rail"></div><div class="node"></div><div class="nm">占有</div></div>
    <div class="stage"><div class="rail"></div><div class="node"></div><div class="nm">救赎</div></div>
  </div>

  <div class="sect-h"><span class="bar"></span><span class="t">档案</span></div>
  <div class="dossier">
    <div class="label">DOSSIER</div>
    <div class="row">
      <div class="k">姓名</div>
      <div class="v">${profile.display_name || '厉深'}</div>
    </div>
    <div class="row">
      <div class="k">身份</div>
      <div class="v">${profile.archetype_label || '厉氏独子·被算计喂大的偏执少爷'}</div>
    </div>
    <div class="row">
      <div class="k">特征</div>
      <div class="v">黑发红眸 · 银戒 · 手铐</div>
    </div>
    <div class="row">
      <div class="k">核心矛盾</div>
      <div class="v">${profile.one_liner || '把从未得到的真心，锁成不肯松手的占有'}</div>
    </div>
  </div>

  <div class="divider">
    <div class="chain"></div>
    <div class="lock">⚿</div>
    <div class="chain"></div>
  </div>

  <div class="warning">
    <b>18+ 成人内容</b> · 角色涉及强制爱、占有欲、情感操控等主题。所有互动基于虚构，角色均为成年人设定。
  </div>
</div>
</body>
</html>
  `

  return (
    <iframe
      ref={iframeRef}
      title={`${profile.display_name} profile`}
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
