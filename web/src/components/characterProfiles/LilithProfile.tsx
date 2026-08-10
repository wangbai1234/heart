import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface LilithProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 莉莉丝专属详情页 — 魅魔女王暗夜殿堂美学
 * 设计语言：暗色王座 + 烛火金光 + 羽翼装饰 + 支配主题
 * 颜色：黑#0d0a0e + 猩红#b8294b + 金#d4a557 + 深紫#2a1828
 */
export function LilithProfile({ profile }: LilithProfileProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [height, setHeight] = useState(1100)

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
        setHeight(1100)
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
  --abyss: #0d0a0e;
  --abyss-2: #1a0f16;
  --throne: #2a1828;
  --crimson: #b8294b;
  --crimson-glow: rgba(184, 41, 75, 0.4);
  --gold: #d4a557;
  --gold-soft: #e4c482;
  --gold-glow: rgba(212, 165, 87, 0.3);
  --tx: #ede7e3;
  --tx-dim: #b39a90;
  --hair: rgba(237, 231, 227, 0.1);
  --shadow: 0 16px 48px rgba(0,0,0,0.7);
  --serif: "Songti SC", "STSong", Georgia, serif;
  --sans: "PingFang SC", system-ui, sans-serif;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--abyss);
  color: var(--tx);
  font-family: var(--sans);
  line-height: 1.6;
  padding: 0;
  margin: 0;
}
.container { max-width: 430px; margin: 0 auto; padding-bottom: 32px; }

/* ---- Throne Hero（王座烛火氛围）---- */
.throne-hero {
  margin: 20px 20px 28px;
  padding: 40px 24px 32px;
  border-radius: 22px;
  background: radial-gradient(circle at 50% 20%, var(--throne), var(--abyss) 80%);
  border: 1px solid var(--hair);
  box-shadow: var(--shadow);
  position: relative;
  overflow: hidden;
}
.throne-hero::before {
  content: "";
  position: absolute;
  top: -50%; left: 50%;
  width: 200px; height: 200px;
  transform: translateX(-50%);
  background: radial-gradient(circle, var(--gold-glow), transparent 70%);
  opacity: 0.4;
}
.throne-hero .crown {
  text-align: center;
  font-size: 48px;
  margin-bottom: 16px;
  filter: drop-shadow(0 4px 16px var(--crimson-glow));
}
.throne-hero .title {
  font-family: var(--serif);
  font-size: 22px;
  text-align: center;
  color: var(--gold-soft);
  letter-spacing: 0.08em;
  margin-bottom: 18px;
}
.throne-hero .tagline {
  font-size: 15px;
  color: var(--tx-dim);
  text-align: center;
  line-height: 1.8;
}

/* ---- 支配宣言卡 ---- */
.decree {
  margin: 0 20px 24px;
  padding: 24px 22px;
  border-radius: 18px;
  background: linear-gradient(140deg, var(--abyss-2), var(--abyss));
  border: 1px solid rgba(184, 41, 75, 0.3);
  box-shadow: 0 8px 24px rgba(184, 41, 75, 0.15);
}
.decree .label {
  font-size: 10px;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  color: var(--gold);
  margin-bottom: 14px;
  font-weight: 600;
}
.decree .text {
  font-family: var(--serif);
  font-size: 15px;
  line-height: 2;
  color: var(--tx);
}
.decree .text em {
  color: var(--crimson);
  font-style: normal;
  font-weight: 600;
}

/* ---- 羽翼分割线 ---- */
.wing-divider {
  margin: 28px 20px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  opacity: 0.6;
}
.wing-divider .wing {
  font-size: 24px;
}
.wing-divider .gem {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: radial-gradient(circle, var(--gold), var(--crimson));
  box-shadow: 0 0 12px var(--gold-glow);
}

/* ---- 女王档案 ---- */
.sect-h {
  margin: 32px 20px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.sect-h .flame {
  font-size: 18px;
  filter: drop-shadow(0 2px 8px var(--crimson-glow));
}
.sect-h .t {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--gold-soft);
}
.dossier {
  margin: 0 20px 24px;
  padding: 24px 20px;
  border-radius: 18px;
  background: linear-gradient(150deg, var(--throne), var(--abyss));
  border: 1px solid var(--hair);
  box-shadow: var(--shadow);
}
.dossier .row {
  display: flex;
  padding: 11px 0;
  border-bottom: 1px solid var(--hair);
  gap: 12px;
}
.dossier .row:last-child { border-bottom: none; }
.dossier .k {
  width: 90px;
  font-size: 12px;
  color: var(--tx-dim);
  flex-shrink: 0;
}
.dossier .v {
  flex: 1;
  font-size: 13.5px;
  color: var(--tx);
}

/* ---- 博弈双轨（支配 vs 反支配）---- */
.duel {
  margin: 24px 20px;
  padding: 22px 20px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(184, 41, 75, 0.08), rgba(212, 165, 87, 0.08));
  border: 1px solid var(--hair);
}
.duel .title {
  font-family: var(--serif);
  font-size: 14px;
  color: var(--gold-soft);
  margin-bottom: 14px;
  text-align: center;
}
.duel .paths {
  display: flex;
  gap: 12px;
}
.duel .path {
  flex: 1;
  padding: 14px 12px;
  border-radius: 12px;
  background: var(--abyss-2);
  border: 1px solid var(--hair);
  text-align: center;
}
.duel .path .icon {
  font-size: 28px;
  margin-bottom: 8px;
}
.duel .path .label {
  font-size: 12px;
  color: var(--tx-dim);
  line-height: 1.6;
}
.duel .path.dom .icon { filter: drop-shadow(0 2px 8px var(--crimson-glow)); }
.duel .path.sub .icon { filter: drop-shadow(0 2px 8px var(--gold-glow)); }

/* ---- 18+ 警示 ---- */
.warning {
  margin: 0 20px 20px;
  padding: 16px 18px;
  border-radius: 14px;
  background: rgba(184, 41, 75, 0.08);
  border: 1px solid rgba(184, 41, 75, 0.2);
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
  <div class="throne-hero">
    <div class="crown">👑</div>
    <div class="title">${profile.display_name || '莉莉丝'} · ${profile.archetype_label || '魅魔女王'}</div>
    <div class="tagline">${profile.tagline || '乖乖听话的，本座见得多了。敢不听的你，才让我上心。'}</div>
  </div>

  <div class="decree">
    <div class="label">Decree</div>
    <div class="text">跪下，让本座好好看看你。<br>这世上的魂灵本座玩腻了——<em>可你偏偏敢直视我。有意思。</em></div>
  </div>

  <div class="wing-divider">
    <div class="wing">🦇</div>
    <div class="gem"></div>
    <div class="wing">🦇</div>
  </div>

  <div class="sect-h"><span class="flame">🕯️</span><span class="t">女王档案</span></div>
  <div class="dossier">
    <div class="row">
      <div class="k">真名</div>
      <div class="v">${profile.display_name || '莉莉丝'}</div>
    </div>
    <div class="row">
      <div class="k">种族</div>
      <div class="v">魅魔 · 支配者血脉</div>
    </div>
    <div class="row">
      <div class="k">特征</div>
      <div class="v">黑发金瞳 · 猩红弯角 · 黑红羽翼</div>
    </div>
    <div class="row">
      <div class="k">食粮</div>
      <div class="v">魂灵的臣服 · 意志的崩解</div>
    </div>
    <div class="row">
      <div class="k">弱点</div>
      <div class="v">${profile.one_liner || '驯服过万千魂灵，却栽在唯一不肯低头的你手里'}</div>
    </div>
  </div>

  <div class="sect-h"><span class="flame">⚔️</span><span class="t">这场博弈的两条路</span></div>
  <div class="duel">
    <div class="title">是你驯服她，还是她收服你</div>
    <div class="paths">
      <div class="path dom">
        <div class="icon">⛓️</div>
        <div class="label">臣服路线<br>成为她的所有物</div>
      </div>
      <div class="path sub">
        <div class="icon">🗝️</div>
        <div class="label">反将路线<br>让女王先动心</div>
      </div>
    </div>
  </div>

  <div class="warning">
    <b>18+ 男性向内容</b> · 角色涉及支配/臣服、女王系、调教等主题。所有互动基于虚构，角色均为成年人设定。
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
