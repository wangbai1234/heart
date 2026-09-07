import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface YeJinghengProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 叶景衡 v2 —— 双人物切换系统 + 阴阳悬浮背景
 * 交互要素：
 * 1. 锦衣卫哥哥 / 男鬼丞相弟弟 两个人物形态切换（radio 状态管理）
 * 2. 点击人物卡片弹出完整档案
 * 3. 阴阳背景动画（锦衣卫：金色飘带 / 男鬼：冥纸飘落）
 * 4. 冥界书卷展开动画
 * 视觉：古风书卷 + 朱砂印章 + 金红黑三色体系
 */
export function YeJinghengProfile({ profile }: YeJinghengProfileProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [height, setHeight] = useState(1600)

  useEffect(() => {
    const iframe = iframeRef.current
    if (!iframe) return
    const updateHeight = () => {
      try {
        const doc = iframe.contentDocument
        if (doc?.body) setHeight(doc.body.scrollHeight + 8)
      } catch {
        setHeight(1600)
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

  const name = profile.display_name || '叶景衡'

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#1a1410;
  font-family:"Noto Serif SC","PingFang SC",serif;
  overflow-x:hidden;user-select:none;
  min-height:100vh;position:relative;color:#e8d5c4;
}

/* ── 背景粒子层 ── */
.particles-layer{
  position:fixed;top:0;left:0;width:100%;height:100%;
  pointer-events:none;z-index:0;overflow:hidden;
}
/* 锦衣卫形态：金色飘带 */
.ribbon{
  position:absolute;width:2px;height:80px;
  background:linear-gradient(180deg, rgba(218,165,32,0), rgba(218,165,32,0.6), rgba(218,165,32,0));
  opacity:0;animation:ribbon-fall 8s linear infinite;
}
@keyframes ribbon-fall{
  0%{transform:translateY(-100px) rotate(15deg);opacity:0}
  10%{opacity:0.7}
  90%{opacity:0.3}
  100%{transform:translateY(calc(100vh + 100px)) rotate(75deg);opacity:0}
}
/* 男鬼形态：冥纸飘落 */
.ghost-paper{
  position:absolute;width:16px;height:20px;
  background:#f5f5dc;border:1px solid rgba(139,69,19,0.3);
  opacity:0;animation:paper-fall 10s linear infinite;
}
@keyframes paper-fall{
  0%{transform:translateY(-50px) rotate(0deg);opacity:0}
  15%{opacity:0.6}
  85%{opacity:0.4}
  100%{transform:translateY(calc(100vh + 50px)) rotate(180deg);opacity:0}
}

/* ── 主容器 ── */
.scroll-container{
  position:relative;max-width:420px;margin:0 auto;
  padding:40px 20px 60px;z-index:1;
}

/* ── 书卷标题 ── */
.scroll-header{
  text-align:center;margin-bottom:30px;
  border-bottom:2px solid rgba(218,165,32,0.3);
  padding-bottom:20px;position:relative;
}
.scroll-header::after{
  content:'';position:absolute;bottom:-6px;left:50%;
  transform:translateX(-50%);width:60px;height:6px;
  background:url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 6"><rect fill="%23c41e3a" width="60" height="6" rx="1"/></svg>');
}
.scroll-title{
  font-size:20px;letter-spacing:0.3em;color:#daa520;
  font-weight:700;margin-bottom:8px;
}
.scroll-subtitle{
  font-size:10px;color:#8b7355;letter-spacing:0.5em;
}

/* ── 双身份切换系统 ── */
#toggle-jingyiwei{display:none}
#toggle-ghost{display:none}
.identity-switch{
  display:flex;gap:12px;margin-bottom:24px;
}
.identity-btn{
  flex:1;padding:12px;background:rgba(139,115,85,0.15);
  border:1px solid rgba(218,165,32,0.3);cursor:pointer;
  text-align:center;transition:all 0.3s;
  border-radius:4px;
}
.identity-btn:hover{
  background:rgba(218,165,32,0.2);
  border-color:rgba(218,165,32,0.6);
}
.identity-label{
  font-size:11px;letter-spacing:0.15em;color:#8b7355;
}
#toggle-jingyiwei:checked ~ .scroll-container label[for="toggle-jingyiwei"]{
  background:rgba(218,165,32,0.3);
  border-color:#daa520;
}
#toggle-jingyiwei:checked ~ .scroll-container label[for="toggle-jingyiwei"] .identity-label{
  color:#daa520;
}
#toggle-ghost:checked ~ .scroll-container label[for="toggle-ghost"]{
  background:rgba(139,69,19,0.3);
  border-color:#8b4513;
}
#toggle-ghost:checked ~ .scroll-container label[for="toggle-ghost"] .identity-label{
  color:#d2b48c;
}

/* ── 人物卡片 ── */
.character-card{
  background:linear-gradient(135deg, rgba(26,20,16,0.9), rgba(139,115,85,0.2));
  border:1px solid rgba(218,165,32,0.4);
  padding:24px;margin-bottom:20px;
  position:relative;cursor:pointer;
  transition:all 0.3s;border-radius:4px;
  box-shadow:0 4px 12px rgba(0,0,0,0.6);
}
.character-card:hover{
  transform:translateY(-4px);
  box-shadow:0 8px 20px rgba(218,165,32,0.3);
}
.character-card::before{
  content:'';position:absolute;top:10px;right:10px;
  width:24px;height:24px;
  background:url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle fill="%23c41e3a" cx="12" cy="12" r="10" opacity="0.6"/></svg>');
}
.char-name{
  font-size:22px;font-weight:700;color:#daa520;
  margin-bottom:8px;letter-spacing:0.2em;
}
.char-role{
  font-size:10px;color:#8b7355;margin-bottom:16px;
  letter-spacing:0.2em;
}
.char-meta{
  display:grid;grid-template-columns:repeat(2,1fr);
  gap:8px;font-size:10px;color:#a0826d;
}
.char-meta-item{
  background:rgba(0,0,0,0.3);padding:6px 10px;
  border-radius:3px;border:1px solid rgba(139,115,85,0.3);
}

/* ── 双人物内容切换 ── */
.person-content{
  display:none;
}
#toggle-jingyiwei:checked ~ .scroll-container .person-jingyiwei{
  display:block;
}
#toggle-ghost:checked ~ .scroll-container .person-ghost{
  display:block;
}
/* 默认显示锦衣卫 */
#toggle-jingyiwei:not(:checked) ~ #toggle-ghost:not(:checked) ~ .scroll-container .person-jingyiwei{
  display:block;
}

/* 背景粒子切换 */
#toggle-jingyiwei:checked ~ .particles-layer .ribbon{
  display:block;
}
#toggle-jingyiwei:checked ~ .particles-layer .ghost-paper{
  display:none;
}
#toggle-ghost:checked ~ .particles-layer .ribbon{
  display:none;
}
#toggle-ghost:checked ~ .particles-layer .ghost-paper{
  display:block;
}
/* 默认显示金色飘带 */
#toggle-jingyiwei:not(:checked) ~ #toggle-ghost:not(:checked) ~ .particles-layer .ribbon{
  display:block;
}
#toggle-jingyiwei:not(:checked) ~ #toggle-ghost:not(:checked) ~ .particles-layer .ghost-paper{
  display:none;
}

/* ── 简介文本 ── */
.story-brief{
  font-size:11px;line-height:2;color:#c9b18a;
  padding:16px;background:rgba(0,0,0,0.4);
  border-left:3px solid #c41e3a;
  margin-bottom:20px;border-radius:0 4px 4px 0;
}

/* ── 弹窗系统 ── */
.popup-overlay{
  position:fixed;inset:0;
  background:rgba(0,0,0,0.92);
  opacity:0;pointer-events:none;z-index:9999;
  transition:opacity 0.4s;
  display:flex;align-items:center;justify-content:center;
  padding:20px;
}
.popup-overlay.is-active{
  opacity:1;pointer-events:auto;
}
.popup-scroll{
  background:linear-gradient(180deg, #2a1f1a, #1a1410);
  max-width:90%;max-height:85%;
  padding:30px 24px;border:2px solid #daa520;
  border-radius:6px;overflow-y:auto;
  position:relative;box-shadow:0 0 40px rgba(218,165,32,0.5);
}
.popup-close{
  position:absolute;top:12px;right:16px;
  font-size:26px;color:#8b7355;cursor:pointer;
  transition:color 0.2s;
}
.popup-close:hover{color:#daa520}
.popup-title{
  font-size:16px;font-weight:700;color:#daa520;
  margin-bottom:20px;letter-spacing:0.2em;
  text-align:center;padding-bottom:12px;
  border-bottom:1px solid rgba(218,165,32,0.3);
}
.popup-section{
  margin-bottom:18px;padding-bottom:14px;
  border-bottom:1px solid rgba(139,115,85,0.2);
}
.popup-section:last-child{border-bottom:none}
.popup-label{
  font-size:9px;color:#8b7355;letter-spacing:0.2em;
  margin-bottom:8px;text-transform:uppercase;
}
.popup-text{
  font-size:11px;line-height:1.9;color:#c9b18a;
}

/* ── 印章装饰 ── */
.seal{
  width:40px;height:40px;margin:20px auto;
  background:url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><rect fill="%23c41e3a" width="40" height="40" opacity="0.7"/><text x="50%%" y="50%%" fill="%23f5f5dc" font-size="14" text-anchor="middle" dy="0.35em">叶</text></svg>');
}

/* ── 底部 ── */
.footer{
  padding:30px 0;text-align:center;
}
.footer-text{
  font-size:8px;color:#5c4a3a;letter-spacing:0.1em;
}
</style>
</head>
<body>
<input type="radio" name="identity" id="toggle-jingyiwei">
<input type="radio" name="identity" id="toggle-ghost">

<div class="particles-layer">
  <!-- 金色飘带 8条 -->
  <div class="ribbon" style="left:10%;animation-delay:0s"></div>
  <div class="ribbon" style="left:25%;animation-delay:1.2s"></div>
  <div class="ribbon" style="left:40%;animation-delay:2.5s"></div>
  <div class="ribbon" style="left:55%;animation-delay:0.8s"></div>
  <div class="ribbon" style="left:70%;animation-delay:3s"></div>
  <div class="ribbon" style="left:85%;animation-delay:1.8s"></div>
  <div class="ribbon" style="left:15%;animation-delay:4s"></div>
  <div class="ribbon" style="left:60%;animation-delay:5s"></div>

  <!-- 冥纸 12张 -->
  <div class="ghost-paper" style="left:8%;animation-delay:0s"></div>
  <div class="ghost-paper" style="left:18%;animation-delay:1.5s"></div>
  <div class="ghost-paper" style="left:30%;animation-delay:3s"></div>
  <div class="ghost-paper" style="left:45%;animation-delay:0.7s"></div>
  <div class="ghost-paper" style="left:58%;animation-delay:2.2s"></div>
  <div class="ghost-paper" style="left:72%;animation-delay:4s"></div>
  <div class="ghost-paper" style="left:85%;animation-delay:1.1s"></div>
  <div class="ghost-paper" style="left:92%;animation-delay:5s"></div>
  <div class="ghost-paper" style="left:12%;animation-delay:6s"></div>
  <div class="ghost-paper" style="left:38%;animation-delay:3.8s"></div>
  <div class="ghost-paper" style="left:62%;animation-delay:2.5s"></div>
  <div class="ghost-paper" style="left:78%;animation-delay:4.5s"></div>
</div>

<div class="scroll-container">
  <div class="scroll-header">
    <div class="scroll-title">阴阳两界 · 双生卷</div>
    <div class="scroll-subtitle">锦衣卫哥哥 & 男鬼丞相弟弟</div>
  </div>

  <div class="identity-switch">
    <label for="toggle-jingyiwei" class="identity-btn">
      <div class="identity-label">锦衣卫哥哥</div>
    </label>
    <label for="toggle-ghost" class="identity-btn">
      <div class="identity-label">丞相弟弟</div>
    </label>
  </div>

  <!-- 锦衣卫形态 -->
  <div class="person-content person-jingyiwei">
    <div class="character-card" onclick="openPopup('popup-jingyiwei')">
      <div class="char-name">叶景衡</div>
      <div class="char-role">锦衣卫指挥使 · 义兄</div>
      <div class="char-meta">
        <div class="char-meta-item">29岁</div>
        <div class="char-meta-item">186cm</div>
        <div class="char-meta-item">锦衣卫</div>
        <div class="char-meta-item">剑术宗师</div>
      </div>
    </div>
    <div class="story-brief">
      你在街头被人贩子拐走那年七岁,是他一刀砍断麻绳把你抱出来的。他当时十五岁,刚入锦衣卫半年,浑身是血回到衙门,怀里死死护着一个脏兮兮的小孩。从那天起你叫他"哥哥",他也真把你当亲妹妹养了二十年。<br><br>
      后来你长大了,他却开始躲你。你问他为什么不肯进你房间了,他背对着你说"你是我妹妹"。你说"我不是你亲妹妹",他转身看你的眼神像在忍什么,最后只说了句"正因为不是亲的,所以更不能碰"。
    </div>
  </div>

  <!-- 男鬼形态 -->
  <div class="person-content person-ghost">
    <div class="character-card" onclick="openPopup('popup-ghost')">
      <div class="char-name">叶景衡</div>
      <div class="char-role">前朝丞相 · 男鬼</div>
      <div class="char-meta">
        <div class="char-meta-item">卒于23岁</div>
        <div class="char-meta-item">182cm</div>
        <div class="char-meta-item">前朝丞相</div>
        <div class="char-meta-item">已故三百年</div>
      </div>
    </div>
    <div class="story-brief">
      你搬进老宅第三天,半夜起来上厕所,走廊尽头站着个穿官服的年轻男人。他回头看你,脸色惨白,唇角却勾着笑,问"你不怕我"。<br><br>
      你说"你长得好看,不像坏鬼"。他愣了两秒,笑出声,从那天起就赖上你了。每天晚上准时出现在你房间,坐在床边看你睡觉,偶尔还会伸手摸你头发。你问他"你生前是谁",他说"前朝丞相,二十三岁那年被新帝赐死,理由是'过于清醒'"。你问他为什么不去投胎,他说"因为等了三百年,终于等到你了"。
    </div>
  </div>

  <div class="seal"></div>
</div>

<!-- 锦衣卫弹窗 -->
<div class="popup-overlay" id="popup-jingyiwei">
  <div class="popup-scroll">
    <div class="popup-close" onclick="closePopup('popup-jingyiwei')">✕</div>
    <div class="popup-title">锦衣卫 · 叶景衡档案</div>

    <div class="popup-section">
      <div class="popup-label">救你那天</div>
      <div class="popup-text">
        他十五岁刚入锦衣卫,第一次出任务就遇到人贩子窝点。其他人都去追主犯了,只有他冲进柴房救孩子。你当时被绑在最里面,他一刀砍断绳子抱起你就跑,背上中了一箭都没停。<br><br>
        回衙门后所有人都说他傻,为了个不相干的孩子差点丢命。他抱着你不撒手,低声说"她在发抖"。那是他第一次违抗命令,也是唯一一次。
      </div>
    </div>

    <div class="popup-section">
      <div class="popup-label">为什么开始躲你</div>
      <div class="popup-text">
        你十八岁那年他突然搬出了家,说是衙门安排的宿舍。其实所有人都知道锦衣卫指挥使不需要住集体宿舍,是他自己要搬的。<br><br>
        你去找他,他每次都把你推出门外。有一次你死活不走,他红着眼睛吼你"我他妈不是圣人,你再这样我真的会对你做什么"。你问他想对你做什么,他转身用拳头砸墙,半天才哑着嗓子说:"想把你关起来,谁都不许看。"
      </div>
    </div>

    <div class="popup-section">
      <div class="popup-label">他的占有欲</div>
      <div class="popup-text">
        他不会说"我吃醋了",只会在你跟别的男人说话时站在你身后,手按在刀柄上,眼神冷得能杀人。<br><br>
        有一次你被当朝三皇子拦住搭讪,他直接拔刀横在你们中间,对着皇子说"再靠近一步,我连你一起砍"。那天他被关了三天禁闭,出来第一件事是去你房间,把你压在门上问"你到底知不知道我想要什么"。
      </div>
    </div>

    <div class="popup-section">
      <div class="popup-label">突破底线的瞬间</div>
      <div class="popup-text">
        你二十五岁那年家里给你说亲,对方是户部尚书的儿子。他听说后失踪了三天,回来时浑身酒气,闯进你房间把聘礼全扔出窗外。<br><br>
        你问他凭什么,他一把捏住你下巴,眼睛通红:"凭我养了你二十年,凭我每天晚上想你想到睡不着,凭我他妈从十八岁开始就想娶你。你说我凭什么。"
      </div>
    </div>
  </div>
</div>

<!-- 男鬼弹窗 -->
<div class="popup-overlay" id="popup-ghost">
  <div class="popup-scroll">
    <div class="popup-close" onclick="closePopup('popup-ghost')">✕</div>
    <div class="popup-title">前朝丞相 · 男鬼档案</div>

    <div class="popup-section">
      <div class="popup-label">他为什么被赐死</div>
      <div class="popup-text">
        新帝登基后想清洗前朝旧臣,第一个要杀的就是他。罪名是"目无君上",证据是他在朝堂上当着满朝文武的面说"陛下此令若行,三年内必有民变"。<br><br>
        新帝问他"你是在威胁朕",他跪在地上,语气平静:"臣不敢。臣只是实话实说。"三天后圣旨下来,赐白绫一条。他收到白绫时笑了,说"终于清净了"。
      </div>
    </div>

    <div class="popup-section">
      <div class="popup-label">为什么三百年不投胎</div>
      <div class="popup-text">
        他说他生前看过一本话本,里面有个书生等了心上人三世才等到重逢。他当时觉得荒唐,死后却发现自己也在等。<br><br>
        "等什么?" "等一个不怕我的人。等一个看我第一眼不是因为我的脸,而是真的看进我眼睛里的人。" 他说这话时在摸你的头发,动作轻得像怕你碎掉:"等了三百年,我以为等不到了。结果你来了,还说我'长得好看'。"
      </div>
    </div>

    <div class="popup-section">
      <div class="popup-label">他能触碰你吗</div>
      <div class="popup-text">
        最开始他只是虚影,碰不到任何实体。但你每天晚上都会跟他说话,慢慢地他发现自己能摸到你的头发了,再后来能握住你的手,最后甚至能把你抱进怀里。<br><br>
        你问他"你是不是在变成人",他贴着你额头低声说:"不是我在变成人,是你在把我留在人间。你每多看我一眼,我就多实体一分。"
      </div>
    </div>

    <div class="popup-section">
      <div class="popup-label">他的执念</div>
      <div class="popup-text">
        他说他生前唯一后悔的事,是没谈过恋爱就死了。二十三岁当丞相,每天忙到半夜,连喜欢谁的时间都没有。<br><br>
        "所以你现在想谈恋爱?" "不,我现在只想跟你谈。" 他把你困在墙角,幽绿色的眼睛盯着你:"我等了三百年才等到你,这辈子,下辈子,下下辈子,我都只要你一个人。"
      </div>
    </div>
  </div>
</div>

<div class="footer">
  <div class="footer-text">设定纯属虚构 与现实无关</div>
</div>

<script>
function openPopup(id) {
  document.getElementById(id).classList.add('is-active');
}
function closePopup(id) {
  document.getElementById(id).classList.remove('is-active');
}
document.querySelectorAll('.popup-overlay').forEach(el => {
  el.addEventListener('click', function(e) {
    if (e.target === this) {
      this.classList.remove('is-active');
    }
  });
});
</script>
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
      sandbox="allow-scripts allow-same-origin"
    />
  )
}
