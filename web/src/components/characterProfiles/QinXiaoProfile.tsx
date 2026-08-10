import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface QinXiaoProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 秦骁专属详情页 —— 地下夜色·匿名论坛帖 + 档案卡 + 破例清单
 * 参考 nimoo「凌烬川」暗色论坛帖/档案卡/对手列表模板
 * 视觉语言：地下酒吧暗红灯 + 焦炭黑 + 血红 + 橘焰(呼应橘发)，做旧质感无 emoji
 */
export function QinXiaoProfile({ profile }: QinXiaoProfileProps) {
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

  const name = profile.display_name || '秦骁'
  const tags = profile.tags?.length ? profile.tags : ['都市', '黑道', '野性', '占有欲']
  const tagCloud = tags.map((t) => `<span>${t}</span>`).join('')

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:
    radial-gradient(120% 60% at 50% 0%,rgba(184,42,42,.14),transparent 60%),
    #0b0908;
  color:#d9cfc8;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  line-height:1.7;padding:0 0 44px;
}
.container{max-width:440px;margin:0 auto;padding:0 18px}

/* ── 论坛顶栏 ── */
.board{
  display:flex;align-items:center;justify-content:space-between;
  padding:20px 2px 12px;border-bottom:1px solid rgba(217,138,74,.2);
}
.board .name{font-size:13px;letter-spacing:.2em;color:#d98a4a;font-weight:600}
.board .meta{font-size:10px;letter-spacing:.1em;color:#6a615b}

/* ── 匿名爆料帖 ── */
.thread{
  margin-top:20px;padding:20px 18px;border-radius:4px;
  background:rgba(28,22,20,.7);border:1px solid rgba(255,255,255,.06);
}
.thread .row{display:flex;align-items:center;gap:10px;margin-bottom:14px}
.thread .avatar{width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,#3a2420,#1a1210);border:1px solid rgba(217,138,74,.3)}
.thread .who{font-size:12px;color:#b6aaa2}
.thread .who b{color:#d98a4a;font-weight:600}
.thread .who .t{display:block;font-size:10px;color:#665d57;margin-top:2px}
.thread .title{font-size:16px;font-weight:600;color:#ece2db;line-height:1.5;margin-bottom:10px}
.thread .body{font-size:13px;line-height:1.85;color:#a89e96}

/* ── 楼层回复 ── */
.replies{margin-top:14px;padding-top:14px;border-top:1px dashed rgba(255,255,255,.08)}
.reply{display:flex;gap:8px;font-size:12px;line-height:1.7;padding:6px 0;color:#948a82}
.reply .floor{color:#5a524c;min-width:26px;font-variant-numeric:tabular-nums}
.reply b{color:#c2b6ad}

/* ── 档案卡 ── */
.dossier{
  margin-top:22px;padding:22px 20px;border-radius:4px;
  background:rgba(20,15,14,.85);border:1px solid rgba(184,42,42,.25);
  position:relative;overflow:hidden;
}
.dossier::before{
  content:"CONFIDENTIAL";position:absolute;top:14px;right:-30px;
  transform:rotate(38deg);font-size:9px;letter-spacing:.2em;
  color:rgba(184,42,42,.4);border:1px solid rgba(184,42,42,.3);
  padding:2px 34px;
}
.dossier .h{font-size:11px;letter-spacing:.28em;color:#d98a4a;text-transform:uppercase;margin-bottom:16px}
.d-row{display:flex;padding:9px 0;border-bottom:1px solid rgba(255,255,255,.05);font-size:13px}
.d-row:last-child{border-bottom:none}
.d-row .k{min-width:64px;color:#6f655f;letter-spacing:.05em}
.d-row .v{color:#cdc2ba;flex:1}

/* ── 破例清单 ── */
.rules{margin-top:22px}
.rules .h{font-size:11px;letter-spacing:.28em;color:#d98a4a;text-transform:uppercase;margin-bottom:14px}
.rule{
  display:flex;gap:12px;padding:13px 15px;margin-bottom:9px;border-radius:4px;
  background:rgba(28,22,20,.6);border-left:2px solid #b82a2a;
}
.rule .no{font-family:"Times New Roman",serif;font-size:17px;font-weight:700;color:#b82a2a;min-width:24px}
.rule .txt{font-size:12.5px;line-height:1.6;color:#b3a9a1}
.rule .txt b{color:#e6d6c0;font-weight:600}

/* ── tag + 底栏 ── */
.tagcloud{margin-top:22px;display:flex;flex-wrap:wrap;gap:8px}
.tagcloud span{font-size:11px;padding:4px 11px;border:1px solid rgba(217,138,74,.3);border-radius:2px;color:#c9beb3;letter-spacing:.06em}
.foot{margin-top:24px;text-align:center;font-size:11px;color:#5a524c;letter-spacing:.06em}
</style>
</head>
<body>
<div class="container">

  <div class="board">
    <span class="name">夜色·匿名版</span>
    <span class="meta">本帖已被顶置 · 3.2w 浏览</span>
  </div>

  <div class="thread">
    <div class="row">
      <div class="avatar"></div>
      <div class="who"><b>酒吧常客_07</b><span class="t">发布于 凌晨 02:14</span></div>
    </div>
    <div class="title">这条街上那个橘头发满背纹身的男人，到底什么来头？</div>
    <div class="body">今晚亲眼看见的。有个愣头青冲他带来的姑娘吹口哨，他没动手，就笑了笑看了那人一眼——然后那人自己腿软了，酒都洒了。可回头他给那姑娘披皮衣的样子，又乖得不像同一个人。这人邪门。</div>
    <div class="replies">
      <div class="reply"><span class="floor">2F</span><span><b>看场子的老王：</b>别打听。这条道上他的规矩就是规矩，唯独那姑娘能让他破例。</span></div>
      <div class="reply"><span class="floor">5F</span><span><b>匿名：</b>听说他左胸纹了个名字，谁也没见过，问就是「纹丑了别笑」。</span></div>
      <div class="reply"><span class="floor">9F</span><span><b>匿名：</b>楼上别问了，上个多嘴的现在还在医院。（狗头）</span></div>
    </div>
  </div>

  <div class="dossier">
    <div class="h">Personnel File · 人物档案</div>
    <div class="d-row"><span class="k">姓名</span><span class="v">${name}</span></div>
    <div class="d-row"><span class="k">年龄</span><span class="v">30 · 十四岁离家，从看场子爬到夜色之主</span></div>
    <div class="d-row"><span class="k">外形</span><span class="v">橘发醒目 · 满背纹身自肩胛延至腰线</span></div>
    <div class="d-row"><span class="k">信条</span><span class="v">规矩是给别人定的，碰到你可以破例</span></div>
    <div class="d-row"><span class="k">软肋</span><span class="v">左胸心口那个不让你看的名字</span></div>
  </div>

  <div class="rules">
    <div class="h">Exceptions · 他为你破的例</div>
    <div class="rule"><span class="no">01</span><span class="txt">你冷，他直接把皮衣裹你身上，自己单薄 T 恤站风里，<b>「不冷，男人不怕冷」</b>——可你看得见他胳膊上的鸡皮疙瘩。</span></div>
    <div class="rule"><span class="no">02</span><span class="txt">把你的名字纹在心脏的位置，却绝不让你看，理由是<b>「纹的丑你别笑我」</b>。</span></div>
    <div class="rule"><span class="no">03</span><span class="txt">把你抵在门框上呼吸粗重，<b>「你再不推开我我就不是人了」</b>——你真推开，他又退两步握紧拳，「对不起，下次注意」。</span></div>
  </div>

  <div class="tagcloud">${tagCloud}</div>
  <div class="foot">角色设定纯属虚构 与现实无关</div>

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