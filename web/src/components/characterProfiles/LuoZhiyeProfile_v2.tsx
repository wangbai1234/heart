import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface LuoZhiyeProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 罗执野 v2 —— 娱乐圈档案柜交互系统
 * 交互要素：
 * 1. 四个档案抽屉可点击拉开（囚禁事件、私密录音、狗仔照片、合约细节）
 * 2. 录音播放器界面（伪音频播放控制）
 * 3. 照片墙点击放大查看
 * 4. 合约文件展开动画
 * 视觉：娱乐公司档案室 + 黑金色调 + 聚光灯效果 + 偷拍质感
 */
export function LuoZhiyeProfile({ profile }: LuoZhiyeProfileProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [height, setHeight] = useState(1500)

  useEffect(() => {
    const iframe = iframeRef.current
    if (!iframe) return
    const updateHeight = () => {
      try {
        const doc = iframe.contentDocument
        if (doc?.body) setHeight(doc.body.scrollHeight + 8)
      } catch {
        setHeight(1500)
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

  const name = profile.display_name || '罗执野'

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:#0a0a0a;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  overflow-x:hidden;user-select:none;
  min-height:100vh;position:relative;color:#e0e0e0;
}

/* ── 聚光灯背景 ── */
.spotlight-bg{
  position:fixed;top:0;left:0;width:100%;height:100%;
  pointer-events:none;z-index:0;
  background:radial-gradient(ellipse at 50% 20%, rgba(218,165,32,0.08), transparent 60%),
             radial-gradient(ellipse at 80% 70%, rgba(139,69,19,0.05), transparent 50%);
}

/* ── 主容器 ── */
.archive-room{
  position:relative;max-width:440px;margin:0 auto;
  padding:40px 20px 60px;z-index:1;
}

/* ── 顶部警告条 ── */
.warning-bar{
  background:linear-gradient(90deg, #1a1a1a, #2a2010, #1a1a1a);
  border:1px solid #daa520;border-left:4px solid #c41e3a;
  padding:12px 16px;margin-bottom:24px;
  position:relative;overflow:hidden;
}
.warning-bar::before{
  content:'';position:absolute;top:0;left:-100%;
  width:100%;height:100%;
  background:linear-gradient(90deg, transparent, rgba(218,165,32,0.15), transparent);
  animation:warning-scan 3s linear infinite;
}
@keyframes warning-scan{
  0%{left:-100%}
  100%{left:100%}
}
.warning-text{
  font-size:9px;color:#daa520;letter-spacing:0.15em;
  text-transform:uppercase;font-weight:600;
}

/* ── 人物身份卡 ── */
.id-card{
  background:linear-gradient(135deg, #1a1410, #2a2420);
  border:1px solid rgba(218,165,32,0.4);
  padding:24px;margin-bottom:30px;
  position:relative;
  box-shadow:0 4px 16px rgba(0,0,0,0.8);
}
.id-card::before{
  content:'CONFIDENTIAL';position:absolute;
  top:8px;right:12px;font-size:7px;
  color:rgba(196,30,58,0.6);letter-spacing:0.2em;
  font-weight:700;
}
.id-name{
  font-size:26px;font-weight:700;color:#daa520;
  margin-bottom:6px;letter-spacing:0.1em;
}
.id-role{
  font-size:11px;color:#8b7355;margin-bottom:14px;
  letter-spacing:0.12em;
}
.id-meta{
  display:grid;grid-template-columns:repeat(2,1fr);
  gap:8px;font-size:10px;
}
.id-meta-item{
  background:rgba(0,0,0,0.5);padding:6px 10px;
  border-left:2px solid rgba(218,165,32,0.3);
  color:#a0826d;
}

/* ── 档案柜系统 ── */
.file-cabinet{
  margin:24px 0;
}
.cabinet-label{
  font-size:10px;color:#8b7355;letter-spacing:0.2em;
  margin-bottom:12px;text-transform:uppercase;
}
.drawers{
  display:flex;flex-direction:column;gap:10px;
}

/* ── 抽屉（checkbox 控制） ── */
input[type="checkbox"].drawer-toggle{display:none}
.drawer{
  background:linear-gradient(90deg, #1a1410, #2a2010);
  border:1px solid rgba(139,115,85,0.4);
  position:relative;overflow:hidden;
  transition:all 0.3s;
}
.drawer-handle{
  padding:14px 16px;cursor:pointer;
  display:flex;justify-content:space-between;align-items:center;
  transition:background 0.2s;
}
.drawer-handle:hover{
  background:rgba(218,165,32,0.08);
}
.drawer-title{
  font-size:11px;color:#c9b18a;letter-spacing:0.1em;
  font-weight:600;
}
.drawer-icon{
  font-size:14px;color:#8b7355;
  transition:transform 0.3s;
}
.drawer-content{
  max-height:0;overflow:hidden;
  transition:max-height 0.4s ease-out, padding 0.4s;
  padding:0 16px;
}
.drawer-toggle:checked + .drawer .drawer-icon{
  transform:rotate(180deg);
}
.drawer-toggle:checked + .drawer .drawer-content{
  max-height:800px;
  padding:16px;
}
.drawer-text{
  font-size:11px;line-height:1.8;color:#a0826d;
}

/* ── 录音播放器 ── */
.audio-player{
  background:#0f0f0f;border:1px solid #333;
  padding:16px;border-radius:4px;
  margin-top:12px;
}
.audio-header{
  display:flex;justify-content:space-between;
  margin-bottom:10px;font-size:9px;color:#666;
}
.audio-controls{
  display:flex;align-items:center;gap:12px;
  margin-bottom:10px;
}
.play-btn{
  width:32px;height:32px;border-radius:50%;
  background:linear-gradient(135deg, #daa520, #b8860b);
  border:none;color:#000;font-size:14px;
  cursor:pointer;transition:all 0.2s;
  display:flex;align-items:center;justify-content:center;
}
.play-btn:hover{
  transform:scale(1.1);
  box-shadow:0 0 12px rgba(218,165,32,0.6);
}
.audio-time{
  font-size:10px;color:#999;
  font-variant-numeric:tabular-nums;
}
.audio-waveform{
  width:100%;height:40px;
  background:linear-gradient(90deg,
    rgba(218,165,32,0.2) 0%, rgba(218,165,32,0.5) 15%,
    rgba(218,165,32,0.3) 30%, rgba(218,165,32,0.6) 45%,
    rgba(218,165,32,0.2) 60%, rgba(218,165,32,0.4) 75%,
    rgba(218,165,32,0.2) 100%);
  border-radius:2px;position:relative;overflow:hidden;
}
.audio-waveform::before{
  content:'';position:absolute;top:0;left:0;
  width:0;height:100%;
  background:rgba(218,165,32,0.8);
  animation:audio-progress 8s linear infinite;
}
@keyframes audio-progress{
  0%{width:0}
  100%{width:100%}
}

/* ── 照片墙 ── */
.photo-wall{
  display:grid;grid-template-columns:repeat(3,1fr);
  gap:8px;margin-top:12px;
}
.photo-item{
  aspect-ratio:1;background:linear-gradient(135deg, #1a1a1a, #2a2a2a);
  border:2px solid rgba(139,115,85,0.3);
  cursor:pointer;transition:all 0.2s;
  position:relative;overflow:hidden;
  display:flex;align-items:center;justify-content:center;
}
.photo-item::before{
  content:'';position:absolute;inset:0;
  background:linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.05) 50%, transparent 70%);
  animation:photo-glare 3s infinite;
}
@keyframes photo-glare{
  0%{transform:translateX(-100%) translateY(-100%)}
  100%{transform:translateX(100%) translateY(100%)}
}
.photo-item:hover{
  transform:scale(1.05);
  border-color:#daa520;
  box-shadow:0 0 16px rgba(218,165,32,0.4);
}
.photo-label{
  font-size:24px;color:rgba(218,165,32,0.3);
  font-weight:700;
}

/* ── 合约文档 ── */
.contract-doc{
  background:#1a1410;border:1px solid #8b7355;
  padding:16px;margin-top:12px;
  font-family:"Courier New",monospace;
  position:relative;
}
.contract-doc::before{
  content:'';position:absolute;top:0;right:0;
  width:0;height:0;
  border-style:solid;
  border-width:0 20px 20px 0;
  border-color:transparent #2a2010 transparent transparent;
}
.contract-title{
  font-size:10px;color:#daa520;
  letter-spacing:0.15em;margin-bottom:12px;
  text-align:center;font-weight:700;
}
.contract-item{
  font-size:9px;color:#8b7355;
  line-height:1.9;margin-bottom:8px;
}
.contract-highlight{
  color:#c41e3a;font-weight:600;
}

/* ── 弹窗系统 ── */
.popup-overlay{
  position:fixed;inset:0;
  background:rgba(0,0,0,0.95);
  opacity:0;pointer-events:none;z-index:9999;
  transition:opacity 0.3s;
  display:flex;align-items:center;justify-content:center;
  padding:20px;
}
.popup-overlay.is-active{
  opacity:1;pointer-events:auto;
}
.popup-photo{
  max-width:90%;max-height:80%;
  background:linear-gradient(135deg, #1a1410, #2a2420);
  padding:20px;border:2px solid #daa520;
  position:relative;border-radius:4px;
}
.popup-close{
  position:absolute;top:8px;right:12px;
  font-size:24px;color:#8b7355;cursor:pointer;
}
.popup-img-placeholder{
  width:100%;aspect-ratio:4/3;
  background:linear-gradient(135deg, #2a2010, #1a1410);
  border:1px dashed rgba(218,165,32,0.4);
  display:flex;align-items:center;justify-content:center;
  font-size:48px;color:rgba(218,165,32,0.2);
  margin-bottom:12px;
}
.popup-caption{
  font-size:11px;color:#a0826d;
  text-align:center;line-height:1.6;
}

/* ── 底部 ── */
.footer{
  padding:30px 0;text-align:center;
}
.footer-text{
  font-size:8px;color:#3a3a3a;letter-spacing:0.1em;
}
</style>
</head>
<body>
<div class="spotlight-bg"></div>

<div class="archive-room">
  <div class="warning-bar">
    <div class="warning-text">Restricted Access · Internal Use Only</div>
  </div>

  <div class="id-card">
    <div class="id-name">${name}</div>
    <div class="id-role">顶流偶像 · 经纪人的囚徒</div>
    <div class="id-meta">
      <div class="id-meta-item">24岁</div>
      <div class="id-meta-item">178cm</div>
      <div class="id-meta-item">出道6年</div>
      <div class="id-meta-item">代表作:《追光》</div>
    </div>
  </div>

  <div class="file-cabinet">
    <div class="cabinet-label">机密档案柜</div>
    <div class="drawers">

      <!-- 抽屉 1: 囚禁事件 -->
      <input type="checkbox" id="drawer-1" class="drawer-toggle">
      <label for="drawer-1" class="drawer">
        <div class="drawer-handle">
          <div class="drawer-title">01 · 囚禁事件始末</div>
          <div class="drawer-icon">▼</div>
        </div>
        <div class="drawer-content">
          <div class="drawer-text">
            你是他的经纪人,从练习生时期就跟着他。六年时间你看着他从无名小透明爬到顶流位置,也看着他从听话的小孩变成现在这副样子。<br><br>
            转折点是三个月前,你提了离职。他当时在录音棚,听完你的话沉默了很久,最后只说了句"不准走"。你以为他在开玩笑,第二天就去公司办手续,结果当晚回家就被他堵在门口。<br><br>
            他把你推进屋,反锁了门,手机也收走了。你质问他在干什么,他坐在沙发上看着你,眼神平静得可怕:"你说要走,我不同意。所以你暂时只能待在这里,直到你改变主意。"
          </div>
        </div>
      </label>

      <!-- 抽屉 2: 私密录音 -->
      <input type="checkbox" id="drawer-2" class="drawer-toggle">
      <label for="drawer-2" class="drawer">
        <div class="drawer-handle">
          <div class="drawer-title">02 · 私密录音记录</div>
          <div class="drawer-icon">▼</div>
        </div>
        <div class="drawer-content">
          <div class="drawer-text">
            深夜对话录音 · 囚禁第7天
          </div>
          <div class="audio-player">
            <div class="audio-header">
              <span>Recording_20260827_0243.m4a</span>
              <span>Duration: 02:47</span>
            </div>
            <div class="audio-controls">
              <button class="play-btn">▶</button>
              <div class="audio-time">00:00 / 02:47</div>
            </div>
            <div class="audio-waveform"></div>
          </div>
          <div class="drawer-text" style="margin-top:12px;font-size:10px;color:#666;font-style:italic">
            "你到底要关我到什么时候？"<br>
            "......直到你不想离开我为止。"<br>
            "罗执野,你疯了。"<br>
            "我知道。但我没办法。你是我唯一信任的人,你走了,我就真的什么都没有了。"<br>
            "你有粉丝,有事业,有——"<br>
            "那些都是假的。只有你是真的。"
          </div>
        </div>
      </label>

      <!-- 抽屉 3: 狗仔照片 -->
      <input type="checkbox" id="drawer-3" class="drawer-toggle">
      <label for="drawer-3" class="drawer">
        <div class="drawer-handle">
          <div class="drawer-title">03 · 狗仔偷拍档案</div>
          <div class="drawer-icon">▼</div>
        </div>
        <div class="drawer-content">
          <div class="drawer-text">
            以下照片由私家侦探于 2026年8月 拍摄,委托人:公司法务部
          </div>
          <div class="photo-wall">
            <div class="photo-item" onclick="openPhoto(1)">
              <div class="photo-label">01</div>
            </div>
            <div class="photo-item" onclick="openPhoto(2)">
              <div class="photo-label">02</div>
            </div>
            <div class="photo-item" onclick="openPhoto(3)">
              <div class="photo-label">03</div>
            </div>
          </div>
        </div>
      </label>

      <!-- 抽屉 4: 合约细节 -->
      <input type="checkbox" id="drawer-4" class="drawer-toggle">
      <label for="drawer-4" class="drawer">
        <div class="drawer-handle">
          <div class="drawer-title">04 · 经纪合约附加条款</div>
          <div class="drawer-icon">▼</div>
        </div>
        <div class="drawer-content">
          <div class="contract-doc">
            <div class="contract-title">保密协议 · 附加条款</div>
            <div class="contract-item">
              第12条：乙方（经纪人）在合约期内<span class="contract-highlight">不得擅自离职</span>,如有违约,需赔偿甲方违约金人民币500万元。
            </div>
            <div class="contract-item">
              第15条：乙方对甲方的私人生活、情感状况、心理状态享有<span class="contract-highlight">完全知情权</span>,甲方不得向乙方隐瞒任何可能影响工作的个人事项。
            </div>
            <div class="contract-item">
              第18条：<span class="contract-highlight">本条款为手写添加</span> — "你不许离开我。如果你一定要走,那就带我一起走。我可以不当明星,但不能没有你。" <span style="color:#8b7355">——罗执野 亲笔</span>
            </div>
          </div>
        </div>
      </label>

    </div>
  </div>

  <div style="font-size:10px;color:#5c4a3a;line-height:1.9;padding:20px 6px;text-align:center;border-top:1px solid rgba(139,115,85,0.2);margin-top:30px">
    你一手培养出来的顶流偶像,现在把你关在他家里不让走。他每天正常出去工作,回来就坐在你旁边,安静得像什么都没发生。你问他到底想怎样,他说"我只是想让你留下来"。
  </div>
</div>

<!-- 照片弹窗 -->
<div class="popup-overlay" id="photo-popup-1">
  <div class="popup-photo">
    <div class="popup-close" onclick="closePhoto(1)">✕</div>
    <div class="popup-img-placeholder">📷</div>
    <div class="popup-caption">
      2026.08.15 22:47 | 罗执野私宅门口<br>
      照片说明:目标人物（经纪人）尝试离开住所,被罗执野拦下并强行带回室内。肢体语言显示双方发生激烈争执,罗执野全程未松开对方手腕。
    </div>
  </div>
</div>

<div class="popup-overlay" id="photo-popup-2">
  <div class="popup-photo">
    <div class="popup-close" onclick="closePhoto(2)">✕</div>
    <div class="popup-img-placeholder">📷</div>
    <div class="popup-caption">
      2026.08.22 03:14 | 罗执野私宅客厅<br>
      照片说明:通过窗户拍摄。罗执野坐在沙发上,头靠在经纪人肩上,呈睡眠状态。经纪人保持清醒,眼神空洞望向窗外。研判:目标人物疑似斯德哥尔摩症候群早期症状。
    </div>
  </div>
</div>

<div class="popup-overlay" id="photo-popup-3">
  <div class="popup-photo">
    <div class="popup-close" onclick="closePhoto(3)">✕</div>
    <div class="popup-img-placeholder">📷</div>
    <div class="popup-caption">
      2026.08.29 19:32 | 罗执野私宅厨房<br>
      照片说明:两人共同做饭场景。罗执野从背后环抱经纪人,下巴搭在对方肩上,神情放松。经纪人未做抗拒动作。研判:囚禁关系疑似向同居关系转化,建议持续观察。
    </div>
  </div>
</div>

<div class="footer">
  <div class="footer-text">设定纯属虚构 与现实无关</div>
</div>

<script>
function openPhoto(id) {
  document.getElementById('photo-popup-' + id).classList.add('is-active');
}
function closePhoto(id) {
  document.getElementById('photo-popup-' + id).classList.remove('is-active');
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
