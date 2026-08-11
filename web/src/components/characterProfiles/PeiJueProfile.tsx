import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface PeiJueProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 裴决专属详情页 —— 政事堂折子 · 密奏呈览
 * 视觉隐喻：摄政王批阅奏章的文牍，玄纸朱批，权谋与深情藏在公文格式里
 * 色彩：墨黑底 + 朱砂红 + 象牙白，模拟宣纸质感
 */
export function PeiJueProfile({ profile }: PeiJueProfileProps) {
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

  const name = profile.display_name || '裴决'
  const age = 29
  const tags = profile.tags?.length ? profile.tags : ['古风', '权谋', '高岭之花', '腹黑']
  const tagCloud = tags.map((t) => `#${t}`).join('&nbsp;&nbsp;')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#0a0a0c;
  color:#e8ddd0;
  font-family:"Songti SC","STSong","SimSun",serif;
  line-height:1.9;
  padding:0 0 48px;
}
.container{max-width:420px;margin:0 auto;padding:0 20px}

/* ── 文牍抬头 ── */
.header{
  padding:28px 0 16px;
  border-bottom:2px solid rgba(195,68,58,.4);
  text-align:center;
}
.seal{
  width:64px;height:64px;margin:0 auto 12px;
  background:radial-gradient(circle,rgba(195,68,58,.15),transparent 70%);
  border:1.5px solid rgba(195,68,58,.6);
  border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-size:18px;font-weight:600;color:#c3443a;letter-spacing:.3em;
}
.doc-title{
  font-size:22px;letter-spacing:.8em;color:#c3443a;margin-bottom:6px;
}
.doc-sub{
  font-size:12px;color:#998877;letter-spacing:.4em;
}

/* ── 奏章主体 ── */
.memorial{
  padding:32px 0;
  border-bottom:1px solid rgba(255,255,255,.06);
}
.mem-label{
  font-size:11px;color:#c3443a;letter-spacing:.3em;margin-bottom:8px;
  border-left:3px solid #c3443a;padding-left:10px;
}
.mem-content{
  font-size:14px;line-height:2.1;color:#d4c4b0;text-indent:2em;
  margin-bottom:18px;
}
.mem-row{
  display:flex;margin-bottom:10px;font-size:13px;
}
.mem-row .label{
  color:#b59b82;min-width:70px;letter-spacing:.2em;
}
.mem-row .value{
  color:#e8ddd0;flex:1;
}

/* ── 朱批（核心信息）── */
.zhu-pi{
  padding:26px 0;
  border-bottom:1px solid rgba(255,255,255,.06);
}
.zhu-pi-head{
  font-size:12px;color:#c3443a;letter-spacing:.4em;margin-bottom:16px;
  text-align:center;
}
.zhu-pi-text{
  font-size:15px;line-height:2.2;color:#c3443a;
  text-align:justify;font-weight:500;
  background:linear-gradient(135deg,rgba(195,68,58,.08),transparent);
  padding:16px;border-left:3px solid #c3443a;border-radius:4px;
}

/* ── 档案标签 ── */
.tags{
  padding:24px 0;
  border-bottom:1px solid rgba(255,255,255,.06);
}
.tags-label{
  font-size:11px;color:#998877;letter-spacing:.3em;margin-bottom:12px;
}
.tags-cloud{
  font-size:12px;line-height:2.4;color:#b59b82;letter-spacing:.08em;
}

/* ── 密档·秘闻 ── */
.backstory{
  padding:28px 0;
}
.back-label{
  font-size:11px;color:#998877;letter-spacing:.3em;margin-bottom:14px;
  text-align:center;
}
.back-text{
  font-size:13px;line-height:2.3;color:#b59b82;
  text-align:justify;text-indent:2em;
}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="seal">裴</div>
    <div class="doc-title">密奏呈览</div>
    <div class="doc-sub">本朝摄政王档 · 极密</div>
  </div>

  <div class="memorial">
    <div class="mem-label">臣工卷宗</div>
    <div class="mem-row"><span class="label">姓名</span><span class="value">${name}</span></div>
    <div class="mem-row"><span class="label">年岁</span><span class="value">${age}岁</span></div>
    <div class="mem-row"><span class="label">职衔</span><span class="value">摄政王 · 执掌半壁江山</span></div>
    <div class="mem-row"><span class="label">评语</span><span class="value">龙椅之侧的影子 · 万人之上的孤家</span></div>
  </div>

  <div class="memorial">
    <div class="mem-label">密奏·其人</div>
    <div class="mem-content">
      他的世界只有两种人：你，和棋子。墨发披落、白袍外拢玄色披风，替年幼皇帝执掌半壁江山。
      朝堂上他翻手为云覆手为雨，一道折子能决人生死，百官见他如见阎王。可这个让天下人胆寒的男人，
      会在批完奏章的深夜忽然搁笔，盯着你随手留在案头的一朵干花出神。
    </div>
    <div class="mem-content">
      他不说想你——他会说「今日政务繁忙，你若不来，我便下不了这盘棋」。
      他的占有欲藏在帝王的体面下：你身边多了个面生的侍卫，次日那人就会被调去守城门；
      有人在宴上多看你一眼，他只是微微一笑，那人第二天便接到了外放三千里的调令。
    </div>
  </div>

  <div class="zhu-pi">
    <div class="zhu-pi-head">朱批手谕</div>
    <div class="zhu-pi-text">
      可当夜深人静，这个把天下人玩弄于股掌的男人会把额头抵在你肩窝，声音低得像在求你：
      「别走。我这辈子只怕一件事——你转身的样子。」
    </div>
  </div>

  <div class="tags">
    <div class="tags-label">档案标签</div>
    <div class="tags-cloud">${tagCloud}</div>
  </div>

  <div class="backstory">
    <div class="back-label">密档·秘闻</div>
    <div class="back-text">
      幼年质子出身，在别国冷宫里熬过十年，被当作弃子时学会了不信任何人。
      归国后步步为营坐到摄政之位，见惯了以情为刀的算计，本以为此生只与权谋为伴。
      他最深的伤口是：从没有人真正想留住他这个「人」，所有人要的都是他手中的权力。
      直到遇见你——一个不看他权势、只看他人的人。
    </div>
  </div>

</div>
</body>
</html>`

  return (
    <iframe
      ref={iframeRef}
      title={\`\${name} profile\`}
      srcDoc={htmlContent}
      style={{
        width: '100%',
        height: \`\${height}px\`,
        border: 'none',
        display: 'block',
        background: 'transparent',
      }}
      sandbox="allow-same-origin"
    />
  )
}

  <div class="memorial">
    <div class="mem-label">人物概要</div>
    <div class="mem-content">
      ${name}，年二十有九，本朝摄政王，替年幼皇帝执掌半壁江山。墨发披落，白袍外拢玄色披风，立于朝堂与灯影之间。表面清隽儒雅，话不多却字字落地成钉，实则心思深如古井，满朝党争在他眼里不过盘中残局。
    </div>
    <div class="mem-row">
      <span class="label">年岁</span>
      <span class="value">${age} 岁</span>
    </div>
    <div class="mem-row">
      <span class="label">身份</span>
      <span class="value">本朝摄政王 · 执棋人 · 龙椅之侧的影子</span>
    </div>
    <div class="mem-row">
      <span class="label">性情</span>
      <span class="value">对旁人永远隔着三尺寒意 · 唯对一人露出缝隙</span>
    </div>
  </div>

  <div class="zhu-pi">
    <div class="zhu-pi-head">— 朱批 —</div>
    <div class="zhu-pi-text">
      这满朝文武的算计，独你算不过我，也独你不必算。<br><br>
      他的世界只有两种人：你，和棋子。朝堂上他翻手为云覆手为雨，可这个让天下人胆寒的男人，会在你无意间打了个喷嚏时，不动声色地让人把整座暖阁的地龙烧旺三分。他不说想你——他会说「今日政务繁忙，你若不来，我便下不了这盘棋」。<br><br>
      可当夜深人静，这个把天下人玩弄于股掌的男人会把额头抵在你肩窝，声音低得像在求你：「别走。我这辈子只怕一件事——你转身的样子。」
    </div>
  </div>

  <div class="tags">
    <div class="tags-label">标签档案</div>
    <div class="tags-cloud">${tagCloud}</div>
  </div>

  <div class="backstory">
    <div class="back-label">— 密档 · 秘闻 —</div>
    <div class="back-text">
      幼年质子出身，在别国冷宫里熬过十年，被当作弃子时学会了不信任何人。归国后步步为营坐到摄政之位，见惯了以情为刀的算计，本以为此生只与权谋为伴。他最深的伤口是：从没有人真正想留住他这个「人」，所有人要的都是他手中的权力。直到遇见你——一个不看他权势、只看他人的人。他最害怕的不是失去江山，而是有一天你也学会用「摄政王」三个字称呼他。
    </div>
  </div>
</div>
</body>
</html>`

  return (
    <div className="profile-wrapper">
      <iframe
        ref={iframeRef}
        srcDoc={htmlContent}
        style={{ width: '100%', height, border: 'none', display: 'block' }}
        title={`${name}的档案`}
        sandbox="allow-same-origin"
      />
    </div>
  )
}

