import { useEffect, useRef, useState } from 'react'
import type { CharacterProfileDTO } from '../../services/api'

interface QinJingzhouProfileProps {
  profile: CharacterProfileDTO
}

/**
 * 秦景舟 v2 —— 婚纱设计工作室交互系统
 * 交互要素：
 * 1. 三稿设计图点击弹出大图 + 设计笔记
 * 2. 草稿台灯开关控制氛围
 * 3. 底部抽屉拉出完整人物档案
 * 视觉：设计师工作台 + 手绘草图 + 白纱蕾丝纹理 + 冷白光
 */
export function QinJingzhouProfile({ profile }: QinJingzhouProfileProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [height, setHeight] = useState(1400)

  useEffect(() => {
    const iframe = iframeRef.current
    if (!iframe) return
    const updateHeight = () => {
      try {
        const doc = iframe.contentDocument
        if (doc?.body) setHeight(doc.body.scrollHeight + 8)
      } catch {
        setHeight(1400)
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

  const htmlContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  background:linear-gradient(180deg,#f8f9fb,#e8eaed);
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;
  overflow-x:hidden;user-select:none;
  min-height:100vh;position:relative;
}

/* ── 蕾丝纹理背景层 ── */
.lace-texture{
  position:fixed;top:0;left:0;width:100%;height:100%;
  pointer-events:none;z-index:0;opacity:0.04;
  background-image:
    radial-gradient(circle at 20% 30%, rgba(0,0,0,0.6) 1px, transparent 2px),
    radial-gradient(circle at 80% 70%, rgba(0,0,0,0.4) 1.5px, transparent 2.5px);
  background-size:40px 40px,60px 60px;
  animation:lace-drift 20s linear infinite;
}
@keyframes lace-drift{
  0%{background-position:0 0,30px 30px}
  100%{background-position:40px 40px,90px 90px}
}

/* ── 工作台容器 ── */
.studio-container{
  position:relative;max-width:440px;margin:0 auto;
  padding:30px 20px 80px;z-index:1;
}

/* ── 顶部工作台标题 ── */
.studio-header{
  text-align:center;margin-bottom:24px;
  border-bottom:1px solid rgba(0,0,0,0.08);padding-bottom:16px;
}
.studio-title{
  font-size:11px;letter-spacing:0.5em;color:#6c757d;
  font-weight:600;margin-bottom:4px;text-transform:uppercase;
}
.studio-subtitle{
  font-size:9px;color:#adb5bd;letter-spacing:0.2em;
}

/* ── 设计师名牌 ── */
.designer-card{
  background:#fff;border:1px solid rgba(0,0,0,0.06);
  padding:20px;margin-bottom:20px;position:relative;
  box-shadow:0 2px 8px rgba(0,0,0,0.04);
}
.designer-card::before{
  content:'';position:absolute;top:12px;right:12px;
  width:8px;height:8px;border-radius:50%;
  background:linear-gradient(135deg,#dee2e6,transparent);
}
.designer-name{
  font-size:24px;font-weight:700;color:#212529;
  margin-bottom:6px;letter-spacing:0.05em;
}
.designer-role{
  font-size:10px;color:#6c757d;margin-bottom:12px;
  letter-spacing:0.15em;
}
.designer-meta{
  display:flex;gap:10px;font-size:9px;color:#868e96;
  flex-wrap:wrap;
}
.designer-meta span{
  background:rgba(108,117,125,0.05);padding:3px 8px;
  border-radius:3px;border:1px solid rgba(108,117,125,0.1);
}

/* ── 三稿草图区（可点击） ── */
.drafts-zone{
  margin:24px 0;display:grid;grid-template-columns:repeat(3,1fr);
  gap:12px;
}
.draft-card{
  background:#fff;border:1px solid rgba(0,0,0,0.08);
  padding:10px;cursor:pointer;transition:all 0.2s;
  position:relative;
}
.draft-card:hover{
  transform:translateY(-3px);
  box-shadow:0 6px 16px rgba(0,0,0,0.12);
}
.draft-card::after{
  content:attr(data-label);position:absolute;bottom:4px;right:6px;
  font-size:8px;color:#adb5bd;letter-spacing:0.1em;
}
.draft-thumb{
  width:100%;aspect-ratio:3/4;
  background:linear-gradient(135deg,#f1f3f5,#dee2e6);
  border:1px dashed rgba(0,0,0,0.12);
  display:flex;align-items:center;justify-content:center;
  font-size:20px;color:rgba(0,0,0,0.15);
}

/* ── 台灯开关（checkbox 控制氛围） ── */
#lamp-toggle{display:none}
.lamp-switch{
  display:inline-block;padding:8px 16px;
  background:#fff;border:1px solid #dee2e6;
  border-radius:4px;cursor:pointer;
  font-size:10px;letter-spacing:0.12em;color:#495057;
  margin:16px 0;transition:all 0.2s;
}
.lamp-switch:hover{background:#f8f9fa}
#lamp-toggle:checked ~ .studio-container{
  background:radial-gradient(circle at 50% 30%, rgba(255,248,220,0.15), transparent);
}
#lamp-toggle:checked ~ .studio-container .lamp-switch{
  background:#fffacd;border-color:#f0e68c;color:#856404;
}

/* ── 抽屉系统 ── */
#drawer-toggle{display:none}
.drawer-trigger{
  position:fixed;bottom:20px;left:50%;transform:translateX(-50%);
  background:#212529;color:#fff;padding:10px 24px;
  border-radius:20px;cursor:pointer;z-index:100;
  font-size:10px;letter-spacing:0.15em;
  box-shadow:0 4px 12px rgba(0,0,0,0.3);
  transition:all 0.3s;
}
.drawer-trigger:hover{transform:translateX(-50%) translateY(-2px)}
.drawer-panel{
  position:fixed;bottom:-100%;left:0;width:100%;height:70%;
  background:#fff;border-top:2px solid #dee2e6;
  z-index:200;transition:bottom 0.4s cubic-bezier(0.25,1,0.5,1);
  overflow-y:auto;padding:30px 20px;
  box-shadow:0 -6px 24px rgba(0,0,0,0.15);
}
#drawer-toggle:checked ~ .drawer-panel{
  bottom:0;
}
.drawer-close{
  position:absolute;top:12px;right:16px;
  font-size:20px;color:#adb5bd;cursor:pointer;
}
.drawer-content{
  max-width:400px;margin:0 auto;
}
.drawer-section{
  margin-bottom:20px;padding-bottom:16px;
  border-bottom:1px solid rgba(0,0,0,0.06);
}
.drawer-section:last-child{border-bottom:none}
.drawer-label{
  font-size:9px;color:#868e96;letter-spacing:0.15em;
  margin-bottom:8px;text-transform:uppercase;
}
.drawer-text{
  font-size:12px;line-height:1.75;color:#495057;
}

/* ── 弹窗系统 ── */
.popup-overlay{
  position:fixed;inset:0;background:rgba(0,0,0,0.85);
  opacity:0;pointer-events:none;z-index:9999;
  transition:opacity 0.3s;display:flex;
  align-items:center;justify-content:center;
}
.popup-overlay.is-active{
  opacity:1;pointer-events:auto;
}
.popup-content{
  background:#fff;max-width:90%;max-height:80%;
  padding:20px;border-radius:4px;overflow-y:auto;
  position:relative;
}
.popup-close{
  position:absolute;top:8px;right:12px;
  font-size:24px;color:#adb5bd;cursor:pointer;
}
.popup-title{
  font-size:14px;font-weight:600;color:#212529;
  margin-bottom:12px;letter-spacing:0.08em;
}
.popup-body{
  font-size:12px;line-height:1.75;color:#495057;
}

/* ── 底部签名 ── */
.footer{
  padding:24px 0;text-align:center;
}
.footer-line{
  width:40px;height:1px;
  background:linear-gradient(90deg,transparent,#dee2e6,transparent);
  margin:0 auto 10px;
}
.footer-text{
  font-size:8px;color:#adb5bd;letter-spacing:0.05em;
}
</style>
</head>
<body>
<div class="lace-texture"></div>
<input type="checkbox" id="lamp-toggle">
<input type="checkbox" id="drawer-toggle">

<div class="studio-container">
  <div class="studio-header">
    <div class="studio-title">Private Atelier</div>
    <div class="studio-subtitle">婚纱设计师工作室</div>
  </div>

  <div class="designer-card">
    <div class="designer-name">${name}</div>
    <div class="designer-role">高定婚纱设计师 · 前男友</div>
    <div class="designer-meta">
      <span>27岁</span>
      <span>180cm</span>
      <span>设计工作室主理人</span>
    </div>
  </div>

  <label for="lamp-toggle" class="lamp-switch">台灯开关</label>

  <div class="drafts-zone">
    <div class="draft-card" data-label="Draft A" onclick="openPopup('popup-1')">
      <div class="draft-thumb">A</div>
    </div>
    <div class="draft-card" data-label="Draft B" onclick="openPopup('popup-2')">
      <div class="draft-thumb">B</div>
    </div>
    <div class="draft-card" data-label="Draft C" onclick="openPopup('popup-3')">
      <div class="draft-thumb">C</div>
    </div>
  </div>

  <div style="font-size:11px;color:#868e96;line-height:1.7;padding:0 6px">
    分手三年，再见面时你提着一袋婚纱款式图来找他。他接过资料袋，指尖停在拉链上顿了两秒，抬眼问"谁的婚纱"。你说"我的"。他垂下眼，把资料袋放回你手里，转身走到工作台前点了根烟，半天才说"我不接这单"。你问为什么，他说"因为画不下手"。
  </div>

  <label for="drawer-toggle" class="drawer-trigger">查看完整档案</label>
</div>

<div class="drawer-panel">
  <label for="drawer-toggle" class="drawer-close">✕</label>
  <div class="drawer-content">
    <div class="drawer-section">
      <div class="drawer-label">设计理念</div>
      <div class="drawer-text">
        秦景舟的设计从不追求繁复堆砌,每一条裁剪线都服务于穿着者的轮廓与气质。他说婚纱设计师的工作不是把布料变成梦,而是把新娘变成她自己最想成为的样子。
      </div>
    </div>
    <div class="drawer-section">
      <div class="drawer-label">分手原因</div>
      <div class="drawer-text">
        你们分手时他刚创业第二年,工作室接连亏损三个月,他每天睡不到四小时。你劝他放弃回家继承产业,他冷着脸说"你也觉得我做不成"。争吵后的第二天你收到分手短信:"对不起,我现在养不起你,也没时间陪你。你该找个更好的。"
      </div>
    </div>
    <div class="drawer-section">
      <div class="drawer-label">再见时刻</div>
      <div class="drawer-text">
        三年后他的工作室已是业内顶流,预约排到两年后。你提着婚纱需求来找他,他看完资料抽了半根烟才说"我不接"。你以为他还在记仇,他却把烟掐灭,低声说:"我画不出来。一想到这婚纱要给别人穿,我连笔都拿不稳。"
      </div>
    </div>
    <div class="drawer-section">
      <div class="drawer-label">占有欲表现</div>
      <div class="drawer-text">
        他不会说"不许你嫁",只会用行动拖延:改第一稿说"腰线不够贴合,重来";改第二稿说"蕾丝材质配不上你";改第三稿时他把图纸撕了,转身抱住你说"别结婚了,回来好不好"。
      </div>
    </div>
  </div>
</div>

<div class="popup-overlay" id="popup-1">
  <div class="popup-content">
    <div class="popup-close" onclick="closePopup('popup-1')">✕</div>
    <div class="popup-title">设计稿 A — 初稿笔记</div>
    <div class="popup-body">
      "鱼尾款,腰线收到这里。她腰很细,这个位置最好看。"<br><br>
      笔记右下角的日期是三年前,那时你们还在一起。他把这份草稿保留到现在,压在工作台最底层的抽屉里。
    </div>
  </div>
</div>

<div class="popup-overlay" id="popup-2">
  <div class="popup-content">
    <div class="popup-close" onclick="closePopup('popup-2')">✕</div>
    <div class="popup-title">设计稿 B — 修改记录</div>
    <div class="popup-body">
      "肩线改过三次,每次都不满意。后来发现问题不在肩线,在我画不出她嫁给别人的样子。"<br><br>
      这句话写在修改记录的最后一行,墨水有点晕开,像是被什么东西滴湿过。
    </div>
  </div>
</div>

<div class="popup-overlay" id="popup-3">
  <div class="popup-content">
    <div class="popup-close" onclick="closePopup('popup-3')">✕</div>
    <div class="popup-title">设计稿 C — 最终决定</div>
    <div class="popup-body">
      第三稿画到一半他停了笔,把图纸撕成两半扔进垃圾桶。他转身走到你面前,指尖还沾着铅笔灰,抬手捏住你的下巴强迫你看着他:<br><br>
      "你非要结婚,我给你画。但新郎必须是我。"
    </div>
  </div>
</div>

<div class="footer">
  <div class="footer-line"></div>
  <div class="footer-text">设定纯属虚构 与现实无关</div>
</div>

<script>
function openPopup(id) {
  document.getElementById(id).classList.add('is-active');
}
function closePopup(id) {
  document.getElementById(id).classList.remove('is-active');
}
// 点击遮罩关闭
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
