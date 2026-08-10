import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface JiYuProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 季屿专属详情页 iframe 内容——bespoke rich HTML。
 * 接收动态数据后渲染成自包含 HTML 文档。
 */
export function JiYuProfile({ profile }: JiYuProfileProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [height, setHeight] = useState(1200) // 初始估算高度

  // 监听 iframe 内高度变化，自动调整外框高度
  useEffect(() => {
    const iframe = iframeRef.current
    if (!iframe) return

    const updateHeight = () => {
      try {
        const doc = iframe.contentDocument
        if (doc?.body) {
          const h = doc.body.scrollHeight
          setHeight(h + 8) // 轻微余量，避免测量取整导致内层再出滚动条
        }
      } catch {
        // sandbox 限制时退回默认高度
        setHeight(1200)
      }
    }

    iframe.addEventListener('load', updateHeight)

    // 监听后续 DOM 变化（如折叠展开）
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

  // 构造注入数据的 HTML 文档（季屿 bespoke 设计，基于 demo）
  const htmlContent = `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<style>
/* ============ 季屿专属设计（来自 character-detail-demo.html）============ */
:root{
  --ink:#171019; --ink-2:#1E1620; --surface:#241926; --surface-2:#2C2030;
  --paper:#E9DFD6; --paper-ink:#2A2230; --paper-line:#C9BBAA;
  --accent:#C24A63; --accent-soft:#E08298; --accent-glow:rgba(194,74,99,.32);
  --gold:#B08A4F; --gold-soft:#D4B983;
  --tx:#ECE2E7; --tx-dim:#B4A4AF; --tx-mute:#8A7C87;
  --hair:rgba(236,226,231,.10); --hair-2:rgba(236,226,231,.06);
  --shadow:0 18px 46px rgba(0,0,0,.5);
  --serif:"Songti SC","STSong","Noto Serif SC",Georgia,serif;
  --sans:"PingFang SC","Helvetica Neue",system-ui,sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--ink);color:var(--tx);font-family:var(--sans);
  -webkit-font-smoothing:antialiased;line-height:1.6;margin:0;padding:0}
.container{max-width:430px;margin:0 auto;background:transparent;padding-bottom:24px}
.sect.first{padding-top:4px}
.eyebrow{font-size:11px;letter-spacing:.22em;text-transform:uppercase;
  color:var(--gold-soft);font-weight:600}
.serif{font-family:var(--serif)}
/* ---- 区块头 ---- */
.sect{padding:28px 22px 0}
.sect-h{display:flex;align-items:center;gap:9px;margin-bottom:14px}
.sect-h .bar{width:3px;height:15px;border-radius:2px;background:linear-gradient(var(--accent),var(--gold))}
.sect-h .t{font-size:15px;font-weight:600;letter-spacing:.04em}
.sect-h .en{font-size:10px;letter-spacing:.2em;color:var(--tx-mute);text-transform:uppercase}
/* ---- 开场预告卡 ---- */
.preview{margin:0 22px;border-radius:20px;overflow:hidden;background:linear-gradient(150deg,var(--surface-2),var(--ink-2));border:1px solid var(--hair);box-shadow:var(--shadow);position:relative}
.preview::before{content:"\\201C";position:absolute;top:-16px;left:14px;font-family:var(--serif);font-size:88px;color:var(--accent-glow);line-height:1}
.preview .inner{padding:22px 20px 18px}
.preview .scene{font-family:var(--serif);font-size:13px;color:var(--tx-mute);font-style:italic;margin-bottom:12px}
.preview .line{font-family:var(--serif);font-size:16.5px;line-height:1.9}
.preview .line em{color:var(--accent-soft);font-style:normal}
.preview .foot{margin-top:16px;padding-top:13px;border-top:1px solid var(--hair-2);display:flex;align-items:center;gap:8px;font-size:12px;color:var(--tx-mute)}
.preview .foot .dot{width:6px;height:6px;border-radius:50%;background:var(--accent);box-shadow:0 0 8px var(--accent-glow)}
/* ---- 关系路线时间轴 ---- */
.route{display:flex;gap:0;margin:0 22px}
.step{flex:1;text-align:center;position:relative}
.step .node{width:11px;height:11px;border-radius:50%;margin:0 auto 8px;background:var(--surface-2);border:2px solid var(--hair)}
.step.on .node{background:var(--accent);border-color:var(--accent);box-shadow:0 0 10px var(--accent-glow)}
.step .rail{position:absolute;top:5px;left:-50%;width:100%;height:2px;background:var(--hair);z-index:-1}
.step.on .rail{background:linear-gradient(90deg,var(--accent),var(--accent-glow))}
.step:first-child .rail{display:none}
.step .nm{font-size:12px;color:var(--tx-dim)}
.step.on .nm{color:var(--accent-soft);font-weight:600}
.route-note{margin:12px 22px 0;font-size:12.5px;color:var(--tx-mute);line-height:1.7;font-family:var(--serif);font-style:italic}
/* ---- 叙引 档案册卡 ---- */
.xy{margin:0 22px;border-radius:20px;overflow:hidden;
  background:linear-gradient(160deg,var(--surface),var(--ink-2));
  border:1px solid var(--hair);box-shadow:var(--shadow)}
.xy .hero{padding:34px 20px 26px;text-align:center;position:relative;
  background:radial-gradient(80% 60% at 50% 0,rgba(194,74,99,.1),transparent)}
.xy .hero .big{font-family:var(--serif);font-size:30px;letter-spacing:.14em;color:var(--tx)}
.xy .hero .big em{color:var(--accent);font-style:normal;font-size:38px}
.xy .hero .en{margin-top:10px;font-size:10px;letter-spacing:.34em;color:var(--tx-mute)}
.xy .hero .no{position:absolute;left:14px;top:14px;font-size:9px;letter-spacing:.2em;
  color:var(--tx-mute);writing-mode:vertical-rl}
.idcard{display:flex;gap:14px;align-items:center;padding:18px 20px;
  border-top:1px solid var(--hair-2);border-bottom:1px solid var(--hair-2)}
.idcard .av{width:66px;height:66px;border-radius:50%;flex:none;
  border:2px solid var(--gold);background:linear-gradient(150deg,#3a2836,#241826)}
.idcard .nm{font-family:var(--serif);font-size:20px;font-weight:600}
.idcard .sub{font-size:12px;color:var(--tx-dim);margin:3px 0 8px}
.idcard .attrs{display:flex;gap:7px;flex-wrap:wrap}
.idcard .attrs span{font-size:11px;color:var(--gold-soft);background:rgba(176,138,79,.12);
  border:1px solid rgba(176,138,79,.24);border-radius:6px;padding:2px 8px}
.bio{padding:18px 20px 22px}
.bio h4{display:flex;align-items:center;gap:8px;font-family:var(--serif);
  font-size:15px;font-weight:600;margin:16px 0 8px}
.bio h4:first-child{margin-top:0}
.bio h4::before{content:"";width:3px;height:14px;border-radius:2px;background:var(--accent)}
.bio p{font-size:13.5px;line-height:1.85;color:var(--tx-dim)}
/* ---- 相遇场景 ---- */
.meet{margin:0 22px;border-radius:16px;padding:18px 18px;background:var(--surface);border:1px solid var(--hair);position:relative}
.meet .scene-line{font-family:var(--serif);font-size:14.5px;line-height:1.85;color:var(--tx-dim)}
.role{margin:12px 22px 0;display:flex;align-items:center;gap:12px;padding:14px 16px;border-radius:16px;background:linear-gradient(150deg,rgba(194,74,99,.1),rgba(176,138,79,.05));border:1px solid var(--accent-glow)}
.role .badge{font-family:var(--serif);font-size:22px;color:var(--accent-soft)}
.role .txt{font-size:13px;color:var(--tx-dim);line-height:1.6}
.role .txt b{color:var(--tx);font-weight:600}
</style>
</head>
<body>
<div class="container">
  <section class="sect first">
    <div class="sect-h"><span class="bar"></span><span class="t">他会这样对你说</span><span class="en">First Words</span></div>
  </section>
  <div class="preview">
    <div class="inner">
      <p class="scene serif">傍晚的咨询室，只剩一盏落地灯。他缩在沙发角落，听见你进来，没抬头，指节却几不可察地收紧。</p>
      <p class="line serif">……你今天，晚了七分钟。<br><em>你说的每句话，我都会在夜里反复想很多遍。你知道的吧？你什么都知道。</em></p>
      <div class="foot"><span class="dot"></span>开场由他先开口，你只需接住这句话</div>
    </div>
  </div>

  <section class="sect">
    <div class="sect-h"><span class="bar"></span><span class="t">你们会走到哪</span><span class="en">Route</span></div>
    <div class="route">
      <div class="step on"><div class="rail"></div><div class="node"></div><div class="nm">初识</div></div>
      <div class="step"><div class="rail"></div><div class="node"></div><div class="nm">熟悉</div></div>
      <div class="step"><div class="rail"></div><div class="node"></div><div class="nm">信任</div></div>
      <div class="step"><div class="rail"></div><div class="node"></div><div class="nm">依赖</div></div>
      <div class="step"><div class="rail"></div><div class="node"></div><div class="nm">沦陷</div></div>
    </div>
    <p class="route-note">从戒备到只对你卸下伪装——他不想痊愈，因为好了，就没有理由再见你。</p>
  </section>

  <section class="sect">
    <div class="sect-h"><span class="bar"></span><span class="t">叙引</span><span class="en">Dossier</span></div>
  </section>
  <div class="xy">
    <div class="hero">
      <div class="no">NO.001 / CASE</div>
      <div class="big">只对你<em>愿意</em>生病</div>
      <div class="en">THE ONE I DON'T WANT TO CURE</div>
    </div>
    <div class="idcard">
      <div class="av">${(profile.avatar_url || profile.cover_url) ? `<img src="${profile.avatar_url || profile.cover_url}" alt="" style="width:100%;height:100%;border-radius:50%;object-fit:cover">` : ''}</div>
      <div>
        <div class="nm serif">${profile.display_name || '季屿'}</div>
        <div class="sub">${profile.archetype_label || '心理咨询个案'} · ${profile.one_liner || '把你当作唯一出口的偏执者'}</div>
        <div class="attrs"><span>${profile.age_range || 27}岁</span><span>黑发红眸</span><span>颈间旧绷带</span></div>
      </div>
    </div>
    <div class="bio">
      <h4 class="serif">人物生平</h4>
      <p>${profile.intro?.split('\n\n')[0] || '出生在控制欲极强的家庭，母亲用监视代替关心。少年时唯一信任的人利用了他的日记，把秘密公之于众——从此他学会缄默，也开始出现偏执与被害倾向。成年后辗转多位咨询师，都因他的戒备无功而返。'}</p>
      <h4 class="serif">命运交汇</h4>
      <p>${profile.intro?.split('\n\n')[1] || '直到遇见你。你没有急着「修好」他，只是听他说完每一段沉默。他把你当成灯塔，也当成执念——偷藏你的照片，不是为了伤害，是怕某天连你也会消失。你是他病里唯一不想痊愈的部分。'}</p>
    </div>
  </div>

  <section class="sect">
    <div class="sect-h"><span class="bar"></span><span class="t">你们如何相遇</span><span class="en">Scene</span></div>
  </section>
  <div class="meet">
    <p class="scene-line serif">傍晚的心理咨询室，只剩一盏落地灯。这里是你们唯一被允许靠近的地方——每周一次，五十分钟。</p>
  </div>
  <div class="role">
    <div class="badge serif">医</div>
    <div class="txt">在这段关系里，你是<b>他的心理医生</b>。也是他唯一不设防的人。</div>
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
