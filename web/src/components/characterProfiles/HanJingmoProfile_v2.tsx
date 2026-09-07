import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface HanJingmoProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 韩靖墨 v2 —— 港圈养父多重身份切换系统
 * 交互要素：
 * 1. 三个身份面板切换：黑道/白道/养父（radio 状态管理）
 * 2. 档案卡片堆叠系统（点击翻开查看多个养女档案）
 * 3. 粤语金句悬浮气泡动画
 * 4. 霓虹灯闪烁效果 + 维港夜景背景
 * 视觉：香港黑帮电影质感 + 金红黑配色 + 繁体字 + 烟雾效果
 */
export function HanJingmoProfile({ profile }: HanJingmoProfileProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [height, setHeight] = useState(1700)

  useEffect(() => {
    const iframe = iframeRef.current
    if (!iframe) return
    const updateHeight = () => {
      try {
        const doc = iframe.contentDocument
        if (doc?.body) setHeight(doc.body.scrollHeight + 8)
      } catch {
        setHeight(1700)
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

  const name = profile.display_name || '韩靖墨'

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#0d0d0d;
  font-family:"Noto Sans HK","PingFang HK",sans-serif;
  overflow-x:hidden;user-select:none;
  min-height:100vh;position:relative;color:#e8d5c4;
}

/* ── 维港夜景背景 ── */
.hk-skyline{
  position:fixed;bottom:0;left:0;width:100%;height:40%;
  background:linear-gradient(0deg, #1a0f0f 0%, transparent 100%);
  pointer-events:none;z-index:0;
}
.neon-glow{
  position:fixed;top:20%;left:10%;
  width:120px;height:120px;
  background:radial-gradient(circle, rgba(218,32,32,0.3), transparent 70%);
  border-radius:50%;filter:blur(40px);
  animation:neon-pulse 4s ease-in-out infinite;
  pointer-events:none;z-index:0;
}
@keyframes neon-pulse{
  0%, 100%{opacity:0.4;transform:scale(1)}
  50%{opacity:0.7;transform:scale(1.15)}
}
.neon-glow:nth-child(2){
  left:auto;right:15%;top:60%;
  background:radial-gradient(circle, rgba(218,165,32,0.25), transparent 70%);
  animation-delay:2s;
}

/* ── 烟雾粒子 ── */
.smoke{
  position:absolute;width:100px;height:100px;
  background:radial-gradient(circle, rgba(255,255,255,0.03), transparent 70%);
  border-radius:50%;opacity:0;
  animation:smoke-rise 12s linear infinite;
}
@keyframes smoke-rise{
  0%{transform:translateY(100vh) scale(0.5);opacity:0}
  10%{opacity:0.15}
  90%{opacity:0.05}
  100%{transform:translateY(-20vh) scale(1.5);opacity:0}
}

/* ── 主容器 ── */
.triad-container{
  position:relative;max-width:440px;margin:0 auto;
  padding:40px 20px 60px;z-index:1;
}

/* ── 霓虹招牌 ── */
.neon-sign{
  text-align:center;margin-bottom:30px;
  position:relative;
}
.neon-title{
  font-size:28px;font-weight:900;color:#da2020;
  letter-spacing:0.15em;
  text-shadow:0 0 10px rgba(218,32,32,0.8),
              0 0 20px rgba(218,32,32,0.5),
              0 0 30px rgba(218,32,32,0.3);
  animation:neon-flicker 3s infinite;
}
@keyframes neon-flicker{
  0%, 100%{opacity:1}
  2%, 8%, 12%{opacity:0.8}
  4%, 10%{opacity:1}
}
.neon-subtitle{
  font-size:11px;color:#daa520;letter-spacing:0.3em;
  margin-top:8px;
}

/* ── 人物档案卡 ── */
.boss-card{
  background:linear-gradient(135deg, #1a0f0f, #2a1a1a);
  border:2px solid rgba(218,32,32,0.5);
  padding:24px;margin-bottom:24px;
  position:relative;
  box-shadow:0 4px 20px rgba(0,0,0,0.8),
             inset 0 1px 0 rgba(218,32,32,0.2);
}
.boss-card::before{
  content:'大佬';position:absolute;top:12px;right:12px;
  font-size:10px;color:rgba(218,165,32,0.5);
  font-weight:700;letter-spacing:0.2em;
}
.boss-name{
  font-size:26px;font-weight:900;color:#da2020;
  margin-bottom:6px;letter-spacing:0.1em;
}
.boss-title{
  font-size:11px;color:#8b4513;margin-bottom:14px;
  letter-spacing:0.15em;
}
.boss-meta{
  display:flex;gap:10px;flex-wrap:wrap;
  font-size:10px;
}
.boss-meta-tag{
  background:rgba(218,32,32,0.15);
  padding:4px 10px;border:1px solid rgba(218,32,32,0.3);
  color:#c9b18a;border-radius:2px;
}

/* ── 三重身份切换 ── */
#toggle-black{display:none}
#toggle-white{display:none}
#toggle-father{display:none}
.identity-tabs{
  display:flex;gap:8px;margin-bottom:24px;
}
.identity-tab{
  flex:1;padding:12px 8px;
  background:rgba(26,15,15,0.6);
  border:1px solid rgba(139,69,19,0.4);
  cursor:pointer;text-align:center;
  transition:all 0.3s;
  border-radius:3px;
}
.identity-tab:hover{
  background:rgba(218,32,32,0.2);
  border-color:rgba(218,32,32,0.6);
}
.identity-name{
  font-size:10px;letter-spacing:0.15em;color:#8b7355;
  font-weight:600;
}
#toggle-black:checked ~ .triad-container label[for="toggle-black"]{
  background:rgba(218,32,32,0.3);
  border-color:#da2020;
}
#toggle-black:checked ~ .triad-container label[for="toggle-black"] .identity-name{
  color:#da2020;
}
#toggle-white:checked ~ .triad-container label[for="toggle-white"]{
  background:rgba(218,165,32,0.3);
  border-color:#daa520;
}
#toggle-white:checked ~ .triad-container label[for="toggle-white"] .identity-name{
  color:#daa520;
}
#toggle-father:checked ~ .triad-container label[for="toggle-father"]{
  background:rgba(139,69,19,0.3);
  border-color:#8b4513;
}
#toggle-father:checked ~ .triad-container label[for="toggle-father"] .identity-name{
  color:#d2b48c;
}

/* ── 身份内容切换 ── */
.identity-content{display:none}
#toggle-black:checked ~ .triad-container .content-black{display:block}
#toggle-white:checked ~ .triad-container .content-white{display:block}
#toggle-father:checked ~ .triad-container .content-father{display:block}
#toggle-black:not(:checked) ~ #toggle-white:not(:checked) ~ #toggle-father:not(:checked) ~ .triad-container .content-black{
  display:block;
}

.identity-panel{
  background:rgba(0,0,0,0.5);
  border-left:3px solid #da2020;
  padding:16px;margin-bottom:20px;
  border-radius:0 4px 4px 0;
}
.panel-text{
  font-size:11px;line-height:1.9;color:#c9b18a;
}

/* ── 养女档案堆叠系统 ── */
.daughters-stack{
  position:relative;margin:24px 0;
  min-height:200px;
}
.daughter-file{
  position:absolute;
  width:100%;
  background:linear-gradient(135deg, #2a1a1a, #1a0f0f);
  border:1px solid rgba(218,165,32,0.4);
  padding:16px;
  box-shadow:0 2px 8px rgba(0,0,0,0.6);
  cursor:pointer;
  transition:all 0.4s cubic-bezier(0.25,1,0.5,1);
}
.daughter-file:nth-child(1){
  top:0;left:0;z-index:3;
  transform:rotate(-1deg);
}
.daughter-file:nth-child(2){
  top:8px;left:4px;z-index:2;
  transform:rotate(0.5deg);
  opacity:0.85;
}
.daughter-file:nth-child(3){
  top:16px;left:8px;z-index:1;
  transform:rotate(1deg);
  opacity:0.7;
}
.daughter-file:hover{
  transform:translateY(-8px) rotate(0deg) scale(1.02);
  box-shadow:0 8px 24px rgba(218,32,32,0.4);
  z-index:10;
}
.file-label{
  font-size:9px;color:#8b7355;
  letter-spacing:0.15em;margin-bottom:6px;
}
.file-name{
  font-size:14px;font-weight:700;color:#daa520;
  margin-bottom:8px;
}
.file-status{
  font-size:10px;color:#a0826d;
  line-height:1.7;
}
.file-priority{
  position:absolute;top:10px;right:12px;
  width:8px;height:8px;border-radius:50%;
}
.priority-high{background:#da2020;box-shadow:0 0 8px rgba(218,32,32,0.8)}
.priority-normal{background:#daa520;box-shadow:0 0 6px rgba(218,165,32,0.6)}

/* ── 粤语金句气泡 ── */
.quote-bubble{
  position:absolute;
  background:rgba(218,32,32,0.15);
  border:1px solid rgba(218,32,32,0.4);
  padding:8px 12px;border-radius:16px;
  font-size:10px;color:#c9b18a;
  opacity:0;pointer-events:none;
  animation:bubble-float 8s ease-in-out infinite;
}
@keyframes bubble-float{
  0%, 100%{opacity:0;transform:translateY(20px)}
  10%, 90%{opacity:0.8}
  50%{transform:translateY(-10px)}
}
.quote-bubble:nth-child(1){
  top:30%;left:5%;
  animation-delay:0s;
}
.quote-bubble:nth-child(2){
  top:50%;right:8%;
  animation-delay:3s;
}
.quote-bubble:nth-child(3){
  top:70%;left:10%;
  animation-delay:6s;
}

/* ── 弹窗 ── */
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
.popup-content{
  background:linear-gradient(180deg, #2a1a1a, #1a0f0f);
  max-width:90%;max-height:85%;
  padding:24px;border:2px solid #da2020;
  border-radius:4px;overflow-y:auto;
  position:relative;
  box-shadow:0 0 40px rgba(218,32,32,0.5);
}
.popup-close{
  position:absolute;top:12px;right:16px;
  font-size:24px;color:#8b7355;cursor:pointer;
}
.popup-title{
  font-size:16px;font-weight:700;color:#da2020;
  margin-bottom:16px;letter-spacing:0.15em;
}
.popup-text{
  font-size:11px;line-height:1.9;color:#c9b18a;
}

/* ── 底部 ── */
.footer{
  padding:30px 0;text-align:center;
}
.footer-text{
  font-size:8px;color:#3a2a2a;letter-spacing:0.1em;
}
</style>
</head>
<body>
<div class="neon-glow"></div>
<div class="neon-glow"></div>
<div class="hk-skyline"></div>

<!-- 烟雾粒子 -->
<div style="position:fixed;inset:0;pointer-events:none;z-index:0;overflow:hidden">
  <div class="smoke" style="left:10%;animation-delay:0s"></div>
  <div class="smoke" style="left:30%;animation-delay:3s"></div>
  <div class="smoke" style="left:50%;animation-delay:6s"></div>
  <div class="smoke" style="left:70%;animation-delay:9s"></div>
  <div class="smoke" style="left:85%;animation-delay:4s"></div>
</div>

<input type="radio" name="identity" id="toggle-black">
<input type="radio" name="identity" id="toggle-white">
<input type="radio" name="identity" id="toggle-father">

<div class="triad-container">
  <div class="neon-sign">
    <div class="neon-title">韓靖墨</div>
    <div class="neon-subtitle">港圈黑白兩道 · 養父</div>
  </div>

  <div class="boss-card">
    <div class="boss-name">${name}</div>
    <div class="boss-title">港島話事人 / 地產大亨 / 收養狂魔</div>
    <div class="boss-meta">
      <div class="boss-meta-tag">42歲</div>
      <div class="boss-meta-tag">188cm</div>
      <div class="boss-meta-tag">黑白通吃</div>
      <div class="boss-meta-tag">養女×7</div>
    </div>
  </div>

  <div class="identity-tabs">
    <label for="toggle-black" class="identity-tab">
      <div class="identity-name">黑道面</div>
    </label>
    <label for="toggle-white" class="identity-tab">
      <div class="identity-name">白道面</div>
    </label>
    <label for="toggle-father" class="identity-tab">
      <div class="identity-name">養父面</div>
    </label>
  </div>

  <!-- 黑道身份 -->
  <div class="identity-content content-black">
    <div class="identity-panel" style="border-left-color:#da2020">
      <div class="panel-text">
        港島三大幫派之一"鴻記"話事人。十八歲出道,二十五歲坐上話事人位置,靠的是夠狠、夠準、夠講義氣。道上人稱"墨爺",說一不二,但從不碰毒品和人口買賣,業內都說他"黑得有底線"。<br><br>
        你是他在茶餐廳遇到的服務員,當時有人來找麻煩,你端著茶壺往那人頭上澆了滾水。他當場笑了,問你"想唔想跟我"。你說"你係咩人",他說"一個可以罩住你嘅人"。
      </div>
    </div>
  </div>

  <!-- 白道身份 -->
  <div class="identity-content content-white">
    <div class="identity-panel" style="border-left-color:#daa520">
      <div class="panel-text">
        港島排名前五的地產開發商,"韓氏集團"董事長。名下物業遍布港九新界,身家保守估計百億起跳。商界人稱"韓生",西裝革履,滴水不漏,談判桌上從不讓步,但私底下會資助街坊小孩讀書。<br><br>
        白道黑道是同一個人,只是看他穿哪套衣服。穿西裝時他是韓生,簽合同喝紅酒;穿黑T時他是墨爺,抽雪茄談規矩。你問他哪個是真的,他說"都係真嘅,唔衝突"。
      </div>
    </div>
  </div>

  <!-- 養父身份 -->
  <div class="identity-content content-father">
    <div class="identity-panel" style="border-left-color:#8b4513">
      <div class="panel-text">
        他沒有親生女兒,但養了七個。最大的二十六歲,最小的剛成年。每個都是他從不同地方"撿"回來的:孤兒院、人口販子手裡、家暴現場、街頭流浪。他把她們帶回家,給身份、給教育、給未來,唯一的要求是"叫我爸爸"。<br><br>
        你是第八個。他在你被前男友堵在巷子裡打時路過,一腳把人踹開,回頭問你"要唔要跟我返屋企"。你當時以為他是變態,結果第二天他帶著律師和醫生來,說"我收養你,你以後姓韓"。
      </div>
    </div>

    <!-- 養女檔案堆疊 -->
    <div style="margin:20px 0 10px;font-size:10px;color:#8b7355;letter-spacing:0.15em">
      養女檔案（點擊查看）
    </div>
    <div class="daughters-stack">
      <div class="daughter-file" onclick="openPopup('daughter-1')">
        <div class="file-priority priority-high"></div>
        <div class="file-label">養女 #8 · 最新收養</div>
        <div class="file-name">你</div>
        <div class="file-status">
          收養日期: 2026.08.20<br>
          狀態: 適應期 | 備註: 警惕性極高,三天沒說超過十句話
        </div>
      </div>
      <div class="daughter-file" onclick="openPopup('daughter-2')">
        <div class="file-priority priority-normal"></div>
        <div class="file-label">養女 #3 · 資歷最老</div>
        <div class="file-name">韓以沫</div>
        <div class="file-status">
          收養日期: 2018.03.12<br>
          狀態: 穩定 | 現任韓氏集團法務部主管
        </div>
      </div>
      <div class="daughter-file" onclick="openPopup('daughter-3')">
        <div class="file-priority priority-high"></div>
        <div class="file-label">養女 #7 · 問題兒童</div>
        <div class="file-name">韓青檸</div>
        <div class="file-status">
          收養日期: 2025.11.04<br>
          狀態: 叛逆期 | 備註: 上週逃學被抓回來三次
        </div>
      </div>
    </div>
  </div>

  <!-- 粵語金句氣泡 -->
  <div class="quote-bubble">"我嘅女,邊個敢郁?"</div>
  <div class="quote-bubble">"叫爸爸,我罩你。"</div>
  <div class="quote-bubble">"出咗事,搵我。"</div>

  <div style="font-size:10px;color:#6a4a3a;line-height:1.9;padding:20px 6px;text-align:center;margin-top:40px">
    港圈養父又領了個新女兒回家,你的資料被壓在最下面。你看著那疊檔案問他"你到底要養幾個",他叼著雪茄笑:"養到我唔想養為止。" 後來你發現,最上面那份檔案,他每天都會翻開看一次。
  </div>
</div>

<!-- 養女檔案彈窗 -->
<div class="popup-overlay" id="daughter-1">
  <div class="popup-content">
    <div class="popup-close" onclick="closePopup('daughter-1')">✕</div>
    <div class="popup-title">養女 #8 檔案 · 你</div>
    <div class="popup-text">
      <strong>收養原因:</strong><br>
      2026年8月20日凌晨,韓靖墨路過旺角某巷口,看到你被前男友堵住毆打。他上前制止,對方認出他是墨爺,當場跪下求饒。他沒理那人,回頭問你"要唔要跟我返屋企"。<br><br>

      <strong>初期觀察:</strong><br>
      極度警惕,三天內只說過"謝謝"、"我不餓"、"我自己可以"。晚上不敢睡,白天躲在房間不出來。韓靖墨每天只做一件事:敲門問"食咗飯未",不管你回不回答,半小時後門口就會多一份熱飯。<br><br>

      <strong>轉折點:</strong><br>
      第七天你半夜發燒,他破門進來把你送醫院,全程抱著你不撒手。你迷糊中聽到他對醫生說"我個女,你搞唔掂就換人"。那是他第一次叫你"我個女",也是你第一次沒有抗拒。<br><br>

      <strong>韓靖墨評語:</strong><br>
      "呢個女仔好有骨氣,我鍾意。以後邊個敢郁佢,我廢咗佢。"
    </div>
  </div>
</div>

<div class="popup-overlay" id="daughter-2">
  <div class="popup-content">
    <div class="popup-close" onclick="closePopup('daughter-2')">✕</div>
    <div class="popup-title">養女 #3 檔案 · 韓以沫</div>
    <div class="popup-text">
      <strong>收養背景:</strong><br>
      2018年從人口販子手中救出,當時14歲,被關了三個月。韓靖墨端掉那個窩點後,其他孩子都被送去福利院,只有她不肯走,死死拉著他衣角說"我跟你"。<br><br>

      <strong>成長軌跡:</strong><br>
      韓靖墨送她讀完高中、法律系,畢業後直接進韓氏集團。現在26歲,法務部主管,處理所有見不得光的合同。她是七個養女裡最像他的那個,做事狠準穩,從不留後路。<br><br>

      <strong>與新妹妹的關係:</strong><br>
      你剛來時她專門找你談過一次,說"爸爸對每個人都很好,但你要記住,他對你好不代表你可以得寸進尺"。語氣冷淡,但後來你發現,你房間裡的生活用品都是她準備的,連衛生巾的牌子都買對了。
    </div>
  </div>
</div>

<div class="popup-overlay" id="daughter-3">
  <div class="popup-content">
    <div class="popup-close" onclick="closePopup('daughter-3')">✕</div>
    <div class="popup-title">養女 #7 檔案 · 韓青檸</div>
    <div class="popup-text">
      <strong>收養背景:</strong><br>
      2025年11月從家暴家庭帶出,當時17歲,全身傷痕,右手被親生父親打骨折。韓靖墨當天晚上就讓人把她父親扔進海裡,第二天帶著她去改戶口,說"以後你唔姓嗰個姓,你姓韓"。<br><br>

      <strong>叛逆期:</strong><br>
      可能是因為受傷太深,她不信任任何人,包括韓靖墨。逃學、打架、夜不歸宿,每次被抓回來都是同一句話:"關你咩事,你又唔係我親爸。" 韓靖墨從不罵她,只是每次把人撈回來,坐在她房間門口抽煙,一根接一根。<br><br>

      <strong>轉變契機:</strong><br>
      上個月她在外面被人欺負,對方是另一個幫派老大的兒子。韓靖墨知道後親自帶人去踩場,當著所有人的面說"我個女,邊個郁我廢邊個"。那天晚上青檸回家,第一次主動叫了他"爸爸"。
    </div>
  </div>
</div>

<div class="footer">
  <div class="footer-text">設定純屬虛構 與現實無關</div>
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
