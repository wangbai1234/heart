import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface XuYanzhiProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 许砚之 v2 —— 课堂笔记本交互系统
 * 交互要素：
 * 1. 三本笔记本可点击翻开（数学笔记、涂鸦本、日记本）
 * 2. 黑板擦拭动画效果
 * 3. 座位卡点击查看详细档案
 * 4. 课桌抽屉拉开系统
 * 视觉：教室场景 + 方格纸 + 铅笔手写体 + 米色书页 + 木纹课桌
 */
export function XuYanzhiProfile({ profile }: XuYanzhiProfileProps) {
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

  const name = profile.display_name || '许砚之'

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#f5f3ed;
  font-family:"Noto Sans SC","PingFang SC",sans-serif;
  overflow-x:hidden;user-select:none;
  min-height:100vh;position:relative;color:#3e3a36;
}

/* ── 方格纸背景 ── */
.grid-paper{
  position:fixed;top:0;left:0;width:100%;height:100%;
  pointer-events:none;z-index:0;opacity:0.15;
  background-image:
    linear-gradient(0deg, transparent 24%, rgba(0,0,0,0.05) 25%, rgba(0,0,0,0.05) 26%, transparent 27%, transparent 74%, rgba(0,0,0,0.05) 75%, rgba(0,0,0,0.05) 76%, transparent 77%, transparent),
    linear-gradient(90deg, transparent 24%, rgba(0,0,0,0.05) 25%, rgba(0,0,0,0.05) 26%, transparent 27%, transparent 74%, rgba(0,0,0,0.05) 75%, rgba(0,0,0,0.05) 76%, transparent 77%, transparent);
  background-size:20px 20px;
}

/* ── 主容器 ── */
.classroom-desk{
  position:relative;max-width:440px;margin:0 auto;
  padding:40px 20px 80px;z-index:1;
}

/* ── 黑板标题区 ── */
.blackboard{
  background:#2d3436;
  border:8px solid #8b7355;
  padding:20px;margin-bottom:24px;
  position:relative;
  box-shadow:0 4px 12px rgba(0,0,0,0.3);
}
.blackboard::before{
  content:'';position:absolute;top:6px;right:6px;
  width:40px;height:40px;
  background:radial-gradient(circle, rgba(255,255,255,0.3) 0%, transparent 70%);
  border-radius:50%;opacity:0.2;
  animation:chalk-dust 4s ease-in-out infinite;
}
@keyframes chalk-dust{
  0%, 100%{opacity:0.1;transform:scale(1)}
  50%{opacity:0.3;transform:scale(1.2)}
}
.board-title{
  font-size:20px;color:#f0f0f0;
  text-align:center;letter-spacing:0.15em;
  font-family:"KaiTi","楷体",serif;
  text-shadow:1px 1px 2px rgba(0,0,0,0.5);
}
.board-date{
  font-size:10px;color:rgba(240,240,240,0.6);
  text-align:right;margin-top:8px;
  font-family:"Courier New",monospace;
}

/* ── 座位卡 ── */
.seat-card{
  background:#fff;
  border:1px solid rgba(139,115,85,0.3);
  padding:20px;margin-bottom:24px;
  position:relative;cursor:pointer;
  transition:all 0.3s;
  box-shadow:0 2px 8px rgba(0,0,0,0.08);
}
.seat-card:hover{
  transform:translateY(-4px) rotate(-0.5deg);
  box-shadow:0 6px 16px rgba(139,115,85,0.25);
}
.seat-card::before{
  content:'座位 A-12';position:absolute;
  top:8px;right:12px;font-size:8px;
  color:rgba(139,115,85,0.5);
  letter-spacing:0.15em;
}
.seat-name{
  font-size:24px;font-weight:700;color:#3e3a36;
  margin-bottom:6px;letter-spacing:0.1em;
}
.seat-label{
  font-size:10px;color:#8b7355;
  margin-bottom:14px;letter-spacing:0.15em;
}
.seat-meta{
  display:grid;grid-template-columns:repeat(2,1fr);
  gap:8px;font-size:10px;
}
.seat-meta-item{
  background:rgba(245,243,237,0.8);
  padding:6px 10px;border:1px solid rgba(139,115,85,0.2);
  color:#6a5f57;border-radius:3px;
}

/* ── 笔记本堆叠系统 ── */
.notebooks-stack{
  margin:24px 0;
  display:flex;gap:12px;flex-wrap:wrap;
  justify-content:center;
}
.notebook{
  width:110px;
  background:linear-gradient(135deg, #faf8f3, #f0ebe0);
  border:1px solid #d4cfc3;
  padding:12px 10px;
  cursor:pointer;transition:all 0.3s;
  position:relative;
  box-shadow:0 2px 6px rgba(0,0,0,0.12);
}
.notebook:hover{
  transform:translateY(-6px) scale(1.05);
  box-shadow:0 6px 16px rgba(139,115,85,0.3);
}
.notebook-cover{
  font-size:11px;color:#5c5248;
  margin-bottom:8px;letter-spacing:0.12em;
  font-weight:600;text-align:center;
  border-bottom:1px dashed rgba(139,115,85,0.3);
  padding-bottom:6px;
}
.notebook-icon{
  font-size:28px;text-align:center;
  margin:12px 0;
}
.notebook-desc{
  font-size:8px;color:#9a8f85;
  text-align:center;line-height:1.5;
}

/* ── 抽屉系统 ── */
#drawer-math{display:none}
#drawer-doodle{display:none}
#drawer-diary{display:none}
.drawer-content{
  display:none;
  background:#fff;border:2px solid #d4cfc3;
  padding:20px;margin:16px 0;
  border-radius:4px;
  box-shadow:inset 0 2px 4px rgba(0,0,0,0.05);
}
#drawer-math:checked ~ .classroom-desk .content-math{display:block}
#drawer-doodle:checked ~ .classroom-desk .content-doodle{display:block}
#drawer-diary:checked ~ .classroom-desk .content-diary{display:block}

.drawer-title{
  font-size:14px;color:#3e3a36;
  margin-bottom:12px;letter-spacing:0.1em;
  font-weight:700;
  border-bottom:2px solid #d4cfc3;
  padding-bottom:8px;
}
.drawer-text{
  font-size:11px;line-height:1.9;color:#5c5248;
  font-family:"KaiTi","楷体",serif;
}
.handwriting{
  font-family:"KaiTi","楷体",serif;
  color:#4a4038;line-height:1.8;
}

/* ── 涂鸦区 ── */
.doodle-grid{
  display:grid;grid-template-columns:repeat(2,1fr);
  gap:10px;margin-top:12px;
}
.doodle-box{
  aspect-ratio:1;
  background:linear-gradient(135deg, #faf8f3, #f5f3ed);
  border:1px dashed #c9c0b3;
  display:flex;align-items:center;justify-content:center;
  font-size:32px;color:rgba(139,115,85,0.3);
  position:relative;
}
.doodle-label{
  position:absolute;bottom:4px;right:6px;
  font-size:8px;color:#9a8f85;
}

/* ── 弹窗 ── */
.popup-overlay{
  position:fixed;inset:0;
  background:rgba(0,0,0,0.88);
  opacity:0;pointer-events:none;z-index:9999;
  transition:opacity 0.3s;
  display:flex;align-items:center;justify-content:center;
  padding:20px;
}
.popup-overlay.is-active{
  opacity:1;pointer-events:auto;
}
.popup-content{
  background:#faf8f3;
  max-width:90%;max-height:85%;
  padding:24px;border:2px solid #8b7355;
  border-radius:4px;overflow-y:auto;
  position:relative;
  box-shadow:0 0 40px rgba(0,0,0,0.5);
}
.popup-close{
  position:absolute;top:12px;right:16px;
  font-size:24px;color:#8b7355;cursor:pointer;
}
.popup-title{
  font-size:16px;font-weight:700;color:#3e3a36;
  margin-bottom:16px;letter-spacing:0.15em;
  border-bottom:2px solid #d4cfc3;
  padding-bottom:10px;
}
.popup-text{
  font-size:11px;line-height:1.9;color:#5c5248;
}

/* ── 底部 ── */
.footer{
  padding:30px 0;text-align:center;
}
.footer-text{
  font-size:8px;color:#b0a89d;letter-spacing:0.1em;
}
</style>
</head>
<body>
<div class="grid-paper"></div>

<input type="checkbox" id="drawer-math">
<input type="checkbox" id="drawer-doodle">
<input type="checkbox" id="drawer-diary">

<div class="classroom-desk">
  <div class="blackboard">
    <div class="board-title">许砚之的课桌</div>
    <div class="board-date">2026.09.03</div>
  </div>

  <div class="seat-card" onclick="openPopup('seat-detail')">
    <div class="seat-name">${name}</div>
    <div class="seat-label">高三 · 理科班第一排 · 闷骚学霸</div>
    <div class="seat-meta">
      <div class="seat-meta-item">18岁</div>
      <div class="seat-meta-item">182cm</div>
      <div class="seat-meta-item">数学竞赛金牌</div>
      <div class="seat-meta-item">隐藏暗恋对象</div>
    </div>
  </div>

  <div style="font-size:10px;color:#8b7355;text-align:center;margin-bottom:12px;letter-spacing:0.15em">
    点击笔记本翻阅
  </div>

  <div class="notebooks-stack">
    <label for="drawer-math" class="notebook">
      <div class="notebook-cover">数学笔记</div>
      <div class="notebook-icon" style="font-size:11px;color:#8b7355;font-weight:600">数学</div>
      <div class="notebook-desc">工整到像印刷体</div>
    </label>

    <label for="drawer-doodle" class="notebook">
      <div class="notebook-cover">涂鸦本</div>
      <div class="notebook-icon" style="font-size:11px;color:#8b7355;font-weight:600">涂鸦</div>
      <div class="notebook-desc">全是你的侧脸</div>
    </label>

    <label for="drawer-diary" class="notebook">
      <div class="notebook-cover">日记本</div>
      <div class="notebook-icon" style="font-size:11px;color:#8b7355;font-weight:600">日记</div>
      <div class="notebook-desc">上锁的秘密</div>
    </label>
  </div>

  <!-- 数学笔记内容 -->
  <div class="drawer-content content-math">
    <div class="drawer-title">数学笔记 · 2026年3月12日</div>
    <div class="drawer-text handwriting">
      例题7: 已知函数 f(x) = x² - 2x + 3, 求...<br><br>
      [完整解题步骤,每一行都工整到像打印出来的]<br><br>
      ——<br>
      笔记空白处用铅笔写了一句:<br>
      "今天她问我这道题,我给她讲了三遍。第三遍时她终于懂了,笑着说'你好耐心'。其实我巴不得她永远不懂,这样就能一直给她讲。"<br><br>
      [铅笔字迹很浅,像是写完就后悔了,但又舍不得擦掉]
    </div>
  </div>

  <!-- 涂鸦本内容 -->
  <div class="drawer-content content-doodle">
    <div class="drawer-title">涂鸦本 · 无日期</div>
    <div class="drawer-text">
      笔记本里没有一张正脸,全是侧脸和背影。<br><br>
      她趴在课桌上睡觉的样子、她抬手回答问题的样子、她托腮看窗外的样子、她笑的时候眼睛弯成月牙的样子。<br><br>
      每一页右下角都有日期,最早的是高一开学第一天。
    </div>
    <div class="doodle-grid">
      <div class="doodle-box">
        <div style="font-size:14px;color:#8b7355">侧脸</div>
        <div class="doodle-label">Day 1</div>
      </div>
      <div class="doodle-box">
        <div style="font-size:14px;color:#8b7355">背影</div>
        <div class="doodle-label">Day 47</div>
      </div>
      <div class="doodle-box">
        <div style="font-size:14px;color:#8b7355">笑容</div>
        <div class="doodle-label">Day 128</div>
      </div>
      <div class="doodle-box">
        <div style="font-size:14px;color:#8b7355">睡颜</div>
        <div class="doodle-label">Day 365</div>
      </div>
    </div>
  </div>

  <!-- 日记本内容 -->
  <div class="drawer-content content-diary">
    <div class="drawer-title">日记本 · 上锁的部分</div>
    <div class="drawer-text handwriting">
      2025.09.01 晴<br>
      高一开学第一天,她坐我前排。自我介绍时她说她喜欢数学,我当时就想,那我一定要考全校第一。<br><br>

      2025.11.23 阴<br>
      今天她数学考了92分,哭着问我为什么自己总学不会。我想说"因为你每次听讲都在开小差",但最后还是说"没关系,我教你"。<br><br>

      2026.02.14 雪<br>
      情人节,她收到三封情书。我看着她把情书塞进书包,心里难受得要命,但还是面无表情地做着卷子。<br><br>

      2026.06.07 晴<br>
      高考结束了。她问我报哪个学校,我说"看你报哪"。她笑着说"那我们做校友吧"。我点头,没说我早就偷偷查过她想去的学校,提前把志愿填好了。<br><br>

      ——<br>
      最后一页写着:<br>
      "我喜欢你三年了。从高一第一天到现在,每一天都喜欢。但我不敢说,因为怕说了之后,连现在这样坐你后面、给你讲题、看你笑的机会都没有了。"
    </div>
  </div>

  <div style="font-size:10px;color:#9a8f85;line-height:1.9;padding:20px 6px;text-align:center;margin-top:30px;background:rgba(255,255,255,0.5);border-radius:4px">
    高三最后一节晚自习,你回头问他借橡皮,他递给你的时候手指碰到你掌心。你没注意,他耳根红了整整十分钟。
  </div>
</div>

<!-- 座位详情弹窗 -->
<div class="popup-overlay" id="seat-detail">
  <div class="popup-content">
    <div class="popup-close" onclick="closePopup('seat-detail')">✕</div>
    <div class="popup-title">座位档案 · A-12 许砚之</div>
    <div class="popup-text">
      <strong>基本信息:</strong><br>
      高三理科班,常年年级第一,数学竞赛省一等奖。坐第一排靠窗位置,你坐他前面。<br><br>

      <strong>外表:</strong><br>
      戴黑框眼镜,校服永远一尘不染,书包里的笔按颜色排列整齐。看起来很乖,但你不知道他每天晚上会盯着你的背影发呆到下课。<br><br>

      <strong>性格:</strong><br>
      闷。话少,除了讲题几乎不主动跟人说话。但对你不一样,你问他问题他能讲一节课,讲到下课铃响还没讲完。<br><br>

      <strong>暗恋方式:</strong><br>
      不会说"我喜欢你",只会:<br>
      - 每天早到十分钟,在你座位上放一瓶热牛奶<br>
      - 你忘带笔,他书包里永远有备用的<br>
      - 你说冷,第二天教室空调温度就调高了(是他偷偷跟老师申请的)<br>
      - 你上课睡着,他会用书挡住老师视线<br><br>

      <strong>被发现的瞬间:</strong><br>
      高考结束那天,全班在教室拍照留念。你翻他桌洞找笔,看到一个笔记本,封面写着"不要打开"。你打开了,里面全是你的侧脸。<br><br>

      你回头看他,他站在教室门口,耳根通红,眼神躲闪,半天才哑着声音说:"对不起......"<br><br>

      你走过去,把笔记本还给他,问:"画了多久?"<br>
      他低着头:"......三年。"<br>
      你说:"那现在可以画正脸了。"<br><br>

      他愣了两秒,然后红着脸笑了,那是你第一次看到他笑得那么明显。
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
