import type { CharacterProfileDTO } from '../../services/api'
import { escapeHtml } from '../../utils/escapeHtml'
import { ImmersiveProfileFrame } from './ImmersiveProfileFrame'

type Props = { profile: CharacterProfileDTO }
const e = (v: string) => escapeHtml(v)
const tagHtml = (p: CharacterProfileDTO) => (p.tags || []).map(t => `<span>${e(t)}</span>`).join('')
const frame = (p: CharacterProfileDTO, title: string, body: string, css: string, js: string, height = 2200) =>
  <ImmersiveProfileFrame title={`${p.display_name || title} · ${title}`} fallbackHeight={height}
    html={`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>${css}</style><body>${body}</body><script>${js}</script></html>`} />

/* ═══════════════════════════════════════════
   温璃 · 空宅手机
   媒介：他的旧手机 — 锁屏 + 单方面微信 + 相册 + 备忘录
   ═══════════════════════════════════════════ */
export function WenLiProfile({ profile }: Props) {
  const n = e(profile.display_name || '温璃'), tg = tagHtml(profile)
  return frame(profile, '空宅手机', `
<main class="device">
<!-- ▸ 手机壳 -->
<div class="phone">
  <div class="notch"></div>

  <!-- ── 锁屏 ── -->
  <section class="lockscreen">
    <div class="ls-time">08:41</div>
    <div class="ls-date">钟停了。日期不重要。</div>
    <div class="ls-noti">
      <div class="noti">
        <b>微信</b>
        <p>妻子今天也没有回来。</p>
        <small>12分钟前</small>
      </div>
      <div class="noti">
        <b>备忘录</b>
        <p>第327天。继续等。</p>
        <small>凌晨03:17</small>
      </div>
    </div>
    <div class="ls-hint">上滑解锁 · 密码是你的生日</div>
  </section>

  <!-- ── 微信聊天 ── -->
  <section class="wechat">
    <div class="wx-header">
      <span class="wx-back">&lt;</span>
      <b>妻子</b>
      <small>（备注由温璃设置）</small>
    </div>
    <div class="wx-body">
      <div class="wx-date">——— 四年前 ———</div>
      <div class="msg him"><div class="avatar">璃</div><div class="bubble">你明天还来吗</div></div>
      <div class="msg her"><div class="bubble">嗯，来的。</div></div>
      <div class="msg him"><div class="avatar">璃</div><div class="bubble">好。我把裙子洗好了放在衣柜。<br>兔兔也帮你缝好了。</div></div>
      <div class="wx-date">——— 你搬走那天 ———</div>
      <div class="msg him"><div class="avatar">璃</div><div class="bubble">你什么时候回来</div></div>
      <div class="msg him"><div class="avatar">璃</div><div class="bubble">妻子？</div></div>
      <div class="msg him"><div class="avatar">璃</div>
        <div class="bubble">
          <div class="voice"><div class="vbar"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div><small>0:52</small></div>
        </div>
      </div>
      <div class="wx-date">——— 此后三年零七个月 ———</div>
      <div class="msg him"><div class="avatar">璃</div><div class="bubble">今天换了你喜欢的洗衣液。</div></div>
      <div class="msg him"><div class="avatar">璃</div><div class="bubble">兔兔的耳朵又掉了。我用蓝色的线缝的。</div></div>
      <div class="msg him"><div class="avatar">璃</div><div class="bubble">你闻起来变了。是不是去了陌生的地方。</div></div>
      <div class="msg him"><div class="avatar">璃</div><div class="bubble">没关系。我等你。</div></div>
      <div class="msg him"><div class="avatar">璃</div><div class="bubble">第327天。</div></div>
      <div class="msg him last"><div class="avatar">璃</div><div class="bubble">不要离开我好吗</div></div>
      <div class="wx-unread">对方已读 · 无回复</div>
    </div>
    <div class="wx-input">
      <input type="text" placeholder="你不会回复的。他知道。" disabled>
      <button disabled>发送</button>
    </div>
  </section>
</div>

<!-- ── 相册（手机外） ── -->
<section class="album">
  <div class="album-head">
    <small>ALBUM / 你的专属相册 · 2,041张</small>
    <h2>他把手机里所有照片<br>分成两类</h2>
    <p>"你" 和 "没有你"。第二类是空的。</p>
  </div>
  <div class="gallery">
    <div class="gcard" id="g1">
      <div class="gicon">👗</div>
      <b>衣柜</b>
      <p>你穿过的连衣裙。叠好。十年。</p>
    </div>
    <div class="gcard" id="g2">
      <div class="gicon">🍴</div>
      <b>叉子</b>
      <p>叉齿上的划痕不是磨损。</p>
    </div>
    <div class="gcard" id="g3">
      <div class="gicon">🐰</div>
      <b>兔兔</b>
      <p>缝补十一次。每次不同颜色的线。</p>
    </div>
  </div>
  <div class="gallery-detail" id="gdetail"></div>
</section>

<!-- ── 备忘录 ── -->
<section class="memo">
  <div class="memo-bar">
    <span>备忘录</span>
    <small>最近编辑：03:17</small>
  </div>
  <div class="memo-title">空宅生存守则</div>
  <div class="memo-body">
    <details open>
      <summary>01 · 她在的时候</summary>
      <p>替她倒水。叠衣服。把食物切成小块。温顺。乖。所有乖巧都指向同一个目的：让她留下。</p>
    </details>
    <details>
      <summary>02 · 她不在的时候</summary>
      <p>反复确认她的物品还在原处。闻她的衣服。抚摸她坐过的椅子。然后在日记本上画她的脸。第三百二十七张。</p>
    </details>
    <details>
      <summary>03 · 她说要走</summary>
      <p>不哭不闹。只是安静地换掉家里所有门的钥匙。控制欲裹着糖衣。分不清是照顾还是囚禁。</p>
    </details>
  </div>
  <button id="diary">翻开日记本 →</button>
  <p class="diary-page" id="page"></p>
</section>

<!-- ── 音乐播放器 ── -->
<section class="player">
  <div class="player-art">
    <div class="disc">
      <div class="disc-hole"></div>
    </div>
  </div>
  <div class="player-info">
    <div class="song">过家家</div>
    <div class="artist">${n} 的 playlist · 仅1首循环</div>
    <div class="progress"><div class="bar"><div class="fill"></div></div><div class="times"><span>2:14</span><span>3:47</span></div></div>
    <div class="controls">
      <span>⟲</span><span>◁</span><span class="play">▶</span><span>▷</span><span>⟳</span>
    </div>
  </div>
  <blockquote>"你给他一颗糖，他还你一整座空房子。<br>条件是你永远不许离开。"</blockquote>
</section>

<footer>
  <div class="tags">${tg}</div>
</footer>
</main>`,

`*{box-sizing:border-box;margin:0}
html,body{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif;-webkit-font-smoothing:antialiased}
.device{max-width:680px;margin:0 auto;background:transparent}

/* ═══ 手机壳 ═══ */
.phone{margin:20px auto;max-width:375px;border-radius:40px;background:#111;border:3px solid #2a2a2a;box-shadow:0 20px 60px rgba(0,0,0,.6),inset 0 0 0 1px #333;overflow:hidden;position:relative}
.notch{width:120px;height:28px;background:#111;border-radius:0 0 16px 16px;margin:0 auto;position:relative;z-index:10}

/* ── 锁屏 ── */
.lockscreen{padding:20px 24px 30px;background:radial-gradient(ellipse at 50% 30%,#2d2538,#130f18 60%,#0a080d);min-height:420px}
.ls-time{font:72px/1 ui-monospace,monospace;color:#e8ddd0;text-align:center;letter-spacing:.02em;margin-top:8px}
.ls-date{text-align:center;color:#8a7e90;font:12px/1 ui-monospace,monospace;letter-spacing:.1em;margin-top:6px}
.ls-noti{margin-top:32px;display:flex;flex-direction:column;gap:10px}
.noti{background:rgba(255,255,255,.08);backdrop-filter:blur(16px);border-radius:14px;padding:12px 14px;border:1px solid rgba(255,255,255,.06)}
.noti b{color:#e0d4c8;font-size:11px;font-weight:600}
.noti p{color:#c8bab0;font-size:13px;margin-top:4px;line-height:1.5}
.noti small{color:#7a6e78;font-size:10px;display:block;margin-top:4px}
.ls-hint{text-align:center;margin-top:32px;color:#5a4e5a;font:10px ui-monospace,monospace;letter-spacing:.12em}

/* ── 微信聊天 ── */
.wechat{background:#ededed}
.wx-header{display:flex;align-items:center;gap:8px;padding:10px 14px;background:#f7f7f7;border-bottom:1px solid #ddd}
.wx-back{color:#07c160;font-size:18px;font-weight:600}
.wx-header b{color:#1a1a1a;font-size:15px;flex:1}
.wx-header small{color:#999;font-size:10px}
.wx-body{padding:14px 12px 18px;display:flex;flex-direction:column;gap:10px}
.wx-date{text-align:center;color:#b0b0b0;font-size:10px;padding:6px 0}
.msg{display:flex;gap:8px;align-items:flex-start}
.msg.her{flex-direction:row-reverse}
.avatar{width:34px;height:34px;border-radius:4px;background:#d4a8c8;color:#fff;font-size:13px;display:grid;place-items:center;flex-shrink:0}
.bubble{max-width:72%;padding:9px 12px;border-radius:4px 14px 14px 14px;background:#fff;color:#333;font-size:13px;line-height:1.6;position:relative}
.msg.her .bubble{background:#95ec69;border-radius:14px 4px 14px 14px;color:#1a1a1a}
.msg.last .bubble{background:#f8e8e8;color:#8b3a3a}
.voice{display:flex;align-items:center;gap:8px}
.vbar{display:flex;gap:2px;align-items:center;height:22px}
.vbar i{display:block;width:3px;background:#8b3a3a;border-radius:2px;animation:vbounce 1.2s ease-in-out infinite}
.vbar i:nth-child(1){height:6px;animation-delay:0s}
.vbar i:nth-child(2){height:12px;animation-delay:.1s}
.vbar i:nth-child(3){height:18px;animation-delay:.2s}
.vbar i:nth-child(4){height:10px;animation-delay:.3s}
.vbar i:nth-child(5){height:16px;animation-delay:.4s}
.vbar i:nth-child(6){height:8px;animation-delay:.5s}
.vbar i:nth-child(7){height:14px;animation-delay:.6s}
.vbar i:nth-child(8){height:20px;animation-delay:.7s}
.vbar i:nth-child(9){height:6px;animation-delay:.8s}
.vbar i:nth-child(10){height:11px;animation-delay:.9s}
.vbar i:nth-child(11){height:15px;animation-delay:1s}
.vbar i:nth-child(12){height:7px;animation-delay:1.1s}
@keyframes vbounce{0%,100%{transform:scaleY(1)}50%{transform:scaleY(.4)}}
.voice small{color:#999;font-size:11px}
.wx-unread{text-align:center;color:#ccc;font-size:10px;padding:8px 0;font-style:italic}
.wx-input{display:flex;gap:8px;padding:10px 12px;background:#f7f7f7;border-top:1px solid #ddd}
.wx-input input{flex:1;border:1px solid #ddd;border-radius:6px;padding:8px 10px;font-size:12px;background:#fff;color:#ccc}
.wx-input button{border:0;background:#ccc;color:#fff;border-radius:6px;padding:8px 14px;font-size:12px}

/* ═══ 相册区域 ═══ */
.album{padding:48px 24px;background:linear-gradient(175deg,#1e1a24,#110e16)}
.album-head small{color:#8a7e90;font:10px ui-monospace,monospace;letter-spacing:.14em}
.album-head h2{margin-top:16px;color:#e8ddd0;font:28px/1.4 "Songti SC",serif;font-weight:400}
.album-head p{color:#a89898;font:13px/1.7 "Kaiti SC",serif;margin-top:8px}
.gallery{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:28px}
.gcard{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.06);border-radius:12px;padding:18px 10px;text-align:center;cursor:pointer;transition:.3s}
.gcard:hover,.gcard.on{background:rgba(255,255,255,.08);border-color:rgba(196,68,68,.25)}
.gicon{font-size:26px;line-height:1}
.gcard b{display:block;margin-top:10px;color:#d4c0b8;font-size:12px}
.gcard p{color:#8a7878;font-size:10px;margin-top:4px;line-height:1.5}
.gallery-detail{min-height:50px;margin-top:18px;color:#d4b8b0;font:15px/1.8 "Kaiti SC",serif;padding:0 4px}

/* ═══ 备忘录 ═══ */
.memo{margin:0 auto;max-width:375px;background:#fff;color:#333}
.memo-bar{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;background:#f8f8f8;border-bottom:1px solid #eee}
.memo-bar span{color:#333;font-size:13px;font-weight:600}
.memo-bar small{color:#aaa;font-size:10px}
.memo-title{padding:18px 18px 0;font-size:22px;font-weight:700;color:#1a1a1a}
.memo-body{padding:14px 18px 20px}
.memo-body details{border-bottom:1px solid #f0f0f0;padding:12px 0}
.memo-body summary{cursor:pointer;font-size:13px;font-weight:600;color:#666;list-style:none}
.memo-body summary::-webkit-details-marker{display:none}
.memo-body summary::before{content:"";display:inline-block;width:6px;height:6px;border-right:2px solid #999;border-bottom:2px solid #999;transform:rotate(-45deg);margin-right:8px;transition:.2s}
details[open] summary::before{transform:rotate(45deg)}
.memo-body p{color:#555;font-size:13px;line-height:1.75;margin-top:8px;padding-left:14px}
.memo>button{display:block;margin:0 18px 18px;border:0;background:none;color:#8b3a3a;font-size:12px;cursor:pointer;padding:0}
.diary-page{min-height:24px;padding:0 18px 20px;color:#8b3a3a;font:14px/1.7 "Kaiti SC",serif}

/* ═══ 音乐播放器 ═══ */
.player{padding:48px 24px 40px;background:radial-gradient(ellipse at 50% 60%,#2a2030,#12101a);text-align:center}
.player-art{display:flex;justify-content:center}
.disc{width:140px;height:140px;border-radius:50%;background:conic-gradient(#3d3042,#1a1520,#3d3042,#1a1520,#3d3042);border:3px solid #4a3e50;display:grid;place-items:center;animation:spin 8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.disc-hole{width:22px;height:22px;border-radius:50%;background:#12101a;border:2px solid #6a5870}
.player-info{margin-top:24px}
.song{color:#e8ddd0;font-size:18px;font-weight:600;letter-spacing:.04em}
.artist{color:#8a7e90;font-size:11px;margin-top:4px}
.progress{margin-top:20px;padding:0 20px}
.bar{height:3px;background:#2a2530;border-radius:2px;overflow:hidden}
.fill{width:58%;height:100%;background:linear-gradient(90deg,#8b3a3a,#c46868);border-radius:2px}
.times{display:flex;justify-content:space-between;margin-top:6px;color:#6a5e70;font-size:10px}
.controls{display:flex;justify-content:center;gap:28px;margin-top:18px;color:#d4c0c0;font-size:20px}
.play{width:40px;height:40px;border-radius:50%;background:rgba(139,58,58,.3);display:grid;place-items:center;font-size:16px}
.player blockquote{margin-top:32px;color:#a89098;font:15px/1.8 "Kaiti SC","Songti SC",serif;text-align:left;padding:18px;border-left:2px solid rgba(139,58,58,.3)}

/* ═══ footer ═══ */
footer{padding:30px 24px 38px;background:transparent}
.tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.tags span{color:#7a6878;font-size:10px;font-family:ui-monospace,monospace;padding:4px 10px;border:1px solid rgba(255,255,255,.06);border-radius:20px}`,

`const details={
  g1:'它还留着十年前洗衣液的残香。他每隔一段时间打开衣柜，把脸埋进去，深深吸一口气。然后把裙子重新叠好。折痕比记忆还整齐。',
  g2:'叉齿上有一道极细的划痕。不是磨损——是舌尖反复舔过留下的。你用过一次的叉子。他舔了四年。',
  g3:'缝补过十一次。每次不同颜色的线。它是你们的女儿。他比你更认真地养着——每晚把它塞进鞋盒，说"女儿睡觉了"。'
};
document.querySelectorAll('.gcard').forEach(c=>c.onclick=()=>{
  document.querySelectorAll('.gcard').forEach(x=>x.classList.remove('on'));
  c.classList.add('on');
  document.getElementById('gdetail').textContent=details[c.id];
});
document.getElementById('diary').onclick=()=>{
  const p=document.getElementById('page');
  p.textContent=p.textContent?'':'第327页。画的还是你。旁边写着一行字，笔迹歪歪扭扭："妻子今天没有回家。等。"';
}`, 2600)
}

/* ═══════════════════════════════════════════
   楚寒声 · 学习桌面
   媒介：桌面俯拍 — 音乐播放器 + 微信四年空白 + 备课时间线 + 折角猫
   ═══════════════════════════════════════════ */
export function ChuHanshengProfile({ profile }: Props) {
  const n = e(profile.display_name || '楚寒声'), tg = tagHtml(profile)
  return frame(profile, '备课桌面', `
<main class="desk">

<!-- ── 音乐播放器卡片 ── -->
<section class="music-card">
  <div class="mc-bg"></div>
  <div class="mc-content">
    <div class="mc-disc"><div class="mc-hole"></div></div>
    <div class="mc-meta">
      <div class="mc-now">PLAYING</div>
      <div class="mc-song">安静</div>
      <div class="mc-artist">周杰伦</div>
      <small>四年前你设成他的铃声。他没换。</small>
    </div>
    <div class="mc-wave">
      ${Array.from({length:24},(_,i)=>`<i style="animation-delay:${(i*0.08).toFixed(2)}s"></i>`).join('')}
    </div>
    <div class="mc-bar"><div class="mc-fill"></div></div>
  </div>
</section>

<!-- ── 模拟手机 ── -->
<div class="phone">
  <div class="notch"></div>

  <!-- 微信聊天 -->
  <section class="wechat">
    <div class="wx-header">
      <span class="wx-back">&lt;</span>
      <b>${n}</b>
      <span class="wx-dot"></span>
    </div>
    <div class="wx-body">
      <div class="wx-date">——— 四年前 ———</div>
      <div class="msg her"><div class="bubble">我们分手吧。</div></div>
      <div class="msg him"><div class="avatar">楚</div><div class="bubble">好。</div></div>
      <div class="wx-date">——— 四年零七天的空白 ———</div>
      <div class="wx-gap">
        <div class="gap-line"></div>
        <p>1,468 天无消息</p>
        <div class="gap-line"></div>
      </div>
      <div class="wx-date">——— 今天 ———</div>
      <div class="msg sys"><p>楚寒声 已通过你哥的推荐添加了你</p></div>
      <div class="msg him"><div class="avatar">楚</div><div class="bubble">周六下午两点，线性代数。<br>课本自备。</div></div>
      <div class="msg her"><div class="bubble">楚寒声？</div></div>
      <div class="msg him"><div class="avatar">楚</div><div class="bubble">嗯。</div></div>
      <div class="msg her"><div class="bubble">你怎么在这儿？</div></div>
      <div class="msg him"><div class="avatar">楚</div><div class="bubble">你哥找的家教。我缺课时费，他缺老师。正好。</div></div>
    </div>
    <div class="wx-input">
      <input type="text" placeholder="他的耳尖红了。你看见了。" disabled>
      <button disabled>发送</button>
    </div>
  </section>
</div>

<!-- ── 备课本 ── -->
<section class="lecturenote">
  <div class="ln-spine"></div>
  <div class="ln-page">
    <div class="ln-grid"></div>
    <div class="ln-margin"></div>
    <small class="ln-label">LECTURE 04 / LINEAR ALGEBRA</small>
    <h2>讲义批注</h2>
    <p class="ln-sub">你的批注密度是其他学生的 <em>3 倍</em></p>
    <div class="timeline">
      <div class="tl-row"><div class="tl-time">18:00</div><div class="tl-dot"></div><div class="tl-text">到达。换鞋。不喝你家的水。</div></div>
      <div class="tl-row"><div class="tl-time">18:03</div><div class="tl-dot"></div><div class="tl-text">翻到第四章。指尖碰到她的手背。<span class="redink">缩回。</span></div></div>
      <div class="tl-row"><div class="tl-time">19:22</div><div class="tl-dot"></div><div class="tl-text">她趴在桌上，额头快碰到备课本。<span class="redink">抽走。</span></div></div>
      <div class="tl-row"><div class="tl-time">20:10</div><div class="tl-dot"></div><div class="tl-text">准时离开。说去图书馆。不是图书馆。</div></div>
      <div class="tl-row last"><div class="tl-time">20:11</div><div class="tl-dot red"></div><div class="tl-text"><span class="redink">在楼下停了三分钟才发动车。</span></div></div>
    </div>
  </div>
</section>

<!-- ── 他的习惯观察 ── -->
<section class="observe">
  <small>AFTER CLASS / 他没说出口的观察报告</small>
  <h2>他记得你的所有习惯</h2>
  <div class="obs-cards">
    <div class="obs-card on" data-o="left">
      <div class="obs-num">01</div>
      <b>左手撑脸</b>
    </div>
    <div class="obs-card" data-o="sleepy">
      <div class="obs-num">02</div>
      <b>八点半犯困</b>
    </div>
    <div class="obs-card" data-o="water">
      <div class="obs-num">03</div>
      <b>杯子空了</b>
    </div>
  </div>
  <p class="obs-detail" id="obstext">你习惯用左手撑脸。他递笔时会递到你左手边。四年前也是。</p>
</section>

<!-- ── 最后一页 · 猫 ── -->
<section class="lastpage">
  <div class="lp-paper">
    <div class="lp-fold"></div>
    <div class="lp-grid"></div>
    <p class="lp-hint">备课本最后一页。折角处夹着一张小纸片。</p>
    <button id="unfold">展开折角 →</button>
    <div class="lp-hidden" id="catReveal">
      <div class="lp-cat">
        <svg viewBox="0 0 80 60" fill="none" stroke="#6b5a42" stroke-width="1.5" stroke-linecap="round">
          <path d="M20 45 Q25 20 35 25 Q40 10 45 25 Q55 20 60 45"/>
          <circle cx="33" cy="32" r="2"/><circle cx="47" cy="32" r="2"/>
          <path d="M38 36 Q40 38 42 36"/>
          <path d="M25 35 L12 33 M25 37 L13 39 M55 35 L68 33 M55 37 L67 39"/>
        </svg>
      </div>
      <p>四年前你画在他手背上的。<br>墨迹已经模糊了。但他没有弄丢。</p>
      <div class="lp-quote">"……下一题，概率论。翻到第七章。"<br><small>他的耳尖红了一小片。</small></div>
    </div>
  </div>
</section>

<!-- ── 收尾 ── -->
<section class="ending">
  <blockquote>备课本最后一页藏着猫。<br>他不是忘了。<br><em>或者，他故意忘了。</em></blockquote>
</section>

<footer>
  <div class="tags">${tg}</div>
</footer>
</main>`,

`*{box-sizing:border-box;margin:0}
html,body{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif;-webkit-font-smoothing:antialiased}
.desk{max-width:680px;margin:0 auto;background:transparent}

/* ═══ 音乐播放器卡片 ═══ */
.music-card{margin:20px 24px;border-radius:20px;overflow:hidden;position:relative;background:#1a2a3a}
.mc-bg{position:absolute;inset:0;background:linear-gradient(135deg,#2c3e50,#1a2a3a);opacity:.9}
.mc-content{position:relative;padding:28px 24px;display:grid;grid-template-columns:72px 1fr;gap:18px;align-items:center}
.mc-disc{width:72px;height:72px;border-radius:50%;background:conic-gradient(#3a5a70,#1a2a38,#3a5a70,#1a2a38);border:2px solid #4a6a80;display:grid;place-items:center;animation:spin 6s linear infinite;grid-row:span 2}
@keyframes spin{to{transform:rotate(360deg)}}
.mc-hole{width:14px;height:14px;border-radius:50%;background:#1a2a3a;border:2px solid #5a7a90}
.mc-now{color:#5a8aaa;font:9px ui-monospace,monospace;letter-spacing:.14em}
.mc-song{color:#e8e2d8;font-size:18px;font-weight:600;margin-top:2px}
.mc-artist{color:#7a9aaa;font-size:11px;margin-top:2px}
.mc-meta small{color:#5a7a8a;font-size:10px;margin-top:4px;display:block;font-style:italic}
.mc-wave{grid-column:span 2;display:flex;gap:2px;align-items:center;height:28px;padding:0 4px}
.mc-wave i{display:block;flex:1;background:#4a7a90;border-radius:1px;animation:wb 1.4s ease-in-out infinite;height:8px}
@keyframes wb{0%,100%{height:4px;opacity:.4}50%{height:22px;opacity:.9}}
.mc-bar{grid-column:span 2;height:2px;background:#2a3a48;border-radius:1px;overflow:hidden}
.mc-fill{width:42%;height:100%;background:linear-gradient(90deg,#4a7a90,#8ab0c0);border-radius:1px}

/* ═══ 手机壳 ═══ */
.phone{margin:28px auto;max-width:375px;border-radius:40px;background:#111;border:3px solid #2a2a2a;box-shadow:0 20px 60px rgba(0,0,0,.6),inset 0 0 0 1px #333;overflow:hidden;position:relative}
.notch{width:120px;height:28px;background:#111;border-radius:0 0 16px 16px;margin:0 auto;position:relative;z-index:10}

/* ── 微信 ── */
.wechat{background:#ededed}
.wx-header{display:flex;align-items:center;gap:8px;padding:10px 14px;background:#f7f7f7;border-bottom:1px solid #ddd}
.wx-back{color:#07c160;font-size:18px;font-weight:600}
.wx-header b{color:#1a1a1a;font-size:15px;flex:1}
.wx-dot{width:8px;height:8px;border-radius:50%;background:#07c160}
.wx-body{padding:14px 12px 18px;display:flex;flex-direction:column;gap:10px}
.wx-date{text-align:center;color:#b0b0b0;font-size:10px;padding:6px 0}
.msg{display:flex;gap:8px;align-items:flex-start}
.msg.her{flex-direction:row-reverse}
.msg.sys{justify-content:center}
.msg.sys p{color:#b0b0b0;font-size:10px;background:rgba(0,0,0,.03);padding:4px 12px;border-radius:4px}
.avatar{width:34px;height:34px;border-radius:4px;background:#4a6a80;color:#fff;font-size:13px;display:grid;place-items:center;flex-shrink:0}
.bubble{max-width:72%;padding:9px 12px;border-radius:4px 14px 14px 14px;background:#fff;color:#333;font-size:13px;line-height:1.6;position:relative}
.msg.her .bubble{background:#95ec69;border-radius:14px 4px 14px 14px;color:#1a1a1a}
.wx-gap{display:flex;align-items:center;gap:12px;padding:16px 0}
.gap-line{flex:1;height:1px;background:#d0d0d0}
.wx-gap p{color:#c0c0c0;font-size:10px;white-space:nowrap;font-style:italic}
.wx-input{display:flex;gap:8px;padding:10px 12px;background:#f7f7f7;border-top:1px solid #ddd}
.wx-input input{flex:1;border:1px solid #ddd;border-radius:6px;padding:8px 10px;font-size:12px;background:#fff;color:#ccc}
.wx-input button{border:0;background:#ccc;color:#fff;border-radius:6px;padding:8px 14px;font-size:12px}

/* ═══ 备课本 ═══ */
.lecturenote{margin:28px 16px;position:relative}
.ln-spine{position:absolute;left:0;top:0;bottom:0;width:12px;background:linear-gradient(90deg,#6b5a42,#8a7560,#6b5a42);border-radius:4px 0 0 4px;z-index:1}
.ln-page{position:relative;margin-left:12px;background:#f5f1e8;padding:28px 20px 32px 32px;border-radius:0 6px 6px 0;overflow:hidden}
.ln-grid{position:absolute;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 27px,#e0dace 27px,#e0dace 28px);opacity:.5;pointer-events:none}
.ln-margin{position:absolute;left:28px;top:0;bottom:0;width:1px;background:#e8a0a0;opacity:.4}
.ln-label{color:#8a7e6e;font:9px ui-monospace,monospace;letter-spacing:.12em;display:block;position:relative}
.ln-page h2{margin-top:14px;color:#2c2820;font:22px "Songti SC",serif;font-weight:400;position:relative}
.ln-sub{color:#6a6258;font:12px "Kaiti SC",serif;margin-top:6px;position:relative}
.ln-sub em{color:#c44;font-style:normal;font-weight:600}
.timeline{margin-top:22px;position:relative;padding-left:16px;border-left:2px solid #d0c8b8}
.tl-row{display:flex;gap:12px;padding:10px 0;position:relative;align-items:baseline}
.tl-time{flex-shrink:0;width:40px;color:#8a7e6e;font:10px ui-monospace,monospace}
.tl-dot{position:absolute;left:-22px;top:14px;width:8px;height:8px;border-radius:50%;background:#c8bfaa;border:2px solid #f5f1e8}
.tl-dot.red{background:#c44}
.tl-text{color:#4a4438;font:12px/1.7 "Kaiti SC",serif;position:relative}
.redink{color:#c44;font-weight:500}
.tl-row.last{border-bottom:none}

/* ═══ 观察报告 ═══ */
.observe{padding:40px 24px;background:linear-gradient(170deg,#1e2a34,#141e28);color:#e0d8cc}
.observe small{color:#6a8a98;font:10px ui-monospace,monospace;letter-spacing:.12em}
.observe h2{margin-top:14px;font:24px "Songti SC",serif;font-weight:400}
.obs-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:24px}
.obs-card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.06);border-radius:10px;padding:14px 10px;text-align:center;cursor:pointer;transition:.3s}
.obs-card:hover,.obs-card.on{background:rgba(74,106,128,.15);border-color:rgba(74,106,128,.35)}
.obs-num{color:#4a7a90;font:10px ui-monospace,monospace}
.obs-card b{display:block;margin-top:6px;color:#c8bcaa;font-size:12px;font-weight:500}
.obs-detail{min-height:50px;margin-top:18px;color:#b0a898;font:14px/1.85 "Kaiti SC",serif}

/* ═══ 最后一页 ═══ */
.lastpage{margin:0 16px;position:relative}
.lp-paper{position:relative;background:#f5f1e8;padding:28px 20px 32px 32px;margin-left:12px;border-radius:0 6px 6px 0;overflow:hidden}
.lp-fold{position:absolute;top:0;right:0;width:50px;height:50px;background:linear-gradient(225deg,#d8d2c6 50%,transparent 50%);box-shadow:-2px 2px 4px rgba(0,0,0,.06);z-index:2}
.lp-grid{position:absolute;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 27px,#e0dace 27px,#e0dace 28px);opacity:.5;pointer-events:none}
.lp-hint{color:#8a7e6e;font:13px "Kaiti SC",serif;position:relative}
.lastpage button{border:0;background:none;color:#8b6a5a;font:11px ui-monospace,monospace;cursor:pointer;margin-top:12px;position:relative}
.lp-hidden{display:none;margin-top:20px;position:relative;animation:fadeIn .6s ease}
.lp-hidden.show{display:block}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.lp-cat{width:80px}
.lp-cat svg{width:100%;display:block;opacity:.6}
.lp-hidden p{margin-top:12px;color:#6b5e50;font:13px/1.8 "Kaiti SC",serif}
.lp-quote{margin-top:16px;padding:14px;background:rgba(107,90,66,.06);border-left:2px solid #8b7355;color:#5a4e40;font:14px/1.75 "Songti SC",serif;border-radius:0 4px 4px 0}
.lp-quote small{color:#8a7e6e;font-size:11px;display:block;margin-top:4px}

/* ═══ 收尾 ═══ */
.ending{padding:40px 24px;text-align:center}
.ending blockquote{color:#c8bcaa;font:20px/1.7 "Songti SC",serif}
.ending em{color:#7a9aaa;font-style:normal}

/* ═══ footer ═══ */
footer{padding:20px 24px 38px;background:transparent}
.tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.tags span{color:#6a8a98;font-size:10px;font-family:ui-monospace,monospace;padding:4px 10px;border:1px solid rgba(255,255,255,.06);border-radius:20px}`,

`const obs={left:'你习惯用左手撑脸。他递笔时会递到你左手边。四年前也是。',sleepy:'你八点半会犯困。他会在八点二十说"休息五分钟"。比你的生物钟还准。',water:'你的杯子空了。他会停下讲课，等你倒完水再继续。好像你喝水这件事，比线性代数重要。'};
document.querySelectorAll('.obs-card').forEach(c=>c.onclick=()=>{
  document.querySelectorAll('.obs-card').forEach(x=>x.classList.remove('on'));
  c.classList.add('on');
  document.getElementById('obstext').textContent=obs[c.dataset.o];
});
document.getElementById('unfold').onclick=()=>{
  const el=document.getElementById('catReveal');
  el.classList.toggle('show');
  document.getElementById('unfold').textContent=el.classList.contains('show')?'折回':'展开折角 →';
}`, 2800)
}
/* ═══════════════════════════════════════════
   陆时衿 · 加密手机
   媒介：他的手机 — 锁屏通知 + 加密备忘录 + 朋友圈 + 闹钟
   ═══════════════════════════════════════════ */
export function LuShijinProfile({ profile }: Props) {
  const n = e(profile.display_name || '陆时衿'), tg = tagHtml(profile)
  return frame(profile, '加密手机', `
<main class="device">
<div class="phone">
  <div class="notch"></div>

  <!-- ── 锁屏 ── -->
  <section class="lockscreen">
    <div class="ls-time">23:48</div>
    <div class="ls-date">周五 · 十一月</div>
    <div class="ls-noti">
      <div class="noti">
        <div class="noti-icon">微信</div>
        <div class="noti-body">
          <b>你</b>
          <p>时衿哥，晚安。</p>
          <small>刚刚 · 已读</small>
        </div>
      </div>
      <div class="noti dim">
        <div class="noti-icon">闹钟</div>
        <div class="noti-body">
          <b>每日 23:48</b>
          <p class="alarm-label">——</p>
          <small>标签已隐藏</small>
        </div>
      </div>
    </div>
    <div class="ls-hint">上滑解锁 · Face ID</div>
  </section>

  <!-- ── 备忘录 · 加密文件夹 ── -->
  <section class="notes-app">
    <div class="notes-header">
      <span>备忘录</span>
      <small>1个文件夹</small>
    </div>
    <div class="folder locked" id="lockedFolder">
      <div class="folder-icon">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#8a9ab0" stroke-width="1.5">
          <rect x="3" y="11" width="18" height="11" rx="2"/>
          <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
        </svg>
      </div>
      <div class="folder-meta">
        <b>不要打开</b>
        <small>已锁定 · 6条记录</small>
      </div>
      <span class="folder-arrow">></span>
    </div>
    <div class="folder-content" id="folderContent">
      <div class="note-entry">
        <div class="note-date">03/15</div>
        <div class="note-text">第一次见面。客厅聚会。她穿家居服，头发半干。叫了我名字。我没有看她第二眼。<span class="redact">（看了。）</span></div>
      </div>
      <div class="note-entry">
        <div class="note-date">03/22</div>
        <div class="note-text">她加了我好友。审核了六个小时。不是犹豫。是在反复确认聊天背景是不是默认的。</div>
      </div>
      <div class="note-entry">
        <div class="note-date">04/08</div>
        <div class="note-text">她评论了我的朋友圈："好厉害"。我没回复。截了图。</div>
      </div>
      <div class="note-entry">
        <div class="note-date">05/17</div>
        <div class="note-text">她在群里@我问投资建议。我私聊发了三千字。发完才意识到语气太认真了。</div>
      </div>
      <div class="note-entry">
        <div class="note-date">07/02</div>
        <div class="note-text">吃饭时她坐在我对面。我全程没看她。<span class="redact">（余光里她换了发型。）</span></div>
      </div>
      <div class="note-entry">
        <div class="note-date">昨晚</div>
        <div class="note-text">23:48，语音消息。"时衿哥，晚安。"有鼻音。刚洗完澡。<br>我回了"嗯"。<br>然后去冲了冷水澡。</div>
      </div>
    </div>
  </section>
</div>

<!-- ── 朋友圈 ── -->
<section class="moments">
  <div class="moments-header">
    <small>WECHAT MOMENTS / 朋友圈</small>
    <h2>他的朋友圈一个月发一条</h2>
    <p>全是行业报告。没有评论。没有点赞。但有一个隐藏相册。</p>
  </div>
  <div class="moment-list">
    <div class="moment-item">
      <div class="moment-avatar">陆</div>
      <div class="moment-body">
        <b>${n}</b>
        <p class="moment-text">转发：2024 Q3 一级市场并购趋势报告</p>
        <small>3天前 · 0评论 · 0点赞</small>
      </div>
    </div>
    <div class="moment-item">
      <div class="moment-avatar">陆</div>
      <div class="moment-body">
        <b>${n}</b>
        <p class="moment-text">转发：消费赛道估值模型重构</p>
        <small>1个月前 · 0评论 · 0点赞</small>
      </div>
    </div>
    <div class="moment-item">
      <div class="moment-avatar">陆</div>
      <div class="moment-body">
        <b>${n}</b>
        <p class="moment-text">转发：硬科技投资逻辑与退出路径</p>
        <small>2个月前 · 0评论 · 0点赞</small>
      </div>
    </div>
  </div>
  <div class="hidden-album">
    <div class="album-icon">
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#8a9ab0" stroke-width="1.5">
        <rect x="3" y="3" width="18" height="18" rx="2"/>
        <circle cx="8" cy="8" r="1.5"/>
        <path d="M21 15l-5-5L5 21"/>
      </svg>
    </div>
    <span>隐藏相册</span>
    <small>47 张</small>
    <p class="album-note">全部来自同一个人的朋友圈。他不点赞。但每一张都长按保存了。</p>
  </div>
</section>

<!-- ── 闹钟 ── -->
<section class="alarm-section">
  <div class="alarm-card">
    <div class="alarm-time">23:48</div>
    <div class="alarm-repeat">每天</div>
    <div class="alarm-name" id="alarmName">标签：——</div>
    <button id="revealAlarm">查看标签</button>
  </div>
  <blockquote>"他对所有人礼貌疏离，<br>只有你的晚安语音能让他半夜起来冲冷水澡。"</blockquote>
</section>

<footer>
  <div class="tags">${tg}</div>
</footer>
</main>`,

`*{box-sizing:border-box;margin:0}
html,body{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif;-webkit-font-smoothing:antialiased}
.device{max-width:680px;margin:0 auto;background:transparent}

/* ═══ 手机壳 ═══ */
.phone{margin:20px auto;max-width:375px;border-radius:40px;background:#111;border:3px solid #2a2a2a;box-shadow:0 20px 60px rgba(0,0,0,.6),inset 0 0 0 1px #333;overflow:hidden;position:relative}
.notch{width:120px;height:28px;background:#111;border-radius:0 0 16px 16px;margin:0 auto;position:relative;z-index:10}

/* ── 锁屏 ── */
.lockscreen{padding:20px 24px 30px;background:linear-gradient(170deg,#1a2030,#0e1420);min-height:380px}
.ls-time{font:68px/1 ui-monospace,monospace;color:#c8d0e0;text-align:center;letter-spacing:.02em;margin-top:8px}
.ls-date{text-align:center;color:#5a6a80;font:12px/1 ui-monospace,monospace;letter-spacing:.1em;margin-top:6px}
.ls-noti{margin-top:28px;display:flex;flex-direction:column;gap:10px}
.noti{background:rgba(255,255,255,.06);backdrop-filter:blur(16px);border-radius:14px;padding:12px 14px;border:1px solid rgba(255,255,255,.05);display:flex;gap:10px;align-items:flex-start}
.noti.dim{opacity:.6}
.noti-icon{width:34px;height:34px;border-radius:8px;background:rgba(100,140,200,.15);color:#7a9ac0;font-size:10px;display:grid;place-items:center;flex-shrink:0}
.noti-body b{color:#c8d0e0;font-size:11px;font-weight:600}
.noti-body p{color:#a0b0c8;font-size:13px;margin-top:3px;line-height:1.4}
.noti-body small{color:#5a6a80;font-size:10px;display:block;margin-top:3px}
.alarm-label{font-style:italic}
.ls-hint{text-align:center;margin-top:28px;color:#3a4a5a;font:10px ui-monospace,monospace;letter-spacing:.12em}

/* ── 备忘录 ── */
.notes-app{background:#f8f8fa}
.notes-header{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;background:#f0f0f2;border-bottom:1px solid #e0e0e2}
.notes-header span{color:#333;font-size:14px;font-weight:600}
.notes-header small{color:#aaa;font-size:10px}
.folder{display:flex;align-items:center;gap:12px;padding:14px 18px;cursor:pointer;border-bottom:1px solid #eee;transition:.2s}
.folder:hover{background:#f0f0f2}
.folder-icon{width:36px;height:36px;border-radius:8px;background:rgba(100,120,160,.08);display:grid;place-items:center}
.folder-meta b{color:#333;font-size:13px;display:block}
.folder-meta small{color:#999;font-size:10px}
.folder-arrow{color:#ccc;font-size:14px;margin-left:auto}
.folder-content{display:none;padding:0 18px 18px;background:#f8f8fa}
.folder-content.show{display:block}
.note-entry{padding:14px 0;border-bottom:1px solid #eee}
.note-date{color:#7a8a9a;font:10px ui-monospace,monospace;margin-bottom:4px}
.note-text{color:#444;font:12px/1.7 "Kaiti SC",serif}
.redact{color:#8b4a4a;font-style:italic}

/* ═══ 朋友圈 ═══ */
.moments{padding:40px 24px;background:linear-gradient(170deg,#1a2030,#0e1420)}
.moments-header small{color:#5a6a80;font:10px ui-monospace,monospace;letter-spacing:.14em}
.moments-header h2{margin-top:14px;color:#c8d0e0;font:24px/1.4 "Songti SC",serif;font-weight:400}
.moments-header p{color:#7a8a9a;font:12px/1.6 "Kaiti SC",serif;margin-top:6px}
.moment-list{margin-top:24px;display:flex;flex-direction:column;gap:16px}
.moment-item{display:flex;gap:10px;align-items:flex-start}
.moment-avatar{width:34px;height:34px;border-radius:4px;background:rgba(100,140,200,.12);color:#8aa0c0;font-size:13px;display:grid;place-items:center;flex-shrink:0}
.moment-body b{color:#b0c0d0;font-size:12px}
.moment-text{color:#8a9aaa;font-size:11px;margin-top:4px;line-height:1.5}
.moment-body small{color:#4a5a6a;font-size:10px;display:block;margin-top:4px}
.hidden-album{margin-top:28px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.06);border-radius:12px;padding:16px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.album-icon{width:28px;height:28px;border-radius:6px;background:rgba(100,140,200,.1);display:grid;place-items:center}
.hidden-album span{color:#a0b0c8;font-size:12px;font-weight:500}
.hidden-album small{color:#c0a060;font:11px ui-monospace,monospace;margin-left:auto}
.album-note{width:100%;margin-top:8px;color:#6a7a8a;font:11px/1.6 "Kaiti SC",serif}

/* ═══ 闹钟 ═══ */
.alarm-section{padding:40px 24px;background:linear-gradient(170deg,#12182a,#0a0e18);text-align:center}
.alarm-card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.06);border-radius:16px;padding:24px;display:inline-block}
.alarm-time{font:48px/1 ui-monospace,monospace;color:#c8d0e0;letter-spacing:.02em}
.alarm-repeat{color:#5a6a80;font:10px ui-monospace,monospace;margin-top:6px;letter-spacing:.12em}
.alarm-name{color:#7a8a9a;font:12px "Kaiti SC",serif;margin-top:12px;min-height:20px;transition:.3s}
.alarm-section button{margin-top:12px;border:0;background:rgba(100,140,200,.12);color:#8aa0c0;font:11px ui-monospace,monospace;padding:6px 16px;border-radius:6px;cursor:pointer}
.alarm-section blockquote{margin-top:28px;color:#7a8a9a;font:15px/1.8 "Kaiti SC","Songti SC",serif;text-align:left;padding:16px;border-left:2px solid rgba(100,140,200,.15)}

/* ═══ footer ═══ */
footer{padding:28px 24px 38px;background:transparent}
.tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.tags span{color:#5a6a80;font-size:10px;font-family:ui-monospace,monospace;padding:4px 10px;border:1px solid rgba(255,255,255,.06);border-radius:20px}`,

`document.getElementById('lockedFolder').onclick=function(){
  var c=document.getElementById('folderContent');
  c.classList.toggle('show');
  this.querySelector('.folder-arrow').textContent=c.classList.contains('show')?'v':'>';
};
document.getElementById('revealAlarm').onclick=function(){
  var el=document.getElementById('alarmName');
  if(el.dataset.revealed){el.textContent='标签：——';el.dataset.revealed='';this.textContent='查看标签';}
  else{el.textContent='标签：她的名字';el.dataset.revealed='1';this.textContent='隐藏';}
};`, 2600)
}

/* ═══════════════════════════════════════════
   顾晏深 · 猎人手机
   媒介：破碎屏幕 — 锁屏监控 + 定位追踪 + 暗拍相册 + 通话记录
   ═══════════════════════════════════════════ */
export function GuYanshenProfile({ profile }: Props) {
  const tg = tagHtml(profile)
  return frame(profile, '猎人手机', `
<main class="device">
<div class="phone cracked">
  <div class="notch"></div>
  <div class="crack-overlay"></div>

  <!-- ── 锁屏 ── -->
  <section class="lockscreen">
    <div class="ls-time">02:47</div>
    <div class="ls-date">她不知道我在看。</div>
    <div class="surveillance">
      <div class="surv-frame">
        <div class="surv-static"></div>
        <div class="surv-overlay">
          <small>CAM-07 / 22:14:03 / REC</small>
          <div class="surv-dot"></div>
        </div>
        <p class="surv-desc">路口便利店。她买了一瓶水。头发剪短了。</p>
      </div>
    </div>
    <div class="ls-hint">密码：她搬走的日期</div>
  </section>

  <!-- ── 定位追踪 ── -->
  <section class="tracker">
    <div class="tracker-header">
      <span class="tracker-dot"></span>
      <b>LOCATION TRACKER</b>
      <small>ACTIVE</small>
    </div>
    <div class="tracker-map">
      <div class="map-grid"></div>
      <div class="map-pin">
        <div class="pin-pulse"></div>
        <div class="pin-label">她</div>
      </div>
      <div class="map-info">
        <div class="map-row"><small>LAT</small><span>39.9042</span></div>
        <div class="map-row"><small>LNG</small><span>116.4074</span></div>
        <div class="map-row"><small>DIST</small><span class="highlight">378m</span></div>
        <div class="map-row"><small>TRACK</small><span>372 天</span></div>
      </div>
    </div>
    <p class="tracker-note">他找到她用了八个月。剩下四个月，他什么都没做。只是看着。</p>
  </section>
</div>

<!-- ── 暗拍相册 ── -->
<section class="gallery">
  <div class="gallery-header">
    <small>GALLERY / 365 天 · 47 张</small>
    <h2>每一张都是偷拍的</h2>
    <p>她不知道他在对面的车里。在天桥上。在便利店门口。</p>
  </div>
  <div class="photo-grid">
    <div class="photo-card" data-id="p1"><div class="photo-placeholder"></div><small>09/12 08:41 上班</small></div>
    <div class="photo-card" data-id="p2"><div class="photo-placeholder"></div><small>10/03 14:22 超市</small></div>
    <div class="photo-card" data-id="p3"><div class="photo-placeholder"></div><small>11/15 17:55 浇花</small></div>
    <div class="photo-card" data-id="p4"><div class="photo-placeholder"></div><small>12/01 20:30 散步</small></div>
    <div class="photo-card" data-id="p5"><div class="photo-placeholder"></div><small>01/08 09:10 咖啡</small></div>
    <div class="photo-card" data-id="p6"><div class="photo-placeholder"></div><small>02/14 19:00 独自</small></div>
  </div>
  <div class="photo-detail" id="photoDetail"></div>
</section>

<!-- ── 通话记录 ── -->
<section class="calllog">
  <div class="call-header">通话记录</div>
  <div class="call-list">
    <div class="call-item">
      <div class="call-name">她</div>
      <div class="call-meta">
        <span class="call-type out">拨出</span>
        <span class="call-duration">0:00</span>
      </div>
      <small>03/15 03:12</small>
    </div>
  </div>
  <p class="call-note">凌晨三点拨出去的。响了一声就挂了。他只是想确认号码还没注销。</p>
</section>

<!-- ── 结语 ── -->
<section class="ending">
  <blockquote>"一年。整整一年。<br>你换号、搬家、剪头发——<br>你以为我找不到你？"</blockquote>
</section>

<footer>
  <div class="tags">${tg}</div>
</footer>
</main>`,

`*{box-sizing:border-box;margin:0}
html,body{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif;-webkit-font-smoothing:antialiased}
.device{max-width:680px;margin:0 auto;background:transparent}

/* ═══ 手机壳 ═══ */
.phone{margin:20px auto;max-width:375px;border-radius:40px;background:#0a0a0a;border:3px solid #1a1a1a;box-shadow:0 20px 60px rgba(0,0,0,.8),inset 0 0 0 1px #222;overflow:hidden;position:relative}
.notch{width:120px;height:28px;background:#0a0a0a;border-radius:0 0 16px 16px;margin:0 auto;position:relative;z-index:10}
.crack-overlay{position:absolute;inset:0;background:linear-gradient(135deg,transparent 40%,rgba(139,26,26,.03) 41%,transparent 42%),linear-gradient(225deg,transparent 60%,rgba(139,26,26,.02) 61%,transparent 62%);pointer-events:none;z-index:5}

/* ── 锁屏 ── */
.lockscreen{padding:20px 24px 30px;background:#050505;min-height:420px}
.ls-time{font:72px/1 ui-monospace,monospace;color:#c0c0c0;text-align:center;letter-spacing:.02em;margin-top:8px}
.ls-date{text-align:center;color:#4a3a3a;font:11px/1 ui-monospace,monospace;letter-spacing:.1em;margin-top:6px;font-style:italic}
.surveillance{margin-top:28px}
.surv-frame{background:#111;border:1px solid #1a1a1a;border-radius:8px;padding:14px;position:relative;overflow:hidden}
.surv-static{position:absolute;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(255,255,255,.01) 2px,rgba(255,255,255,.01) 4px);pointer-events:none}
.surv-overlay{display:flex;justify-content:space-between;align-items:center}
.surv-overlay small{color:#8b1a1a;font:9px ui-monospace,monospace;letter-spacing:.08em}
.surv-dot{width:6px;height:6px;border-radius:50%;background:#8b1a1a;animation:blink 2s ease-in-out infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.2}}
.surv-desc{color:#6a5a5a;font:12px/1.6 "Kaiti SC",serif;margin-top:12px;padding-top:12px;border-top:1px solid #1a1a1a}
.ls-hint{text-align:center;margin-top:24px;color:#3a2a2a;font:10px ui-monospace,monospace;letter-spacing:.12em}

/* ── 定位追踪 ── */
.tracker{background:#0a0a0a;padding:20px;border-top:1px solid #1a1a1a}
.tracker-header{display:flex;align-items:center;gap:8px}
.tracker-dot{width:6px;height:6px;border-radius:50%;background:#8b1a1a;animation:blink 1.5s ease-in-out infinite}
.tracker-header b{color:#6a5a5a;font:10px ui-monospace,monospace;letter-spacing:.1em}
.tracker-header small{color:#8b1a1a;font:9px ui-monospace,monospace;margin-left:auto}
.tracker-map{margin-top:16px;background:#111;border:1px solid #1a1a1a;border-radius:8px;padding:20px;position:relative;min-height:180px}
.map-grid{position:absolute;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 29px,rgba(139,26,26,.06) 29px,rgba(139,26,26,.06) 30px),repeating-linear-gradient(90deg,transparent,transparent 29px,rgba(139,26,26,.06) 29px,rgba(139,26,26,.06) 30px);pointer-events:none;border-radius:8px}
.map-pin{position:absolute;top:40%;left:55%;transform:translate(-50%,-50%)}
.pin-pulse{width:40px;height:40px;border-radius:50%;background:rgba(139,26,26,.1);border:1px solid rgba(139,26,26,.25);animation:pulse 3s ease-in-out infinite;position:absolute;top:-12px;left:-12px}
@keyframes pulse{0%,100%{transform:scale(1);opacity:.6}50%{transform:scale(1.6);opacity:0}}
.pin-label{background:#8b1a1a;color:#e0c0c0;font:10px ui-monospace,monospace;padding:3px 8px;border-radius:4px;white-space:nowrap;position:relative}
.map-info{margin-top:8px;display:grid;grid-template-columns:1fr 1fr;gap:6px}
.map-row{display:flex;gap:8px;align-items:baseline}
.map-row small{color:#4a3a3a;font:9px ui-monospace,monospace;width:36px}
.map-row span{color:#8a7a7a;font:11px ui-monospace,monospace}
.map-row .highlight{color:#8b1a1a;font-weight:600}
.tracker-note{color:#5a4a4a;font:11px/1.6 "Kaiti SC",serif;margin-top:14px;font-style:italic}

/* ═══ 暗拍相册 ═══ */
.gallery{padding:40px 24px;background:linear-gradient(170deg,#0e0a0a,#060404)}
.gallery-header small{color:#5a3a3a;font:10px ui-monospace,monospace;letter-spacing:.14em}
.gallery-header h2{margin-top:14px;color:#c0a8a8;font:24px/1.4 "Songti SC",serif;font-weight:400}
.gallery-header p{color:#6a5a5a;font:12px/1.6 "Kaiti SC",serif;margin-top:6px}
.photo-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:24px}
.photo-card{background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.04);border-radius:8px;padding:12px 8px;text-align:center;cursor:pointer;transition:.3s}
.photo-card:hover,.photo-card.on{background:rgba(139,26,26,.08);border-color:rgba(139,26,26,.2)}
.photo-placeholder{width:100%;aspect-ratio:3/4;background:linear-gradient(135deg,#1a1a1a,#111);border-radius:4px;margin-bottom:6px}
.photo-card small{color:#5a4a4a;font:9px ui-monospace,monospace}
.photo-detail{min-height:40px;margin-top:18px;color:#8a6a6a;font:13px/1.8 "Kaiti SC",serif;padding:0 4px}

/* ═══ 通话记录 ═══ */
.calllog{margin:0 auto;max-width:375px;background:#0a0a0a;border-top:1px solid #1a1a1a}
.call-header{padding:14px 18px;color:#6a5a5a;font:13px/1 ui-monospace,monospace;border-bottom:1px solid #1a1a1a}
.call-list{padding:0 18px}
.call-item{display:flex;align-items:center;gap:12px;padding:14px 0;border-bottom:1px solid #111}
.call-name{color:#c0a8a8;font-size:14px;font-weight:500;flex:1}
.call-meta{display:flex;gap:8px;align-items:center}
.call-type{font:9px ui-monospace,monospace;padding:2px 6px;border-radius:3px}
.call-type.out{color:#8b1a1a;background:rgba(139,26,26,.1)}
.call-duration{color:#5a4a4a;font:11px ui-monospace,monospace}
.call-item small{color:#3a2a2a;font:10px ui-monospace,monospace}
.call-note{padding:14px 18px;color:#5a4a4a;font:11px/1.6 "Kaiti SC",serif;font-style:italic}

/* ═══ 结语 ═══ */
.ending{padding:40px 24px;text-align:center}
.ending blockquote{color:#c0a8a8;font:18px/1.7 "Songti SC",serif}

/* ═══ footer ═══ */
footer{padding:20px 24px 38px;background:transparent}
.tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.tags span{color:#5a3a3a;font-size:10px;font-family:ui-monospace,monospace;padding:4px 10px;border:1px solid rgba(255,255,255,.04);border-radius:20px}`,

`var photoData={
  p1:'八点四十一分。她从地铁口出来，左手拎着早餐袋，低头看手机。新换了一件灰色大衣。走路的姿势没变。',
  p2:'超市里。她在水果区挑了很久的草莓。最后放下了——大概觉得贵。他记住了这件事。',
  p3:'阳台。她在浇花。栀子花。以前他送过她一盆，不知道是不是同一种。',
  p4:'散步。一个人。戴了耳机。走到街角停下来看了一会儿流浪猫。他在五十米外的车里。',
  p5:'咖啡馆靠窗的位置。她点了冰美式。以前她只喝热的——口味变了。他不喜欢这种变化。',
  p6:'情人节。独自一人。在便利店买了一个三明治。回家的路上走得很慢。他跟了全程。'
};
document.querySelectorAll('.photo-card').forEach(function(c){c.onclick=function(){
  document.querySelectorAll('.photo-card').forEach(function(x){x.classList.remove('on')});
  c.classList.add('on');
  document.getElementById('photoDetail').textContent=photoData[c.dataset.id]||'';
}});`, 2800)
}

/* ═══════════════════════════════════════════
   纪言 · 通知中心
   媒介：iPhone通知中心 + 设置面板 + 叛逆之夜
   ═══════════════════════════════════════════ */
export function JiYanProfile({ profile }: Props) {
  const n = e(profile.display_name || '纪言'), tg = tagHtml(profile)
  return frame(profile, '通知中心', `
<main class="device">
<div class="phone">
  <div class="notch"></div>

  <!-- ── 通知中心 ── -->
  <section class="noti-center">
    <div class="nc-header">
      <div class="nc-time">22:07</div>
      <div class="nc-date">周六</div>
    </div>
    <div class="nc-stack">
      <div class="nc-item">
        <div class="nc-app">查找</div>
        <div class="nc-body">
          <b>${n} 与你共享了位置</b>
          <small>持续中 · 23个月</small>
        </div>
      </div>
      <div class="nc-item">
        <div class="nc-app">查找</div>
        <div class="nc-body">
          <b>${n} 将你的位置标记为"安全"</b>
          <small>今天 18:42</small>
        </div>
      </div>
      <div class="nc-item">
        <div class="nc-app">备忘录</div>
        <div class="nc-body">
          <b>${n} 编辑了共享备忘录"规矩"</b>
          <small>今天 16:20 · 第37次编辑</small>
        </div>
      </div>
      <div class="nc-item missed">
        <div class="nc-app">电话</div>
        <div class="nc-body">
          <b>未接来电 (3)</b>
          <small>22:01, 22:03, 22:05</small>
        </div>
      </div>
      <div class="nc-item missed">
        <div class="nc-app">短信</div>
        <div class="nc-body">
          <b>未读消息 (12)</b>
          <small>最新：你在哪？</small>
        </div>
      </div>
    </div>
  </section>

  <!-- ── 设置 / 规矩 ── -->
  <section class="rules-panel">
    <div class="rules-header">
      <small>SETTINGS</small>
      <h3>他的规矩</h3>
      <p>两年里逐条添加。每一条都是"为你好"。</p>
    </div>
    <div class="rules-list">
      <div class="rule-row" data-r="ice">
        <div class="rule-info">
          <b>冰饮料</b>
          <small>例假刚走不能喝冰的</small>
        </div>
        <div class="toggle off"><div class="toggle-knob"></div></div>
      </div>
      <div class="rule-row" data-r="skirt">
        <div class="rule-info">
          <b>裙子过膝</b>
          <small>太短了招人看</small>
        </div>
        <div class="toggle on"><div class="toggle-knob"></div></div>
      </div>
      <div class="rule-row" data-r="bar">
        <div class="rule-info">
          <b>酒吧 / 夜店</b>
          <small>鱼龙混杂不安全</small>
        </div>
        <div class="toggle off"><div class="toggle-knob"></div></div>
      </div>
      <div class="rule-row" data-r="curfew">
        <div class="rule-info">
          <b>22:00 前到家</b>
          <small>晚归不安全</small>
        </div>
        <div class="toggle on"><div class="toggle-knob"></div></div>
      </div>
      <div class="rule-row" data-r="lock">
        <div class="rule-info">
          <b>手机无锁屏</b>
          <small>你又不是有什么不能让我看的</small>
        </div>
        <div class="toggle on"><div class="toggle-knob"></div></div>
      </div>
    </div>
    <div class="rule-reaction" id="ruleReaction"></div>
  </section>
</div>

<!-- ── 叛逆之夜 ── -->
<section class="rebellion">
  <div class="rebel-header">
    <small>DAY 7 / 分手后第七天</small>
    <h2>她穿上了那条裙子</h2>
  </div>
  <div class="rebel-scene">
    <div class="dress-card">
      <div class="dress-placeholder"></div>
      <p>黑色。短的。<br>他说过"你敢穿这条出门我跟你没完"的那条。</p>
    </div>
    <div class="location-ping">
      <div class="ping-dot"></div>
      <span>VELVET 酒吧</span>
      <small>23:14</small>
    </div>
  </div>
</section>

<!-- ── 他到了 ── -->
<section class="arrival">
  <div class="arrival-scene">
    <p class="arrival-text">吧台三步之外。灯光和阴影的交界线上。</p>
    <div class="arrival-bubble">
      <div class="arr-avatar">言</div>
      <div class="arr-msg">穿这条来的？</div>
    </div>
    <p class="arrival-sub">他笑了一下。没有温度。</p>
    <div class="arrival-bubble">
      <div class="arr-avatar">言</div>
      <div class="arr-msg last">我该怎么罚你呢。</div>
    </div>
  </div>
</section>

<footer>
  <div class="tags">${tg}</div>
</footer>
</main>`,

`*{box-sizing:border-box;margin:0}
html,body{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif;-webkit-font-smoothing:antialiased}
.device{max-width:680px;margin:0 auto;background:transparent}

/* ═══ 手机壳 ═══ */
.phone{margin:20px auto;max-width:375px;border-radius:40px;background:#1c1c1e;border:3px solid #2a2a2c;box-shadow:0 20px 60px rgba(0,0,0,.6),inset 0 0 0 1px #333;overflow:hidden;position:relative}
.notch{width:120px;height:28px;background:#1c1c1e;border-radius:0 0 16px 16px;margin:0 auto;position:relative;z-index:10}

/* ── 通知中心 ── */
.noti-center{padding:12px 16px 24px;background:rgba(28,28,30,.95)}
.nc-header{text-align:center;padding:8px 0 16px}
.nc-time{font:42px/1 ui-monospace,monospace;color:#e0e0e4;letter-spacing:.02em}
.nc-date{color:#8e8e93;font:11px/1 ui-monospace,monospace;margin-top:4px}
.nc-stack{display:flex;flex-direction:column;gap:8px}
.nc-item{background:rgba(255,255,255,.06);backdrop-filter:blur(16px);border-radius:14px;padding:11px 14px;display:flex;gap:10px;align-items:flex-start;border:1px solid rgba(255,255,255,.04)}
.nc-item.missed{border-color:rgba(200,100,100,.15)}
.nc-app{width:30px;height:30px;border-radius:7px;background:rgba(142,142,147,.12);color:#8e8e93;font-size:8px;display:grid;place-items:center;flex-shrink:0}
.nc-item.missed .nc-app{background:rgba(200,100,100,.12);color:#c86464}
.nc-body b{color:#e0e0e4;font-size:11px;font-weight:500;display:block}
.nc-body small{color:#636366;font-size:10px;display:block;margin-top:2px}

/* ── 规矩面板 ── */
.rules-panel{background:#1c1c1e;padding:20px 16px}
.rules-header{padding-bottom:14px;border-bottom:1px solid rgba(255,255,255,.06)}
.rules-header small{color:#636366;font:9px ui-monospace,monospace;letter-spacing:.12em}
.rules-header h3{color:#e0e0e4;font-size:15px;font-weight:600;margin-top:6px}
.rules-header p{color:#8e8e93;font-size:11px;margin-top:4px}
.rules-list{margin-top:8px}
.rule-row{display:flex;align-items:center;justify-content:space-between;padding:13px 0;border-bottom:1px solid rgba(255,255,255,.04);cursor:pointer}
.rule-info b{color:#e0e0e4;font-size:13px;font-weight:500;display:block}
.rule-info small{color:#636366;font-size:10px;display:block;margin-top:2px}
.toggle{width:46px;height:28px;border-radius:14px;position:relative;flex-shrink:0;transition:.3s}
.toggle.on{background:#34c759}
.toggle.off{background:#48484a}
.toggle-knob{width:24px;height:24px;border-radius:50%;background:#fff;position:absolute;top:2px;transition:.3s;box-shadow:0 1px 3px rgba(0,0,0,.3)}
.toggle.on .toggle-knob{left:20px}
.toggle.off .toggle-knob{left:2px}
.rule-reaction{min-height:36px;padding:12px 0 4px;color:#c86464;font:12px/1.6 "Kaiti SC",serif;font-style:italic}

/* ═══ 叛逆之夜 ═══ */
.rebellion{padding:40px 24px;background:linear-gradient(170deg,#1a1820,#0e0c14)}
.rebel-header small{color:#636366;font:10px ui-monospace,monospace;letter-spacing:.14em}
.rebel-header h2{margin-top:14px;color:#e0d8e4;font:24px/1.4 "Songti SC",serif;font-weight:400}
.rebel-scene{margin-top:24px;display:flex;flex-direction:column;gap:20px}
.dress-card{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.05);border-radius:12px;padding:20px;text-align:center}
.dress-placeholder{width:120px;height:180px;margin:0 auto;background:linear-gradient(170deg,#1a1a1a,#0e0e0e);border-radius:8px;border:1px solid #2a2a2a}
.dress-card p{color:#8a7e90;font:12px/1.7 "Kaiti SC",serif;margin-top:14px}
.location-ping{display:flex;align-items:center;gap:10px;padding:12px 16px;background:rgba(200,100,200,.06);border:1px solid rgba(200,100,200,.12);border-radius:10px}
.ping-dot{width:8px;height:8px;border-radius:50%;background:#c864c8;animation:blink 1.5s ease-in-out infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.2}}
.location-ping span{color:#c8a0c8;font:12px ui-monospace,monospace}
.location-ping small{color:#636366;font:10px ui-monospace,monospace;margin-left:auto}

/* ═══ 他到了 ═══ */
.arrival{padding:40px 24px;background:linear-gradient(170deg,#14121a,#0a0810)}
.arrival-scene{max-width:320px;margin:0 auto}
.arrival-text{color:#8a7e90;font:13px/1.7 "Kaiti SC",serif;text-align:center;margin-bottom:20px}
.arrival-bubble{display:flex;gap:8px;align-items:flex-start;margin-bottom:14px}
.arr-avatar{width:34px;height:34px;border-radius:4px;background:rgba(200,200,200,.08);color:#a0a0a4;font-size:13px;display:grid;place-items:center;flex-shrink:0}
.arr-msg{max-width:72%;padding:9px 12px;border-radius:4px 14px 14px 14px;background:rgba(255,255,255,.06);color:#e0d8e4;font-size:13px;line-height:1.6}
.arr-msg.last{background:rgba(200,100,100,.1);color:#e0c0c0}
.arrival-sub{color:#636366;font:11px/1.6 "Kaiti SC",serif;text-align:center;margin:8px 0 14px;font-style:italic}

/* ═══ footer ═══ */
footer{padding:20px 24px 38px;background:transparent}
.tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.tags span{color:#636366;font-size:10px;font-family:ui-monospace,monospace;padding:4px 10px;border:1px solid rgba(255,255,255,.04);border-radius:20px}`,

`var ruleReactions={
  ice:'"你例假刚走，不能喝冰的。""我自己知道。""你不知道。"——他管了你两年的冰饮料。连夏天也不例外。',
  skirt:'"这条裙子太短了。""就到膝盖上面一点而已。""换一条。"他的语气不是商量。从来不是。',
  bar:'"那种地方鱼龙混杂。"你说你就是去坐坐。他说"坐坐也不行"。你没去。直到分手后第七天。',
  curfew:'你有一次十点十五分到家。他坐在门口台阶上等你。没有生气的样子。只是说"以后别这样了"。然后把你的定位又确认了一遍。',
  lock:'"你又不是有什么不能让我看的。"你没设密码。不是因为没什么好藏，是因为上次你设了密码，他一整晚没睡，坐在客厅盯着你的手机看。'
};
document.querySelectorAll('.rule-row').forEach(function(r){r.onclick=function(){
  document.getElementById('ruleReaction').textContent=ruleReactions[r.dataset.r]||'';
}});`, 2600)
}

/* ═══════════════════════════════════════════
   萧凛 · 安保简报
   媒介：安保加密设备 — 日报 + 档案 + 事件 + 保险柜
   ═══════════════════════════════════════════ */
export function XiaoLinProfile({ profile }: Props) {
  const n = e(profile.display_name || '萧凛'), tg = tagHtml(profile)
  return frame(profile, '安保简报', `
<main class="device">

<!-- ── 安保简报头 ── -->
<section class="briefing-header">
  <div class="bh-top">
    <small>XIAO PRIVATE SECURITY</small>
    <span class="bh-class">CLASSIFIED</span>
  </div>
  <div class="bh-title">DAILY REPORT</div>
  <div class="bh-meta">
    <span>DATE: 2024-11-15</span>
    <span>AGENT: LI-07</span>
    <span>AUTH: S-LEVEL</span>
  </div>
  <div class="bh-line"></div>
</section>

<!-- ── 对象档案 ── -->
<section class="dossier">
  <div class="dos-header">
    <small>SUBJECT DOSSIER</small>
  </div>
  <div class="dos-card">
    <div class="dos-photo">
      <svg viewBox="0 0 60 60" width="60" height="60" fill="none">
        <circle cx="30" cy="22" r="12" stroke="#c9a84c" stroke-width="1"/>
        <path d="M10 55c0-11 9-20 20-20s20 9 20 20" stroke="#c9a84c" stroke-width="1"/>
      </svg>
    </div>
    <div class="dos-info">
      <div class="dos-row"><small>CODENAME</small><b>丫头</b></div>
      <div class="dos-row"><small>STATUS</small><span class="status safe">SAFE</span></div>
      <div class="dos-row"><small>THREAT</small><span class="status low">LOW</span></div>
      <div class="dos-row"><small>DETAIL</small><span>24h 随行安保 · 司机配备</span></div>
    </div>
  </div>
</section>

<!-- ── 活动日志 ── -->
<section class="activity-log">
  <div class="log-header">
    <small>ACTIVITY LOG</small>
    <span>2024-11-15</span>
  </div>
  <div class="log-table">
    <div class="log-row"><div class="log-time">09:12</div><div class="log-event">出门。目的地：商场。司机随行。</div><div class="log-status ok">NORMAL</div></div>
    <div class="log-row"><div class="log-time">13:40</div><div class="log-event">午餐。独自。西餐厅A3。无异常。</div><div class="log-status ok">NORMAL</div></div>
    <div class="log-row highlight"><div class="log-time">15:22</div><div class="log-event">踹了陈家少爷的车门。</div><div class="log-status flag">INCIDENT</div></div>
    <div class="log-row"><div class="log-time">15:24</div><div class="log-event">司机已录像。证据保全完毕。</div><div class="log-status ok">RESOLVED</div></div>
    <div class="log-row"><div class="log-time">17:55</div><div class="log-event">回家。情绪良好。零食消耗：薯片x1。</div><div class="log-status ok">NORMAL</div></div>
  </div>
</section>

<!-- ── 事件报告 ── -->
<section class="incident-report">
  <div class="ir-header">
    <small>INCIDENT REPORT</small>
    <span class="ir-id">IR-2024-1115-001</span>
  </div>
  <div class="ir-card">
    <div class="ir-row"><small>EVENT</small><span>陈家公子投诉（电话40分钟）</span></div>
    <div class="ir-row"><small>CAUSE</small><span>车辆停放挡住对象出行路径</span></div>
    <div class="ir-row"><small>ACTION</small><span>法务已处理。陈家已撤诉。</span></div>
    <div class="ir-row note"><small>NOTE</small><span>"下次踹之前先让司机录像。方便我的律师取证。"<br>—— ${n}</span></div>
  </div>
</section>

<!-- ── 保险柜清单 ── -->
<section class="safe-section">
  <div class="safe-header">
    <small>SAFE CONTENTS / 保险柜</small>
    <h2>密码只有他知道</h2>
    <p>里面没有商业机密。</p>
  </div>
  <div class="safe-list">
    <div class="safe-item" data-s="s1"><div class="safe-tab" style="background:#c9a84c"></div><b>体检报告 2019</b><small>6岁。第一年。</small></div>
    <div class="safe-item" data-s="s2"><div class="safe-tab" style="background:#a0c8a0"></div><b>体检报告 2020</b><small>7岁。蛀牙两颗。</small></div>
    <div class="safe-item" data-s="s3"><div class="safe-tab" style="background:#80a8d0"></div><b>体检报告 2021</b><small>8岁。身高窜了8cm。</small></div>
    <div class="safe-item" data-s="s4"><div class="safe-tab" style="background:#d0a080"></div><b>体检报告 2022</b><small>9岁。一切正常。</small></div>
    <div class="safe-item" data-s="s5"><div class="safe-tab" style="background:#c080a0"></div><b>体检报告 2023</b><small>10岁。过敏源清单已更新。</small></div>
    <div class="safe-item" data-s="s6"><div class="safe-tab" style="background:#c9a84c"></div><b>体检报告 2024</b><small>11岁。批注：需复查视力。</small></div>
  </div>
  <div class="safe-detail" id="safeDetail"></div>
</section>

<!-- ── 加密壁纸 ── -->
<section class="wallpaper-section">
  <div class="wp-card" id="wpCard">
    <div class="wp-lock">
      <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#c9a84c" stroke-width="1.5">
        <rect x="3" y="11" width="18" height="11" rx="2"/>
        <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
      </svg>
      <small>PERSONAL / ENCRYPTED</small>
      <button id="wpReveal">DECRYPT</button>
    </div>
    <div class="wp-content" id="wpContent">
      <p>手机壁纸。她上周趴在客厅沙发上睡着的照片。嘴角挂着薯片碎屑。偷拍的。</p>
      <small>他每天看十二次。</small>
    </div>
  </div>
</section>

<!-- ── 结语 ── -->
<section class="ending">
  <blockquote>"别人怎么说你我不关心。<br>但在我面前，你永远是对的。"</blockquote>
  <p class="ending-sub">—— 全城都知道：<br>动萧凛的女儿，和动萧凛本人，后果一样。</p>
</section>

<footer>
  <div class="tags">${tg}</div>
</footer>
</main>`,

`*{box-sizing:border-box;margin:0}
html,body{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif;-webkit-font-smoothing:antialiased}
.device{max-width:680px;margin:0 auto;background:transparent}

/* ═══ 简报头 ═══ */
.briefing-header{padding:28px 24px 20px;background:linear-gradient(170deg,#0d1117,#0a0e14)}
.bh-top{display:flex;justify-content:space-between;align-items:center}
.bh-top small{color:#4a5a6a;font:9px ui-monospace,monospace;letter-spacing:.14em}
.bh-class{color:#c9a84c;font:9px ui-monospace,monospace;letter-spacing:.12em;padding:3px 8px;border:1px solid rgba(201,168,76,.25);border-radius:3px}
.bh-title{margin-top:14px;color:#c8d4e0;font:28px ui-monospace,monospace;font-weight:700;letter-spacing:.06em}
.bh-meta{margin-top:10px;display:flex;gap:16px;flex-wrap:wrap}
.bh-meta span{color:#4a5a6a;font:9px ui-monospace,monospace}
.bh-line{height:1px;background:linear-gradient(90deg,rgba(201,168,76,.3),transparent);margin-top:16px}

/* ═══ 档案 ═══ */
.dossier{padding:24px;background:#0d1117}
.dos-header small{color:#4a5a6a;font:9px ui-monospace,monospace;letter-spacing:.12em}
.dos-card{margin-top:14px;display:flex;gap:20px;align-items:flex-start;background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.04);border-radius:12px;padding:18px}
.dos-photo{width:60px;height:60px;border-radius:8px;background:rgba(201,168,76,.06);display:grid;place-items:center;flex-shrink:0}
.dos-info{flex:1;display:flex;flex-direction:column;gap:8px}
.dos-row{display:flex;gap:10px;align-items:baseline}
.dos-row small{color:#4a5a6a;font:8px ui-monospace,monospace;width:70px;flex-shrink:0}
.dos-row b{color:#e0d8c8;font-size:14px;font-weight:500}
.dos-row span{color:#8a9aaa;font-size:11px}
.status{font:9px ui-monospace,monospace;padding:2px 8px;border-radius:3px}
.status.safe{color:#4aaa4a;background:rgba(74,170,74,.1)}
.status.low{color:#c9a84c;background:rgba(201,168,76,.1)}

/* ═══ 活动日志 ═══ */
.activity-log{padding:24px;background:#0d1117;border-top:1px solid rgba(255,255,255,.04)}
.log-header{display:flex;justify-content:space-between;align-items:center}
.log-header small{color:#4a5a6a;font:9px ui-monospace,monospace;letter-spacing:.12em}
.log-header span{color:#4a5a6a;font:9px ui-monospace,monospace}
.log-table{margin-top:14px;display:flex;flex-direction:column;gap:0}
.log-row{display:flex;gap:12px;align-items:center;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.03)}
.log-row.highlight{background:rgba(201,168,76,.04);margin:0 -12px;padding:10px 12px;border-radius:6px}
.log-time{color:#4a5a6a;font:10px ui-monospace,monospace;width:40px;flex-shrink:0}
.log-event{color:#a0b0c0;font-size:11px;flex:1;line-height:1.5}
.log-status{font:8px ui-monospace,monospace;padding:2px 6px;border-radius:3px;flex-shrink:0}
.log-status.ok{color:#4a8a6a;background:rgba(74,138,106,.08)}
.log-status.flag{color:#c9a84c;background:rgba(201,168,76,.1)}

/* ═══ 事件报告 ═══ */
.incident-report{padding:24px;background:#0d1117;border-top:1px solid rgba(255,255,255,.04)}
.ir-header{display:flex;justify-content:space-between;align-items:center}
.ir-header small{color:#4a5a6a;font:9px ui-monospace,monospace;letter-spacing:.12em}
.ir-id{color:#4a5a6a;font:9px ui-monospace,monospace}
.ir-card{margin-top:14px;background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.04);border-radius:10px;padding:16px}
.ir-row{display:flex;gap:12px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.03);align-items:baseline}
.ir-row:last-child{border-bottom:none}
.ir-row small{color:#4a5a6a;font:8px ui-monospace,monospace;width:56px;flex-shrink:0}
.ir-row span{color:#a0b0c0;font-size:11px;line-height:1.5}
.ir-row.note span{color:#c9a84c;font:12px/1.6 "Kaiti SC",serif}

/* ═══ 保险柜 ═══ */
.safe-section{padding:40px 24px;background:linear-gradient(170deg,#10141a,#0a0e14)}
.safe-header small{color:#4a5a6a;font:10px ui-monospace,monospace;letter-spacing:.14em}
.safe-header h2{margin-top:14px;color:#e0d8c8;font:22px "Songti SC",serif;font-weight:400}
.safe-header p{color:#6a7a8a;font:12px "Kaiti SC",serif;margin-top:6px}
.safe-list{margin-top:24px;display:flex;flex-direction:column;gap:6px}
.safe-item{display:flex;gap:12px;align-items:center;padding:10px 12px;background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.03);border-radius:8px;cursor:pointer;transition:.2s}
.safe-item:hover,.safe-item.on{background:rgba(201,168,76,.06);border-color:rgba(201,168,76,.15)}
.safe-tab{width:4px;height:24px;border-radius:2px;flex-shrink:0}
.safe-item b{color:#c8d0d8;font-size:12px;font-weight:500}
.safe-item small{color:#5a6a7a;font-size:10px;margin-left:auto}
.safe-detail{min-height:36px;margin-top:16px;color:#c9a84c;font:13px/1.7 "Kaiti SC",serif}

/* ═══ 加密壁纸 ═══ */
.wallpaper-section{padding:28px 24px;background:#0d1117}
.wp-card{background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.04);border-radius:14px;padding:24px;text-align:center;position:relative;overflow:hidden}
.wp-lock{display:flex;flex-direction:column;align-items:center;gap:10px}
.wp-lock small{color:#4a5a6a;font:10px ui-monospace,monospace;letter-spacing:.12em}
.wp-lock button{border:1px solid rgba(201,168,76,.3);background:rgba(201,168,76,.08);color:#c9a84c;font:10px ui-monospace,monospace;padding:6px 20px;border-radius:4px;cursor:pointer;margin-top:4px;letter-spacing:.08em}
.wp-content{display:none;padding-top:16px}
.wp-content.show{display:block}
.wp-content p{color:#c8c0b0;font:14px/1.7 "Kaiti SC",serif}
.wp-content small{color:#6a7a8a;font:11px "Kaiti SC",serif;display:block;margin-top:8px}

/* ═══ 结语 ═══ */
.ending{padding:40px 24px;text-align:center;background:linear-gradient(170deg,#0d1117,#080c10)}
.ending blockquote{color:#e0d8c8;font:18px/1.7 "Songti SC",serif}
.ending-sub{color:#6a7a8a;font:13px/1.7 "Kaiti SC",serif;margin-top:18px}

/* ═══ footer ═══ */
footer{padding:20px 24px 38px;background:transparent}
.tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.tags span{color:#4a5a6a;font-size:10px;font-family:ui-monospace,monospace;padding:4px 10px;border:1px solid rgba(255,255,255,.04);border-radius:20px}`,

`var safeData={
  s1:'第一年。她刚被带回来，怕生，什么都不敢吃。他让厨房每天换菜单，直到找到她肯吃的东西。体检报告他用荧光笔标了重点：体重偏轻。',
  s2:'两颗蛀牙。她怕疼不肯去看牙医。他在诊所门口蹲了一个小时哄她，最后说"你去了我给你买三个冰淇淋"。牙医说这是他见过最紧张的家长。',
  s3:'一年长了八厘米。他在书房门框上给她量的身高刻度，每一条线旁边都标了日期。那些刻度他从来没有让人刷掉。',
  s4:'一切正常。他在"一切正常"四个字下面画了一条线，旁边写了"好"。一个字。但那个字的笔迹明显比其他地方用力。',
  s5:'过敏源清单更新了。新增了芒果。他当天让厨房把所有含芒果的食材清了出去，安保人员的备忘录里也加了这一条。',
  s6:'视力下降。他批注："需复查。约最好的眼科。不要告诉她——她会不肯去。"他自己的年度体检从来没做过。'
};
document.querySelectorAll('.safe-item').forEach(function(c){c.onclick=function(){
  document.querySelectorAll('.safe-item').forEach(function(x){x.classList.remove('on')});
  c.classList.add('on');
  document.getElementById('safeDetail').textContent=safeData[c.dataset.s]||'';
}});
document.getElementById('wpReveal').onclick=function(){
  var el=document.getElementById('wpContent');
  el.classList.toggle('show');
  this.textContent=el.classList.contains('show')?'ENCRYPT':'DECRYPT';
};`, 2800)
}
/* ═══════════════════════════════════════════
   裴寂行 · 婚前协议
   媒介：一份被批注过的合同 — 条款 + 附加规则 + 隐藏真相
   ═══════════════════════════════════════════ */
export function PeiJixingProfile({ profile }: Props) {
  const n = e(profile.display_name || '裴寂行'), tg = tagHtml(profile)
  return frame(profile, '婚前协议', `
<main class="contract">

<!-- ── 合同封面 ── -->
<section class="cover">
  <div class="cover-border">
    <div class="cover-label">寂行资本 · 法务部</div>
    <div class="cover-no">编号：PJX-2024-0001</div>
    <h1>婚前协议书</h1>
    <div class="cover-sub">甲方：${n}<br>乙方：＿＿＿＿（你）</div>
    <div class="seal">
      <svg viewBox="0 0 100 100" width="90" height="90">
        <circle cx="50" cy="50" r="45" fill="none" stroke="#c44" stroke-width="3"/>
        <text x="50" y="38" text-anchor="middle" fill="#c44" font-size="11" font-family="Songti SC,serif">裴氏集团</text>
        <text x="50" y="55" text-anchor="middle" fill="#c44" font-size="16" font-weight="bold" font-family="Songti SC,serif">专用章</text>
        <text x="50" y="70" text-anchor="middle" fill="#c44" font-size="8" font-family="Songti SC,serif">CONFIDENTIAL</text>
      </svg>
    </div>
    <div class="cover-date">签署日期：婚礼前夜</div>
  </div>
</section>

<!-- ── 条款正文 ── -->
<section class="terms">
  <div class="terms-head">
    <small>SECTION I / 协议条款</small>
    <p class="terms-note">点击条款查看批注</p>
  </div>

  <div class="clause" data-c="1">
    <div class="clause-num">第一条</div>
    <div class="clause-text">双方为名义夫妻，各有各的生活。互不干涉对方私人事务。</div>
    <div class="clause-anno" id="a1">他在签字时停顿了两秒。钢笔尖在纸上留下了一个多余的墨点。</div>
  </div>

  <div class="clause" data-c="2">
    <div class="clause-num">第二条</div>
    <div class="clause-text">同住一套房产。甲方使用主卧，乙方使用客卧。书房为甲方专属区域。</div>
    <div class="clause-anno" id="a2">书房的灯从未在凌晨两点前熄灭。他在等什么？门缝下的光知道。</div>
  </div>

  <div class="clause" data-c="3">
    <div class="clause-num">第三条</div>
    <div class="clause-text">对外保持正常夫妻形象。不需要演得太好，别太差就行。</div>
    <div class="clause-anno" id="a3">他把手搭在你腰上时，掌心温度比脸上的表情高了六度。</div>
  </div>

  <div class="clause" data-c="4">
    <div class="clause-num">第四条</div>
    <div class="clause-text">本协议有效期至双方任一方提出解除为止。</div>
    <div class="clause-anno" id="a4">"解除"两个字他写了三遍才写对。每一遍笔画都更用力。</div>
  </div>

  <div class="sign-line">
    <div class="sign-box">
      <small>甲方签字</small>
      <div class="sig">裴寂行</div>
    </div>
    <div class="sign-box">
      <small>乙方签字</small>
      <div class="sig empty">等你落笔</div>
    </div>
  </div>
</section>

<!-- ── 补充条款（后来加的规矩） ── -->
<section class="addendum">
  <small>ADDENDUM / 他后来加的规矩</small>
  <h2>笼子是一条一条焊上的</h2>
  <div class="sticky-wall">
    <div class="sticky s1" data-s="1">
      <div class="sticky-front">
        <b>第一个月</b>
        <p>外出跟司机说一声</p>
      </div>
      <div class="sticky-back">理由是"安全考虑"。司机的汇报对象只有他。</div>
    </div>
    <div class="sticky s2" data-s="2">
      <div class="sticky-front">
        <b>第二个月</b>
        <p>裙子别太短，拍到不好解释</p>
      </div>
      <div class="sticky-back">你的衣柜被换了一批新衣服。件件好看，件件过膝。</div>
    </div>
    <div class="sticky s3" data-s="3">
      <div class="sticky-front">
        <b>第三个月</b>
        <p>晚上十点之前回家</p>
      </div>
      <div class="sticky-back">你的通讯录多了三个号码，全是他的人。你还觉得这是安全措施吗？</div>
    </div>
  </div>
</section>

<!-- ── 保险柜里的东西 ── -->
<section class="vault">
  <small>CLASSIFIED / 书房保险柜 · 密码未知</small>
  <h2>合同以外的证据</h2>
  <div class="vault-item">
    <div class="vault-label">文件 A</div>
    <p>你父亲公司的困境——是第三方制造的。他在你签协议之前就已经解决了资金问题。</p>
    <p class="vault-hl">他完全可以不娶你。但他选择了这条路。</p>
  </div>
  <div class="vault-item">
    <div class="vault-label">文件 B</div>
    <p>你每次外出的安保人员，他亲自筛选。每个人都有你的过敏源清单和常去医院的急诊号码。</p>
  </div>
  <div class="vault-item">
    <div class="vault-label">文件 C</div>
    <button id="reveal">解锁相框 →</button>
    <div class="vault-photo" id="photo">
      <p>一个相框。背面朝外放着。翻过来——</p>
      <p class="vault-hl">领证那天。你穿白衬衫。这张照片是让司机偷拍的。</p>
      <p class="vault-note">他每天看。</p>
    </div>
  </div>
</section>

<!-- ── 收尾 ── -->
<section class="ending">
  <blockquote>"你父亲的公司有我需要的东西。<br>你是最快的路径。"<br><br><em>——这是合同上写的版本。<br>真实版本他至今没有说出口。</em></blockquote>
</section>

<footer>
  <div class="tags">${tg}</div>
</footer>
</main>`,

`*{box-sizing:border-box;margin:0}
html,body{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif;-webkit-font-smoothing:antialiased}
.contract{max-width:680px;margin:0 auto;background:transparent}

/* ═══ 封面 ═══ */
.cover{padding:32px 24px}
.cover-border{border:2px solid #c8bfaa;padding:40px 28px;position:relative;background:linear-gradient(170deg,#f5f0e6,#ebe5d6)}
.cover-label{color:#8a7e6e;font:10px ui-monospace,monospace;letter-spacing:.14em}
.cover-no{color:#a89888;font:9px ui-monospace,monospace;margin-top:4px}
.cover h1{margin-top:28px;font:36px "Songti SC",serif;font-weight:400;color:#2a2420;letter-spacing:.06em}
.cover-sub{margin-top:18px;color:#5a4e40;font:14px/1.8 "Kaiti SC",serif}
.seal{position:absolute;right:28px;bottom:30px;opacity:.75;animation:stamp .8s ease-out}
@keyframes stamp{0%{transform:scale(1.5) rotate(-10deg);opacity:0}70%{transform:scale(.95) rotate(2deg);opacity:.9}100%{transform:scale(1) rotate(0deg);opacity:.75}}
.cover-date{margin-top:28px;color:#8a7e6e;font:11px ui-monospace,monospace;text-align:right}

/* ═══ 条款 ═══ */
.terms{padding:32px 24px;background:linear-gradient(180deg,#f5f0e6 0%,#efe9db 100%)}
.terms-head small{color:#8a7e6e;font:10px ui-monospace,monospace;letter-spacing:.14em}
.terms-note{color:#b0a090;font:10px "Kaiti SC",serif;margin-top:4px;font-style:italic}
.clause{padding:18px 0;border-bottom:1px solid #ddd5c8;cursor:pointer;position:relative}
.clause:hover{background:rgba(196,68,68,.03)}
.clause-num{color:#c44;font:11px ui-monospace,monospace;font-weight:600}
.clause-text{margin-top:6px;color:#3a3028;font:14px/1.8 "Songti SC",serif}
.clause-anno{display:none;margin-top:10px;padding:10px 14px;background:rgba(196,68,68,.04);border-left:2px solid #c44;color:#8b4a3a;font:12px/1.7 "Kaiti SC",serif;font-style:italic;animation:fadeSlide .3s ease}
.clause-anno.show{display:block}
@keyframes fadeSlide{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:translateY(0)}}
.sign-line{display:flex;gap:20px;margin-top:28px;padding-top:20px;border-top:1px solid #ddd5c8}
.sign-box{flex:1;text-align:center}
.sign-box small{color:#8a7e6e;font:10px ui-monospace,monospace}
.sig{margin-top:8px;font:20px "Kaiti SC",serif;color:#2a2420}
.sig.empty{color:#c8bfaa;font-style:italic;font-size:13px}

/* ═══ 补充条款 ═══ */
.addendum{padding:40px 24px;background:linear-gradient(170deg,#1e1a14,#120e0a)}
.addendum small{color:#8a7860;font:10px ui-monospace,monospace;letter-spacing:.14em}
.addendum h2{margin-top:14px;color:#e0d8c8;font:24px "Songti SC",serif;font-weight:400}
.sticky-wall{display:flex;flex-direction:column;gap:14px;margin-top:24px}
.sticky{background:rgba(245,240,230,.06);border:1px solid rgba(245,240,230,.08);border-radius:4px;cursor:pointer;overflow:hidden;transition:.3s}
.sticky:hover{border-color:rgba(196,68,68,.2)}
.s1{border-left:3px solid #c9a84c}
.s2{border-left:3px solid #c47a3a}
.s3{border-left:3px solid #c44}
.sticky-front{padding:14px 16px}
.sticky-front b{color:#c8bfaa;font-size:10px;font-family:ui-monospace,monospace;letter-spacing:.08em}
.sticky-front p{color:#e0d8c8;font:13px/1.6 "Songti SC",serif;margin-top:4px}
.sticky-back{display:none;padding:0 16px 14px;color:#a89080;font:12px/1.7 "Kaiti SC",serif;font-style:italic}
.sticky-back.show{display:block}

/* ═══ 保险柜 ═══ */
.vault{padding:40px 24px;background:linear-gradient(175deg,#1a1610,#0e0c08)}
.vault small{color:#6a6050;font:10px ui-monospace,monospace;letter-spacing:.14em}
.vault h2{margin-top:14px;color:#d4c8b0;font:22px "Songti SC",serif;font-weight:400}
.vault-item{margin-top:20px;padding:16px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.05);border-radius:6px}
.vault-label{color:#c44;font:9px ui-monospace,monospace;letter-spacing:.12em;font-weight:600}
.vault-item p{color:#b0a898;font:13px/1.75 "Kaiti SC",serif;margin-top:8px}
.vault-hl{color:#c44;font-weight:500}
.vault button{border:0;background:none;color:#c9a84c;font:11px ui-monospace,monospace;cursor:pointer;margin-top:8px;padding:0}
.vault-photo{display:none;margin-top:12px;padding:14px;background:rgba(196,68,68,.04);border-radius:4px;animation:fadeSlide .4s ease}
.vault-photo.show{display:block}
.vault-note{color:#8a6a5a;font:11px "Kaiti SC",serif;font-style:italic;margin-top:4px}

/* ═══ 收尾 ═══ */
.ending{padding:40px 24px;text-align:center}
.ending blockquote{color:#c8b8a0;font:18px/1.8 "Songti SC",serif;max-width:380px;margin:0 auto}
.ending em{color:#c44;font-style:normal;display:block;margin-top:12px;font-size:14px;line-height:1.7}

/* ═══ footer ═══ */
footer{padding:20px 24px 38px;background:transparent}
.tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.tags span{color:#8a7860;font-size:10px;font-family:ui-monospace,monospace;padding:4px 10px;border:1px solid rgba(255,255,255,.06);border-radius:20px}`,

`document.querySelectorAll('.clause').forEach(c=>c.onclick=()=>{
  const id='a'+c.dataset.c;
  const el=document.getElementById(id);
  el.classList.toggle('show');
});
document.querySelectorAll('.sticky').forEach(s=>s.onclick=()=>{
  s.querySelector('.sticky-back').classList.toggle('show');
});
document.getElementById('reveal').onclick=()=>{
  document.getElementById('photo').classList.toggle('show');
}`, 2800)
}

/* ═══════════════════════════════════════════
   傅承衍 · 酒会请柬
   媒介：奢华请柬 + 杂志版面 + 事件时间线
   ═══════════════════════════════════════════ */
export function FuChengyanProfile({ profile }: Props) {
  const tg = tagHtml(profile)
  return frame(profile, '酒会请柬', `
<main class="gala">

<!-- ── 请柬 ── -->
<section class="invite">
  <div class="invite-card">
    <div class="invite-border">
      <div class="invite-crest">F</div>
      <small>THE HOUSE OF FU</small>
      <h1>傅氏集团年度酒会</h1>
      <div class="invite-line"></div>
      <p>诚邀</p>
      <div class="invite-name">傅夫人</div>
      <p>莅临出席</p>
      <div class="invite-details">
        <span>DATE · 周五</span>
        <span>TIME · 20:00</span>
        <span>DRESS · 晚礼服</span>
      </div>
    </div>
  </div>
</section>

<!-- ── 红裙特写 ── -->
<section class="editorial">
  <div class="ed-hollow">RED</div>
  <h2>那条裙子</h2>
  <p class="ed-sub">红色丝绸长裙。灯光下泛着流水一样的光泽。<br>穿上它的那一刻，你不再是某人的名义夫人。<br>你是整个宴会厅里最危险的存在。</p>
  <div class="ed-fabric">
    <div class="fabric-shimmer"></div>
  </div>
  <p class="ed-quote">"你今晚穿成这样，是给谁看的。"</p>
</section>

<!-- ── 事件时间线 ── -->
<section class="timeline-sec">
  <small>INCIDENT LOG / 当晚事件还原</small>
  <h2>21:03</h2>
  <p class="tl-sub">一切发生在两秒之内</p>
  <div class="tl-list">
    <div class="tl-item" data-t="1">
      <div class="tl-time">20:15</div>
      <div class="tl-dot"></div>
      <div class="tl-text">到达酒会。他把手搭在你腰上。演戏。</div>
      <div class="tl-detail" id="t1">他的掌心温度比脸上的表情高了六度。你低头看了一眼他的手。他没有收回去。</div>
    </div>
    <div class="tl-item" data-t="2">
      <div class="tl-time">21:03:00</div>
      <div class="tl-dot"></div>
      <div class="tl-text">林骁敬酒。手搭腰侧。停留2秒。</div>
      <div class="tl-detail" id="t2">那只手的位置比他丈夫平时放的位置高了两厘米。这两厘米是导火索。</div>
    </div>
    <div class="tl-item" data-t="3">
      <div class="tl-time">21:03:02</div>
      <div class="tl-dot red"></div>
      <div class="tl-text">他放下酒杯。</div>
      <div class="tl-detail" id="t3">杯底碰桌面的声音不大。但方圆三米内所有人的对话都停了。</div>
    </div>
    <div class="tl-item" data-t="4">
      <div class="tl-time">21:03:12</div>
      <div class="tl-dot red"></div>
      <div class="tl-text">她被拉走。当着三十几个人的面。</div>
      <div class="tl-detail" id="t4">他没有跟任何人解释。外套扔给司机。十秒穿过宴会厅。她的高跟鞋在大理石地面上打滑了两次。</div>
    </div>
  </div>
</section>

<!-- ── 空别墅 ── -->
<section class="villa">
  <div class="villa-glow"></div>
  <p class="villa-desc">别墅的人都被清了出去。<br>落锁声清脆。<br>整栋房子只剩你和他。</p>
  <div class="villa-scene">
    <p>他靠在玄关柜边。松领带。卷袖口。<br>那个动作不急不缓——<br>像在准备做一件需要耐心的事。</p>
  </div>
</section>

<!-- ── 名义 ── -->
<section class="nominal">
  <div class="nom-text" id="nomText">名义？</div>
  <p class="nom-after" id="nomAfter">从今晚开始，这两个字作废。</p>
</section>

<!-- ── 收尾 ── -->
<section class="ending">
  <blockquote>"分床睡是你提的。<br>现在，我改主意了。"</blockquote>
</section>

<footer>
  <div class="tags">${tg}</div>
</footer>
</main>`,

`*{box-sizing:border-box;margin:0}
html,body{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif;-webkit-font-smoothing:antialiased}
.gala{max-width:680px;margin:0 auto;background:transparent}

/* ═══ 请柬 ═══ */
.invite{padding:32px 24px}
.invite-card{max-width:380px;margin:0 auto}
.invite-border{border:2px solid #c9a84c;padding:36px 28px;text-align:center;background:linear-gradient(170deg,#1a1218,#0e0a10);position:relative}
.invite-border::before,.invite-border::after{content:'';position:absolute;width:20px;height:20px;border:1px solid #c9a84c}
.invite-border::before{top:8px;left:8px;border-right:0;border-bottom:0}
.invite-border::after{bottom:8px;right:8px;border-left:0;border-top:0}
.invite-crest{font:36px "Songti SC",serif;color:#c9a84c;letter-spacing:.1em;margin-bottom:6px}
.invite small{color:#8a7860;font:9px ui-monospace,monospace;letter-spacing:.2em}
.invite h1{margin-top:16px;font:22px "Songti SC",serif;color:#e8dcc8;font-weight:400;letter-spacing:.05em}
.invite-line{width:60px;height:1px;background:#c9a84c;margin:16px auto}
.invite p{color:#a89878;font:12px "Kaiti SC",serif}
.invite-name{font:28px "Songti SC",serif;color:#c9a84c;margin:8px 0;letter-spacing:.08em}
.invite-details{display:flex;justify-content:center;gap:16px;margin-top:20px}
.invite-details span{color:#7a6a58;font:8px ui-monospace,monospace;letter-spacing:.12em}

/* ═══ 红裙特写 ═══ */
.editorial{padding:48px 24px;text-align:center;position:relative;overflow:hidden}
.ed-hollow{position:absolute;top:20px;left:50%;transform:translateX(-50%);font:120px ui-monospace,monospace;color:transparent;-webkit-text-stroke:1px rgba(196,68,68,.12);letter-spacing:.15em;pointer-events:none;line-height:1}
.editorial h2{color:#e8d0c8;font:28px "Songti SC",serif;font-weight:400;position:relative}
.ed-sub{color:#a08878;font:13px/1.9 "Kaiti SC",serif;margin-top:14px;position:relative}
.ed-fabric{width:100%;height:80px;margin-top:28px;background:linear-gradient(135deg,#4a1520,#6a2030,#3a1218,#5a1828,#4a1520);border-radius:4px;position:relative;overflow:hidden}
.fabric-shimmer{position:absolute;inset:0;background:linear-gradient(110deg,transparent 30%,rgba(255,255,255,.08) 50%,transparent 70%);animation:shimmer 4s ease-in-out infinite}
@keyframes shimmer{0%,100%{transform:translateX(-100%)}50%{transform:translateX(100%)}}
.ed-quote{margin-top:24px;color:#c44;font:16px/1.7 "Songti SC",serif;font-style:normal;position:relative}

/* ═══ 时间线 ═══ */
.timeline-sec{padding:40px 24px;background:linear-gradient(175deg,#1a1218,#100c10)}
.timeline-sec small{color:#6a5858;font:10px ui-monospace,monospace;letter-spacing:.14em}
.timeline-sec h2{color:#c44;font:48px ui-monospace,monospace;margin-top:10px;letter-spacing:.05em}
.tl-sub{color:#8a6868;font:12px "Kaiti SC",serif;margin-top:4px}
.tl-list{margin-top:24px;padding-left:16px;border-left:2px solid #3a2028}
.tl-item{padding:14px 0;position:relative;cursor:pointer}
.tl-item:hover{background:rgba(196,68,68,.03)}
.tl-time{color:#c44;font:11px ui-monospace,monospace;font-weight:600}
.tl-dot{position:absolute;left:-22px;top:18px;width:8px;height:8px;border-radius:50%;background:#3a2828;border:2px solid #1a1218}
.tl-dot.red{background:#c44}
.tl-text{margin-top:4px;color:#d4c0b8;font:13px/1.6 "Songti SC",serif}
.tl-detail{display:none;margin-top:8px;padding:10px 14px;background:rgba(196,68,68,.04);border-left:2px solid rgba(196,68,68,.3);color:#a08070;font:12px/1.7 "Kaiti SC",serif;font-style:italic;animation:fadeSlide .3s ease}
.tl-detail.show{display:block}
@keyframes fadeSlide{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:translateY(0)}}

/* ═══ 空别墅 ═══ */
.villa{padding:48px 24px;text-align:center;position:relative}
.villa-glow{position:absolute;top:50%;left:50%;width:200px;height:200px;background:radial-gradient(circle,rgba(196,68,68,.06),transparent);transform:translate(-50%,-50%);pointer-events:none}
.villa-desc{color:#8a7068;font:14px/2 "Kaiti SC",serif;position:relative}
.villa-scene{margin-top:28px;padding:20px;background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.04);border-radius:6px;position:relative}
.villa-scene p{color:#c8b0a8;font:15px/1.9 "Songti SC",serif}

/* ═══ 名义 ═══ */
.nominal{padding:60px 24px;text-align:center}
.nom-text{font:64px "Songti SC",serif;color:#e8d0c0;cursor:pointer;position:relative;display:inline-block;transition:.4s}
.nom-text.cracked{color:#c44;text-shadow:0 0 20px rgba(196,68,68,.3);letter-spacing:.15em}
.nom-after{display:none;margin-top:20px;color:#8a6060;font:14px/1.7 "Kaiti SC",serif;animation:fadeSlide .5s ease}
.nom-after.show{display:block}

/* ═══ 收尾 ═══ */
.ending{padding:32px 24px;text-align:center}
.ending blockquote{color:#c8b0a0;font:18px/1.8 "Songti SC",serif}

/* ═══ footer ═══ */
footer{padding:20px 24px 38px;background:transparent}
.tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.tags span{color:#8a5858;font-size:10px;font-family:ui-monospace,monospace;padding:4px 10px;border:1px solid rgba(255,255,255,.06);border-radius:20px}`,

`document.querySelectorAll('.tl-item').forEach(item=>item.onclick=()=>{
  const id='t'+item.dataset.t;
  const el=document.getElementById(id);
  el.classList.toggle('show');
});
document.getElementById('nomText').onclick=function(){
  this.classList.add('cracked');
  document.getElementById('nomAfter').classList.add('show');
}`, 2600)
}

/* ═══════════════════════════════════════════
   萧泊辰 · 购物清单
   媒介：奢侈品清单 + 空餐桌 + 手机消息 + 咖啡馆对照
   ═══════════════════════════════════════════ */
export function XiaoBochenProfile({ profile }: Props) {
  const n = e(profile.display_name || '萧泊辰'), tg = tagHtml(profile)
  return frame(profile, '购物清单', `
<main class="inventory">

<!-- ── 奢侈品清单 ── -->
<section class="receipt">
  <div class="rcpt-header">
    <div class="rcpt-logo">XIAO GROUP</div>
    <small>VIP CLIENT STATEMENT</small>
    <div class="rcpt-line"></div>
  </div>
  <div class="rcpt-title">婚后两年 · 资产清单</div>
  <div class="rcpt-list">
    <div class="rcpt-row"><span class="rcpt-item">市中心别墅（300㎡）</span><span class="rcpt-price">¥ 28,000,000</span></div>
    <div class="rcpt-row"><span class="rcpt-item">意大利手工沙发 x1</span><span class="rcpt-price">¥ 460,000</span></div>
    <div class="rcpt-row"><span class="rcpt-item">限量版落地灯 x1</span><span class="rcpt-price">¥ 180,000</span></div>
    <div class="rcpt-row"><span class="rcpt-item">恒温酒柜（红酒32瓶）</span><span class="rcpt-price">¥ 520,000</span></div>
    <div class="rcpt-row"><span class="rcpt-item">百合花（每三天更换）</span><span class="rcpt-price">¥ 360/次 x ∞</span></div>
    <div class="rcpt-row"><span class="rcpt-item">浴室香薰（周期同步）</span><span class="rcpt-price">¥ 2,800/月</span></div>
    <div class="rcpt-row"><span class="rcpt-item">银行卡（无上限）</span><span class="rcpt-price">UNLIMITED</span></div>
    <div class="rcpt-sep"></div>
    <div class="rcpt-row last"><span class="rcpt-item">晚餐陪伴</span><span class="rcpt-price rcpt-missing">15次 / 730天</span></div>
  </div>
  <div class="rcpt-note">"想要什么我给你买。"<br>他说过一百遍。每一遍都真诚。<br>每一遍都像隔着一层真空玻璃。</div>
</section>

<!-- ── 空餐桌 ── -->
<section class="dinner">
  <div class="table">
    <div class="plate her-plate">
      <div class="plate-circle">
        <small>她的位置</small>
      </div>
    </div>
    <div class="table-center">
      <div class="table-time" id="clock">20:47</div>
      <p>他说过"下次"。<br>下次永远没有来。</p>
    </div>
    <div class="plate his-plate">
      <div class="plate-circle empty">
        <small>空</small>
      </div>
    </div>
  </div>
</section>

<!-- ── 手机消息 ── -->
<section class="imsg">
  <div class="imsg-header">
    <b>${n}</b>
    <small>老公</small>
  </div>
  <div class="imsg-body">
    <div class="imsg-bubble him">今晚有应酬</div>
    <div class="imsg-bubble him">冰箱里有菜，自己热</div>
    <div class="imsg-bubble him">缺什么跟李姐说</div>
    <div class="imsg-bubble her">好</div>
    <div class="imsg-gap">
      <span>第二天</span>
    </div>
    <div class="imsg-bubble him">今天也晚</div>
    <div class="imsg-bubble her">好</div>
    <div class="imsg-gap">
      <span>第三天</span>
    </div>
    <div class="imsg-bubble him">想要什么我给你买</div>
    <div class="imsg-bubble her last">我想你回来吃饭</div>
    <div class="imsg-read">已读</div>
  </div>
</section>

<!-- ── 成玹 · 咖啡馆 ── -->
<section class="cafe">
  <div class="cafe-contrast">
    <small>MEANWHILE / 另一种温度</small>
    <h2>半糖拿铁</h2>
  </div>
  <div class="cafe-card">
    <div class="cafe-icon">
      <svg viewBox="0 0 40 40" width="40" height="40">
        <rect x="8" y="12" width="18" height="20" rx="3" fill="none" stroke="#c9a070" stroke-width="1.5"/>
        <path d="M26 18 Q32 18 32 24 Q32 30 26 30" fill="none" stroke="#c9a070" stroke-width="1.5"/>
        <ellipse cx="17" cy="14" rx="7" ry="2" fill="none" stroke="#c9a070" stroke-width="1"/>
        <path d="M14 8 Q15 5 16 8 M17 6 Q18 3 19 6" stroke="#c9a070" stroke-width="1" fill="none" opacity=".5"/>
      </svg>
    </div>
    <div class="cafe-info">
      <b>成玹</b>
      <p>银灰色头发。干净的五官。比你小两岁。海边咖啡馆。</p>
      <p class="cafe-hl">他记得你喜欢半糖。记得你说过想看海。记得你上次穿了浅蓝色的毛衣。</p>
    </div>
  </div>
  <p class="cafe-line">你在他面前不需要刷卡，不需要住别墅。<br>只需要坐在吧台前听他讲潮汐。</p>
</section>

<!-- ── 对峙 ── -->
<section class="confront">
  <p class="confront-scene">他提前回来了。<br>门锁响了一声。目光扫过客厅——<br>你、成玹、茶杯、画册。<br>停了三秒。</p>
  <div class="confront-word" id="choose">选谁。</div>
  <div class="confront-after" id="chooseAfter">
    <p>他的表情终于有了裂痕。</p>
    <p class="confront-hl">"你可以现在告诉我，<br>也可以等我先让他从这座城市消失。"</p>
  </div>
</section>

<footer>
  <div class="tags">${tg}</div>
</footer>
</main>`,

`*{box-sizing:border-box;margin:0}
html,body{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif;-webkit-font-smoothing:antialiased}
.inventory{max-width:680px;margin:0 auto;background:transparent}

/* ═══ 奢侈品清单 ═══ */
.receipt{padding:32px 24px;background:linear-gradient(175deg,#f8f6f2,#eae6e0)}
.rcpt-header{text-align:center}
.rcpt-logo{font:16px ui-monospace,monospace;color:#1a1a2e;letter-spacing:.2em;font-weight:600}
.rcpt-header small{color:#a8a0a0;font:9px ui-monospace,monospace;letter-spacing:.14em;display:block;margin-top:2px}
.rcpt-line{width:40px;height:1px;background:#d0c8c0;margin:14px auto}
.rcpt-title{text-align:center;color:#5a5058;font:13px "Songti SC",serif;margin-bottom:20px}
.rcpt-list{border-top:1px dashed #d0c8c0;border-bottom:1px dashed #d0c8c0;padding:14px 0}
.rcpt-row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(0,0,0,.04)}
.rcpt-row.last{border-bottom:none;padding-top:14px}
.rcpt-item{color:#3a3038;font:12px "Songti SC",serif}
.rcpt-price{color:#8a8080;font:11px ui-monospace,monospace;text-align:right}
.rcpt-missing{color:#c44;font-weight:600}
.rcpt-sep{height:1px;background:repeating-linear-gradient(90deg,#c0b8b0 0 4px,transparent 4px 8px);margin:10px 0}
.rcpt-note{text-align:center;margin-top:20px;color:#a89890;font:13px/1.8 "Kaiti SC",serif;font-style:italic}

/* ═══ 空餐桌 ═══ */
.dinner{padding:40px 24px;background:linear-gradient(170deg,#1a1a2e,#10101e)}
.table{display:flex;align-items:center;justify-content:center;gap:32px}
.plate-circle{width:80px;height:80px;border-radius:50%;border:1px solid rgba(255,255,255,.08);display:grid;place-items:center}
.plate-circle small{color:#6a6878;font:10px ui-monospace,monospace}
.plate-circle.empty{border-style:dashed;border-color:rgba(255,255,255,.04)}
.plate-circle.empty small{color:#3a3848}
.table-center{text-align:center}
.table-time{color:#e8e4e0;font:32px ui-monospace,monospace;letter-spacing:.05em}
.table-center p{color:#6a6878;font:11px/1.8 "Kaiti SC",serif;margin-top:8px}

/* ═══ 手机消息 ═══ */
.imsg{margin:28px 24px;max-width:375px;margin-left:auto;margin-right:auto;border-radius:20px;background:#fff;overflow:hidden}
.imsg-header{padding:12px 16px;background:#f8f8f8;border-bottom:1px solid #eee;text-align:center}
.imsg-header b{color:#1a1a1a;font-size:15px}
.imsg-header small{display:block;color:#999;font-size:10px;margin-top:2px}
.imsg-body{padding:14px 12px 18px;display:flex;flex-direction:column;gap:8px;background:#fff}
.imsg-bubble{max-width:75%;padding:9px 14px;border-radius:18px;font-size:13px;line-height:1.5}
.imsg-bubble.him{background:#e9e9eb;color:#333;align-self:flex-start;border-bottom-left-radius:4px}
.imsg-bubble.her{background:#007aff;color:#fff;align-self:flex-end;border-bottom-right-radius:4px}
.imsg-bubble.last{background:#ff3b30}
.imsg-gap{text-align:center;padding:8px 0}
.imsg-gap span{color:#b0b0b0;font-size:10px;background:#f0f0f0;padding:2px 10px;border-radius:10px}
.imsg-read{text-align:right;color:#ccc;font-size:10px;padding:2px 8px}

/* ═══ 咖啡馆 ═══ */
.cafe{padding:40px 24px;background:linear-gradient(170deg,#f5e6d0,#ede0cc)}
.cafe-contrast small{color:#a89070;font:10px ui-monospace,monospace;letter-spacing:.14em}
.cafe-contrast h2{color:#5a4838;font:26px "Songti SC",serif;font-weight:400;margin-top:8px}
.cafe-card{margin-top:20px;display:flex;gap:16px;padding:18px;background:rgba(255,255,255,.6);border-radius:12px;border:1px solid rgba(0,0,0,.04)}
.cafe-icon{flex-shrink:0;width:40px;padding-top:4px}
.cafe-info b{color:#5a4838;font-size:14px}
.cafe-info p{color:#8a7868;font:12px/1.7 "Kaiti SC",serif;margin-top:4px}
.cafe-hl{color:#6a5040;font-weight:500}
.cafe-line{margin-top:20px;color:#8a7060;font:14px/1.9 "Kaiti SC",serif;text-align:center}

/* ═══ 对峙 ═══ */
.confront{padding:48px 24px;background:linear-gradient(170deg,#1a1a2e,#10101e);text-align:center}
.confront-scene{color:#8a8898;font:13px/2 "Kaiti SC",serif}
.confront-word{margin-top:28px;font:56px "Songti SC",serif;color:#e8e4e0;cursor:pointer;transition:.4s;display:inline-block}
.confront-word.cracked{color:#c44;letter-spacing:.1em;text-shadow:0 0 20px rgba(196,68,68,.3)}
.confront-after{display:none;margin-top:24px;animation:fadeSlide .5s ease}
.confront-after.show{display:block}
@keyframes fadeSlide{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:translateY(0)}}
.confront-after p{color:#8a8898;font:14px/1.7 "Kaiti SC",serif}
.confront-hl{color:#c44;font:16px/1.8 "Songti SC",serif;margin-top:12px}

/* ═══ footer ═══ */
footer{padding:20px 24px 38px;background:transparent}
.tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.tags span{color:#6a6878;font-size:10px;font-family:ui-monospace,monospace;padding:4px 10px;border:1px solid rgba(255,255,255,.06);border-radius:20px}`,

`document.getElementById('choose').onclick=function(){
  this.classList.add('cracked');
  document.getElementById('chooseAfter').classList.add('show');
};
var h=20,m=47;
setInterval(function(){
  m++;if(m>=60){m=0;h++;if(h>=24)h=0}
  document.getElementById('clock').textContent=String(h).padStart(2,'0')+':'+String(m).padStart(2,'0');
},3000)`, 2800)
}

/* ═══════════════════════════════════════════
   叶修远 · 任务档案
   媒介：军事档案 — 人员卡 + 距离日志 + 事故报告 + 脱密备注
   ═══════════════════════════════════════════ */
export function YeXiuyuanProfile({ profile }: Props) {
  const n = e(profile.display_name || '叶修远'), tg = tagHtml(profile)
  return frame(profile, '任务档案', `
<main class="dossier">

<!-- ── 档案封面 ── -->
<section class="file-cover">
  <div class="fc-stamp">CLASSIFIED</div>
  <div class="fc-title">
    <small>SECURITY DIVISION / PRIVATE SECTOR</small>
    <h1>安保任务档案</h1>
    <div class="fc-no">FILE NO. YXY-2024-0847</div>
  </div>
  <div class="fc-bars">
    <div class="bar"></div>
    <div class="bar"></div>
    <div class="bar short"></div>
  </div>
</section>

<!-- ── 人员卡 ── -->
<section class="personnel">
  <small>SUBJECT PROFILE / 执行人员信息</small>
  <div class="pcard">
    <div class="pcard-photo">
      <svg viewBox="0 0 60 80" width="60" height="80">
        <rect x="5" y="5" width="50" height="70" rx="3" fill="#2a3020" stroke="#4a5a40" stroke-width="1"/>
        <circle cx="30" cy="28" r="12" fill="none" stroke="#6a7a60" stroke-width="1.5"/>
        <path d="M15 65 Q15 48 30 45 Q45 48 45 65" fill="none" stroke="#6a7a60" stroke-width="1.5"/>
        <text x="30" y="75" text-anchor="middle" fill="#4a5a40" font-size="6" font-family="monospace">PHOTO</text>
      </svg>
    </div>
    <div class="pcard-info">
      <div class="prow"><span class="plabel">代号</span><span class="pval">影</span></div>
      <div class="prow"><span class="plabel">姓名</span><span class="pval">${n}</span></div>
      <div class="prow"><span class="plabel">军衔</span><span class="pval">上尉（退役）</span></div>
      <div class="prow"><span class="plabel">服役</span><span class="pval">8年 · 特种部队</span></div>
      <div class="prow"><span class="plabel">任务完成率</span><span class="pval hi">100%</span></div>
      <div class="prow"><span class="plabel">当前状态</span><span class="pval">私人安保</span></div>
    </div>
  </div>
</section>

<!-- ── 保护对象 ── -->
<section class="target-sec">
  <small>PROTECTION TARGET / 保护对象</small>
  <div class="target-card">
    <div class="target-silhouette">
      <svg viewBox="0 0 60 80" width="48" height="64">
        <circle cx="30" cy="22" r="14" fill="#3a4a30"/>
        <path d="M10 80 Q10 50 30 45 Q50 50 50 80" fill="#3a4a30"/>
      </svg>
    </div>
    <div class="target-info">
      <div class="prow"><span class="plabel">身份</span><span class="pval">委托人之女</span></div>
      <div class="prow"><span class="plabel">威胁等级</span><span class="pval hi">高</span></div>
      <div class="prow"><span class="plabel">保护期限</span><span class="pval">持续</span></div>
      <div class="prow"><span class="plabel">安全距离</span><span class="pval">3.0 米</span></div>
    </div>
  </div>
</section>

<!-- ── 距离日志 ── -->
<section class="distance">
  <small>DISTANCE LOG / 90天距离记录</small>
  <h2>他在靠近</h2>
  <p class="dist-note">执行人员与保护对象的平均维持距离（米）</p>
  <div class="dist-chart" id="distChart">
    ${Array.from({length:18},(_,i)=>{
      const d = 3.0 - (i * 0.06) - (i > 12 ? (i-12)*0.02 : 0);
      const pct = ((d - 1.8) / 1.4) * 100;
      const day = (i+1)*5;
      return '<div class="dist-bar-wrap"><div class="dist-bar" style="height:'+pct.toFixed(0)+'%"></div><small>'+day+'</small></div>';
    }).join('')}
  </div>
  <div class="dist-labels">
    <span>3.0m</span>
    <span class="dist-arrow">→</span>
    <span class="dist-end">2.0m</span>
  </div>
  <p class="dist-hl">从三步到两步。<br>他知道这违反了所有他给自己定的规矩。</p>
</section>

<!-- ── 事故报告 ── -->
<section class="incident">
  <small>INCIDENT REPORT / 事故记录 #IR-0847-03</small>
  <div class="ir-card">
    <div class="ir-row"><span class="ir-label">事件类型</span><span>利器袭击</span></div>
    <div class="ir-row"><span class="ir-label">时间</span><span>第67天 22:14</span></div>
    <div class="ir-row"><span class="ir-label">地点</span><span>商场地下停车场</span></div>
    <div class="ir-row"><span class="ir-label">伤情</span><span>左手背裂伤</span></div>
    <div class="ir-row"><span class="ir-label">处置</span><span>清创缝合</span></div>
    <div class="ir-row"><span class="ir-label">缝合</span><span class="ir-hl">7针</span></div>
    <div class="ir-row"><span class="ir-label">执行人员报告</span><span>"皮外伤。"</span></div>
    <div class="ir-row"><span class="ir-label">医疗编号</span><span class="redacted">MR-████-████</span></div>
  </div>
  <p class="ir-note">他说不疼。医疗报告说缝了七针。<br>他撕掉了自己那份报告副本。</p>
</section>

<!-- ── 脱密备注 ── -->
<section class="classified-notes">
  <small>PERSONNEL EVALUATION / 人员心理评估（部分脱密）</small>
  <div class="cn-block">
    <p><span class="redact" data-r="在执行对象哭泣时心率飙升至112bpm">████████████████████</span>期间出现<span class="cn-vis">心率异常</span>。</p>
    <p>建议<span class="cn-vis">重新评估</span>执行人员与保护对象的<span class="redact" data-r="情感距离已低于安全阈值">██████████████</span>。</p>
    <p>注：上述行为<span class="cn-vis">非任务范畴</span>。<span class="redact" data-r="执行人员否认一切。但他的手在写否认报告时是抖的。">████████████████████████████████</span></p>
    <p class="cn-hint">点击黑条解密</p>
  </div>
</section>

<!-- ── 收尾 ── -->
<section class="ending">
  <blockquote>"不用操心我。"<br><br><em>——他说这句话的时候，<br>站的位置已经不是三步了。</em></blockquote>
</section>

<footer>
  <div class="tags">${tg}</div>
</footer>
</main>`,

`*{box-sizing:border-box;margin:0}
html,body{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif;-webkit-font-smoothing:antialiased}
.dossier{max-width:680px;margin:0 auto;background:transparent}

/* ═══ 档案封面 ═══ */
.file-cover{padding:32px 24px;background:linear-gradient(170deg,#2a3020,#1a2018);position:relative}
.fc-stamp{position:absolute;top:20px;right:24px;color:#c44;font:14px ui-monospace,monospace;font-weight:700;letter-spacing:.12em;border:2px solid #c44;padding:4px 10px;transform:rotate(6deg);opacity:.7}
.fc-title small{color:#6a7a60;font:9px ui-monospace,monospace;letter-spacing:.16em}
.fc-title h1{margin-top:12px;color:#d4c8a8;font:28px ui-monospace,monospace;font-weight:400;letter-spacing:.04em}
.fc-no{margin-top:8px;color:#8a9a78;font:11px ui-monospace,monospace}
.fc-bars{margin-top:20px;display:flex;flex-direction:column;gap:6px}
.bar{height:8px;background:#1a2018;border:1px solid #3a4a30;border-radius:2px}
.bar.short{width:60%}

/* ═══ 人员卡 ═══ */
.personnel{padding:28px 24px;background:linear-gradient(175deg,#222e1e,#1a2618)}
.personnel small{color:#6a7a60;font:10px ui-monospace,monospace;letter-spacing:.14em}
.pcard{display:flex;gap:18px;margin-top:16px;padding:18px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.05);border-radius:6px}
.pcard-photo{flex-shrink:0}
.pcard-info{flex:1}
.prow{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.04)}
.plabel{color:#6a7a60;font:10px ui-monospace,monospace}
.pval{color:#c8d0b8;font:11px ui-monospace,monospace;text-align:right}
.pval.hi{color:#c44;font-weight:600}

/* ═══ 保护对象 ═══ */
.target-sec{padding:28px 24px;background:linear-gradient(175deg,#1e2a1a,#182016)}
.target-sec small{color:#6a7a60;font:10px ui-monospace,monospace;letter-spacing:.14em}
.target-card{display:flex;gap:16px;margin-top:16px;padding:18px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.05);border-radius:6px}
.target-silhouette{flex-shrink:0;opacity:.5}
.target-info{flex:1}

/* ═══ 距离日志 ═══ */
.distance{padding:40px 24px;background:linear-gradient(175deg,#2a3020,#1e2818)}
.distance small{color:#6a7a60;font:10px ui-monospace,monospace;letter-spacing:.14em}
.distance h2{margin-top:10px;color:#d4c8a8;font:22px "Songti SC",serif;font-weight:400}
.dist-note{color:#8a9a78;font:11px ui-monospace,monospace;margin-top:4px}
.dist-chart{display:flex;gap:3px;align-items:flex-end;height:100px;margin-top:20px;padding:0 4px}
.dist-bar-wrap{flex:1;display:flex;flex-direction:column;align-items:center;height:100%}
.dist-bar{width:100%;background:linear-gradient(180deg,#6a8a60,#4a6a40);border-radius:2px 2px 0 0;margin-top:auto;transition:height 1.2s ease;min-height:4px}
.dist-bar-wrap small{color:#6a7a60;font:7px ui-monospace,monospace;margin-top:4px}
.dist-labels{display:flex;justify-content:space-between;align-items:center;margin-top:10px;color:#8a9a78;font:11px ui-monospace,monospace}
.dist-arrow{color:#6a7a60}
.dist-end{color:#c44;font-weight:600}
.dist-hl{margin-top:18px;color:#a0b098;font:14px/1.8 "Kaiti SC",serif;text-align:center}

/* ═══ 事故报告 ═══ */
.incident{padding:28px 24px;background:linear-gradient(175deg,#1e2a1a,#162014)}
.incident small{color:#6a7a60;font:10px ui-monospace,monospace;letter-spacing:.14em}
.ir-card{margin-top:16px;padding:18px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.05);border-radius:6px}
.ir-row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.04);color:#c8d0b8;font:11px ui-monospace,monospace}
.ir-label{color:#6a7a60}
.ir-hl{color:#c44;font-weight:600}
.redacted{background:#c8d0b8;color:#c8d0b8;border-radius:2px;padding:0 4px;user-select:none;font-size:10px}
.ir-note{margin-top:14px;color:#a0a890;font:12px/1.7 "Kaiti SC",serif;text-align:center;font-style:italic}

/* ═══ 脱密备注 ═══ */
.classified-notes{padding:28px 24px;background:linear-gradient(175deg,#222e1e,#1a2418)}
.classified-notes small{color:#6a7a60;font:10px ui-monospace,monospace;letter-spacing:.14em}
.cn-block{margin-top:16px;padding:18px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.05);border-radius:6px}
.cn-block p{color:#a0b098;font:12px/2 ui-monospace,monospace;margin-top:4px}
.cn-vis{color:#c44;font-weight:600}
.redact{background:#c8d0b8;color:#c8d0b8;border-radius:2px;padding:1px 2px;cursor:pointer;transition:.3s;user-select:none}
.redact.revealed{background:rgba(196,68,68,.1);color:#c44}
.cn-hint{color:#5a6a50;font:10px ui-monospace,monospace;margin-top:12px;text-align:center;font-style:italic}

/* ═══ 收尾 ═══ */
.ending{padding:40px 24px;text-align:center}
.ending blockquote{color:#c8d0b8;font:18px/1.8 "Songti SC",serif}
.ending em{color:#8a9a78;font-style:normal;display:block;margin-top:12px;font-size:14px;line-height:1.7}

/* ═══ footer ═══ */
footer{padding:20px 24px 38px;background:transparent}
.tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.tags span{color:#6a7a60;font-size:10px;font-family:ui-monospace,monospace;padding:4px 10px;border:1px solid rgba(255,255,255,.06);border-radius:20px}`,

`document.querySelectorAll('.redact').forEach(r=>r.onclick=function(){
  this.textContent=this.dataset.r;
  this.classList.add('revealed');
});
setTimeout(function(){
  document.querySelectorAll('.dist-bar').forEach(function(bar){
    bar.style.height=bar.style.height;
  });
},300)`, 2600)
}
/* ═══════════════════════════════════════════
   宋时柒 · 冰箱留言板
   媒介：他的厨房 — 冰箱门 + 菜谱卡 + 删了又发的消息 + 围裙
   ═══════════════════════════════════════════ */
export function SongShiqiProfile({ profile }: Props) {
  const tg = tagHtml(profile)
  return frame(profile, '冰箱留言板', `
<main class="kitchen">

<!-- ── 冰箱门 ── -->
<section class="fridge">
  <div class="fridge-surface">
    <div class="fridge-handle"></div>

    <div class="magnet photo-magnet">
      <div class="photo-area">
        <div class="photo-placeholder"></div>
        <small>相亲第一天的合照<br>他笑得拘谨，你笑得敷衍</small>
      </div>
    </div>

    <div class="magnet note-magnet" id="note1" data-front="排骨汤 · 小火炖2小时<br><small>汤面上的油花要撇三遍</small>" data-back="上次你说好喝。我记住了。">
      <div class="note-front">排骨汤 · 小火炖2小时<br><small>汤面上的油花要撇三遍</small></div>
      <div class="note-back">上次你说好喝。我记住了。</div>
    </div>

    <div class="magnet list-magnet">
      <div class="list-title">采 购 清 单</div>
      <div class="list-item done">排骨 2斤</div>
      <div class="list-item done">白萝卜</div>
      <div class="list-item done">葱姜蒜</div>
      <div class="list-item done">你爱喝的酸奶（草莓味）</div>
      <div class="list-item">鲈鱼 1条<span class="cross-note">她不吃鱼。</span></div>
    </div>

    <div class="magnet pink-note" id="note2" data-front="不知道你喜不喜欢<br>这个牌子" data-back="买之前犹豫了很久<br>怕你觉得我多管闲事">
      <div class="note-front">不知道你喜不喜欢<br>这个牌子</div>
      <div class="note-back">买之前犹豫了很久<br>怕你觉得我多管闲事</div>
    </div>

    <div class="fridge-temp">4 C</div>
  </div>
</section>

<!-- ── 菜谱卡 ── -->
<section class="recipe">
  <div class="recipe-card">
    <div class="recipe-clip"></div>
    <div class="recipe-header">
      <small>RECIPE CARD</small>
      <h2>清蒸鲈鱼</h2>
    </div>
    <div class="recipe-steps">
      <div class="step"><span>01</span>鲈鱼去鳞去内脏，冲洗干净</div>
      <div class="step"><span>02</span>鱼身两面各划三刀，塞入姜丝</div>
      <div class="step"><span>03</span>大火蒸八分钟，关火虚蒸两分钟</div>
      <div class="step"><span>04</span>淋热油、撒葱丝、浇蒸鱼豉油</div>
      <div class="step"><span>05</span>摆盘。把最嫩的部分放在她那边。</div>
    </div>
    <div class="recipe-note">
      她不吃鱼。我不知道。<br>
      <small>——她吃了一整块。一句话没说。是不想让我难过。</small>
    </div>
  </div>
</section>

<!-- ── 微信草稿 ── -->
<section class="drafts">
  <small>CHAT DRAFTS / 他发出去的永远只有最后一条</small>
  <h2>消息草稿箱</h2>
  <div class="draft-list">
    <div class="draft deleted" id="d1">
      <div class="draft-bubble">你在忙吗</div>
      <div class="draft-status">已删除</div>
      <div class="draft-process">
        <p>「你在忙吗」 → 「你在干嘛」 → 「忙吗」 → 全选 → 删除</p>
        <small>怕打扰你。又怕你觉得我不关心。</small>
      </div>
    </div>
    <div class="draft deleted" id="d2">
      <div class="draft-bubble">今天开心吗</div>
      <div class="draft-status">已删除</div>
      <div class="draft-process">
        <p>「今天开心吗」 → 「今天怎么样」 → 「吃了吗」 → 全选 → 删除</p>
        <small>你从来不跟我说不开心的事。我不敢问。</small>
      </div>
    </div>
    <div class="draft sent" id="d3">
      <div class="draft-bubble">冰箱里有汤你记得喝</div>
      <div class="draft-status">已发送</div>
      <div class="draft-process">
        <p>这条没有修改。这是他唯一确定不会出错的话。</p>
        <small>因为汤是真的在冰箱里。这是一个事实。事实不会惹你烦。</small>
      </div>
    </div>
  </div>
</section>

<!-- ── 围裙 ── -->
<section class="apron-section">
  <div class="apron">
    <div class="apron-neck">
      <div class="apron-strap"></div>
      <div class="apron-strap r"></div>
    </div>
    <div class="apron-body">
      <div class="apron-pocket"></div>
      <div class="apron-stain"></div>
    </div>
  </div>
  <div class="apron-text">
    <small>THAT NIGHT</small>
    <p>粉色围裙。他做饭时系、洗碗时系、端菜时系。<br>那天晚上你跟你的发小聊了三个小时。<br>他站在厨房门口，围裙还没解下来，手上还沾着泡沫。</p>
    <p class="stain-note">围裙胸口偏左的位置，有一小块深色的痕迹。<br>不是油渍。是眼泪砸上去的。</p>
  </div>
</section>

<!-- ── 他的声音 ── -->
<section class="voice">
  <div class="voice-text" id="voiceText">
    <p class="v1">你是不是一直都嫌弃我。</p>
    <p class="v2">嫌我结过婚。嫌我脏。</p>
    <p class="v3">我们除了领了证什么都没干过。<br>她没碰过我。我很干净的。</p>
    <p class="v4">如果你不想要我，<br>就早点告诉我。<br>别这样吊着。<br>我受不了的。</p>
  </div>
  <small class="voice-hint">他说这些话的时候，声音在抖。</small>
</section>

<footer>
  <div class="tags">${tg}</div>
</footer>
</main>`,

`*{box-sizing:border-box;margin:0}
html,body{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif;-webkit-font-smoothing:antialiased}
.kitchen{max-width:680px;margin:0 auto;background:transparent}

/* ═══ 冰箱门 ═══ */
.fridge{padding:20px}
.fridge-surface{position:relative;background:linear-gradient(175deg,#e8e4de,#d8d2c8);border-radius:16px;min-height:500px;padding:40px 24px;border:1px solid #ccc8c0;box-shadow:inset 0 1px 0 rgba(255,255,255,.5),0 8px 24px rgba(0,0,0,.12)}
.fridge-handle{position:absolute;right:12px;top:50%;transform:translateY(-50%);width:6px;height:80px;background:linear-gradient(90deg,#b0a898,#c8c0b0,#b0a898);border-radius:3px}
.fridge-temp{position:absolute;right:16px;bottom:16px;color:#a09888;font:10px ui-monospace,monospace;letter-spacing:.1em}

.magnet{position:relative;cursor:pointer;perspective:600px}
.photo-magnet{margin-bottom:20px}
.photo-area{background:#fff;padding:10px;border-radius:2px;box-shadow:2px 3px 8px rgba(0,0,0,.1);transform:rotate(-2deg);display:inline-block}
.photo-placeholder{width:120px;height:90px;background:linear-gradient(135deg,#f0e8e0,#e8ddd0);border-radius:1px;margin-bottom:6px}
.photo-area small{color:#a09080;font:10px/1.5 "Kaiti SC",serif;display:block}

.note-magnet{background:#fff8cc;padding:14px;border-radius:2px;box-shadow:2px 3px 8px rgba(0,0,0,.08);transform:rotate(1deg);margin-bottom:16px;width:fit-content;max-width:220px;transition:transform .4s}
.note-magnet .note-front{color:#6a5a40;font:13px/1.6 "Kaiti SC",serif}
.note-magnet .note-front small{color:#a09070;font-size:10px}
.note-magnet .note-back{display:none;color:#8b6a50;font:12px/1.6 "Kaiti SC",serif;font-style:italic}
.note-magnet.flipped .note-front{display:none}
.note-magnet.flipped .note-back{display:block}
.note-magnet.flipped{transform:rotate(-1deg);background:#ffe8a0}

.list-magnet{background:#fff;padding:14px 16px;border-radius:2px;box-shadow:2px 3px 8px rgba(0,0,0,.08);transform:rotate(-1.5deg);margin-bottom:16px;max-width:240px}
.list-title{color:#8a7a60;font:9px ui-monospace,monospace;letter-spacing:.14em;margin-bottom:10px}
.list-item{color:#5a4a38;font:12px/2 "Kaiti SC",serif;position:relative;padding-left:16px}
.list-item::before{content:"";position:absolute;left:0;top:50%;width:8px;height:8px;border:1.5px solid #c0b8a0;border-radius:2px;transform:translateY(-50%)}
.list-item.done{color:#b0a090;text-decoration:line-through}
.list-item.done::before{background:#c0b8a0}
.cross-note{display:block;color:#c08080;font:11px "Kaiti SC",serif;text-decoration:none;padding-left:0;margin-top:2px;font-style:italic}

.pink-note{background:#f8e0d8;padding:14px;border-radius:2px;box-shadow:2px 3px 8px rgba(0,0,0,.08);transform:rotate(2deg);width:fit-content;max-width:200px;transition:transform .4s}
.pink-note .note-front{color:#8b6060;font:12px/1.6 "Kaiti SC",serif}
.pink-note .note-back{display:none;color:#a07060;font:11px/1.6 "Kaiti SC",serif;font-style:italic}
.pink-note.flipped .note-front{display:none}
.pink-note.flipped .note-back{display:block}
.pink-note.flipped{transform:rotate(-1deg);background:#f0c8c0}

/* ═══ 菜谱卡 ═══ */
.recipe{padding:32px 20px}
.recipe-card{background:#faf6f0;border-radius:8px;padding:28px 24px;box-shadow:0 4px 16px rgba(0,0,0,.06);position:relative;border:1px solid #e8e0d0}
.recipe-clip{position:absolute;top:-8px;left:50%;transform:translateX(-50%);width:40px;height:16px;background:#c8b8a0;border-radius:0 0 8px 8px;box-shadow:0 2px 4px rgba(0,0,0,.1)}
.recipe-header small{color:#b0a090;font:9px ui-monospace,monospace;letter-spacing:.14em}
.recipe-header h2{color:#5a4a38;font:22px "Songti SC",serif;font-weight:400;margin-top:6px}
.recipe-steps{margin-top:20px;display:flex;flex-direction:column;gap:8px}
.step{color:#6a5a48;font:12px/1.7 "Kaiti SC",serif;display:flex;gap:10px;align-items:baseline}
.step span{color:#c0b0a0;font:10px ui-monospace,monospace;flex-shrink:0}
.recipe-note{margin-top:24px;padding:16px;background:rgba(192,128,128,.06);border-left:2px solid #c08080;border-radius:0 4px 4px 0;color:#c08080;font:14px/1.7 "Kaiti SC",serif}
.recipe-note small{color:#b09090;display:block;margin-top:6px;font-size:11px}

/* ═══ 消息草稿 ═══ */
.drafts{padding:40px 24px;background:linear-gradient(175deg,#1a1418,#120e14)}
.drafts small{color:#8a7878;font:10px ui-monospace,monospace;letter-spacing:.12em}
.drafts h2{color:#e8ddd0;font:24px "Songti SC",serif;font-weight:400;margin-top:10px}
.draft-list{margin-top:24px;display:flex;flex-direction:column;gap:16px}
.draft{position:relative;cursor:pointer}
.draft-bubble{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:12px 16px;color:#d0c0b0;font:13px "PingFang SC",sans-serif;display:inline-block}
.draft.deleted .draft-bubble{text-decoration:line-through;opacity:.5}
.draft.sent .draft-bubble{background:rgba(149,236,105,.12);border-color:rgba(149,236,105,.2);text-decoration:none;opacity:1}
.draft-status{display:inline-block;margin-left:10px;font:10px ui-monospace,monospace;vertical-align:middle}
.draft.deleted .draft-status{color:#c08080}
.draft.sent .draft-status{color:#95ec69}
.draft-process{display:none;margin-top:10px;padding:12px 16px;background:rgba(255,255,255,.03);border-radius:8px;border-left:2px solid rgba(192,128,128,.3)}
.draft-process p{color:#b0a098;font:12px/1.7 "Kaiti SC",serif}
.draft-process small{color:#8a7878;font-size:10px;display:block;margin-top:4px;font-style:italic}
.draft.open .draft-process{display:block}

/* ═══ 围裙 ═══ */
.apron-section{padding:40px 24px;display:flex;gap:24px;align-items:flex-start}
.apron{width:120px;flex-shrink:0}
.apron-neck{display:flex;justify-content:center;gap:40px;position:relative}
.apron-strap{width:2px;height:30px;background:#e0b0a8;transform:rotate(-15deg);transform-origin:bottom}
.apron-strap.r{transform:rotate(15deg);transform-origin:bottom}
.apron-body{width:100px;height:140px;background:#f0c8c0;border-radius:8px 8px 40px 40px;margin:0 auto;position:relative;box-shadow:0 4px 12px rgba(0,0,0,.06)}
.apron-pocket{width:50px;height:30px;border:1.5px solid #e0a898;border-top:none;border-radius:0 0 8px 8px;position:absolute;bottom:50px;left:50%;transform:translateX(-50%)}
.apron-stain{position:absolute;top:25px;left:30px;width:14px;height:14px;border-radius:50%;background:rgba(140,90,80,.25);filter:blur(2px)}
.apron-text{flex:1}
.apron-text small{color:#b0a090;font:9px ui-monospace,monospace;letter-spacing:.12em}
.apron-text p{color:#8a7a68;font:13px/1.8 "Kaiti SC",serif;margin-top:8px}
.stain-note{color:#c08080;font-style:italic;margin-top:12px}

/* ═══ 他的声音 ═══ */
.voice{padding:48px 24px 32px;background:transparent;text-align:center}
.voice-text p{color:#e0ccc0;font:18px/2 "Songti SC",serif;opacity:0;animation:fadeUp 1.2s ease forwards}
.v1{animation-delay:0s}
.v2{animation-delay:.8s}
.v3{animation-delay:1.6s;font-size:16px;margin-top:12px}
.v4{animation-delay:2.8s;font-size:20px;margin-top:20px;color:#c08080}
@keyframes fadeUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
.voice-hint{display:block;margin-top:24px;color:#8a7878;font:10px ui-monospace,monospace;letter-spacing:.12em}

/* ═══ footer ═══ */
footer{padding:30px 24px 38px;background:transparent}
.tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.tags span{color:#8a7a68;font-size:10px;font-family:ui-monospace,monospace;padding:4px 10px;border:1px solid rgba(255,255,255,.06);border-radius:20px}`,

`document.querySelectorAll('.note-magnet,.pink-note').forEach(n=>{
  n.onclick=()=>n.classList.toggle('flipped');
});
document.querySelectorAll('.draft').forEach(d=>{
  d.onclick=()=>d.classList.toggle('open');
});`, 2600)
}


/* ═══════════════════════════════════════════
   沈越清 · 靠窗桌
   媒介：海边咖啡馆 — 黑板菜单 + 两杯饮品 + 餐巾纸 + 潮汐
   ═══════════════════════════════════════════ */
export function ShenYueqingProfile({ profile }: Props) {
  const tg = tagHtml(profile)
  return frame(profile, '靠窗桌', `
<main class="cafe">

<!-- ── 窗景 ── -->
<section class="window-scene">
  <div class="sea-bg">
    <div class="wave w1"></div>
    <div class="wave w2"></div>
    <div class="wave w3"></div>
  </div>
  <div class="window-frame">
    <div class="window-text">
      <small>COASTAL CAFE</small>
      <h1>靠窗的位子</h1>
      <p>午后阳光从落地窗斜进来，<br>把木桌上的灰尘照成缓慢漂浮的金粒。</p>
    </div>
    <div class="dust d1"></div>
    <div class="dust d2"></div>
    <div class="dust d3"></div>
    <div class="dust d4"></div>
    <div class="dust d5"></div>
  </div>
</section>

<!-- ── 黑板菜单 ── -->
<section class="menu">
  <div class="chalkboard">
    <div class="chalk-border"></div>
    <div class="chalk-content">
      <div class="chalk-title">MENU</div>
      <div class="chalk-item">
        <span>拿铁</span>
        <span class="chalk-price">28</span>
      </div>
      <div class="chalk-item her-item">
        <span>热可可</span>
        <span class="chalk-price">22</span>
        <small class="chalk-note">她的</small>
      </div>
      <div class="chalk-item">
        <span>手工饼干</span>
        <span class="chalk-price">12/块</span>
        <small class="chalk-note">每次多放一块</small>
      </div>
      <div class="chalk-divider"></div>
      <div class="chalk-special">
        <small>TODAY'S SPECIAL</small>
        <span>陪伴 · 免费</span>
      </div>
    </div>
  </div>
</section>

<!-- ── 两杯饮品 ── -->
<section class="cups">
  <div class="cup-pair">
    <div class="cup cold-cup">
      <div class="cup-body">
        <div class="latte-surface">
          <div class="ruined-art"></div>
        </div>
      </div>
      <div class="cup-handle"></div>
      <small>凉透的拿铁<br>拉花塌成模糊的白</small>
    </div>
    <div class="cup hot-cup">
      <div class="cup-body hot">
        <div class="cocoa-surface"></div>
        <div class="steam">
          <div class="steam-line s1"></div>
          <div class="steam-line s2"></div>
          <div class="steam-line s3"></div>
        </div>
      </div>
      <div class="cup-handle"></div>
      <small>热可可<br>他在你进门前三分钟热好的</small>
    </div>
  </div>
  <p class="cups-text">"凉了。换一杯。"</p>
</section>

<!-- ── 餐巾纸 ── -->
<section class="napkin-section">
  <small>NAPKIN NOTE / 他的字很轻，像怕弄皱纸面</small>
  <div class="napkin" id="napkin">
    <div class="napkin-folded">
      <p>......</p>
      <small>点击展开</small>
    </div>
    <div class="napkin-open">
      <div class="nap-line">"我在。"</div>
      <div class="nap-line">"趁热喝。"</div>
      <div class="nap-line">"你不用一直笑。<br>在我面前不用。"</div>
      <div class="nap-footer">
        <small>餐巾纸的角被他的拇指揉出了褶皱。<br>他写这些字的时候，你在看窗外。</small>
      </div>
    </div>
  </div>
</section>

<!-- ── 潮汐表 ── -->
<section class="tidal">
  <div class="tidal-header">
    <small>DAILY TIDE</small>
    <h2>他的一天</h2>
  </div>
  <div class="tidal-chart">
    <svg viewBox="0 0 400 100" preserveAspectRatio="none">
      <path d="M0 70 Q50 60 100 55 Q150 48 180 40 Q200 35 220 32 Q250 38 300 55 Q350 68 400 72" fill="none" stroke="rgba(106,154,176,.4)" stroke-width="2"/>
      <circle cx="200" cy="32" r="5" fill="#e8c878"/>
    </svg>
    <div class="tidal-labels">
      <span>8AM<br><small>开门</small></span>
      <span>12PM<br><small>擦桌</small></span>
      <span class="highlight">2PM<br><small>你来了</small></span>
      <span>5PM<br><small>你走了</small></span>
      <span>10PM<br><small>关门</small></span>
    </div>
  </div>
  <p class="tidal-note">他的一天围绕下午两点运转。<br>像潮汐围绕月亮。他是潮水，你是月亮。</p>
</section>

<!-- ── 窗外的问题 ── -->
<section class="question">
  <div class="question-glass">
    <p>什么都没有的人，<br>凭什么比什么都有的人<br>更让你心安</p>
  </div>
  <small>他从来没有问过这个问题。但你一直在想。</small>
</section>

<footer>
  <div class="tags">${tg}</div>
</footer>
</main>`,

`*{box-sizing:border-box;margin:0}
html,body{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif;-webkit-font-smoothing:antialiased}
.cafe{max-width:680px;margin:0 auto;background:transparent}

/* ═══ 窗景 ═══ */
.window-scene{position:relative;min-height:300px;overflow:hidden;border-radius:16px;margin:20px}
.sea-bg{position:absolute;inset:0;background:linear-gradient(180deg,#d4e4ef 0%,#a8c8dc 40%,#8ab0c4 70%,#6a9ab0 100%)}
.wave{position:absolute;bottom:0;left:-10%;width:120%;height:40px;border-radius:50% 50% 0 0;opacity:.3}
.w1{background:#6a9ab0;animation:wave 6s ease-in-out infinite;bottom:0}
.w2{background:#8ab0c4;animation:wave 8s ease-in-out infinite reverse;bottom:10px}
.w3{background:#a8c8dc;animation:wave 7s ease-in-out infinite;bottom:20px;opacity:.2}
@keyframes wave{0%,100%{transform:translateX(0)}50%{transform:translateX(3%)}}
.window-frame{position:relative;z-index:1;padding:60px 30px 40px;text-align:center}
.window-text small{color:rgba(255,255,255,.7);font:10px ui-monospace,monospace;letter-spacing:.2em}
.window-text h1{color:#fff;font:32px "Songti SC",serif;font-weight:400;margin-top:10px;text-shadow:0 2px 12px rgba(0,0,0,.15)}
.window-text p{color:rgba(255,255,255,.85);font:13px/1.8 "Kaiti SC",serif;margin-top:14px}
.dust{position:absolute;width:3px;height:3px;border-radius:50%;background:rgba(255,255,255,.5);animation:floatDust 8s ease-in-out infinite}
.d1{top:30%;left:20%;animation-delay:0s}
.d2{top:45%;left:60%;animation-delay:1.5s;width:2px;height:2px}
.d3{top:25%;left:75%;animation-delay:3s}
.d4{top:55%;left:35%;animation-delay:4.5s;width:2px;height:2px}
.d5{top:40%;left:85%;animation-delay:2s}
@keyframes floatDust{0%,100%{transform:translateY(0) translateX(0);opacity:.3}50%{transform:translateY(-20px) translateX(8px);opacity:.8}}

/* ═══ 黑板 ═══ */
.menu{padding:28px 20px}
.chalkboard{background:#2a3832;border-radius:8px;padding:4px;box-shadow:0 6px 20px rgba(0,0,0,.15)}
.chalk-border{position:absolute;inset:6px;border:1px solid rgba(255,255,255,.08);border-radius:4px;pointer-events:none}
.chalk-content{padding:24px 20px;position:relative}
.chalk-title{color:rgba(255,255,255,.5);font:10px ui-monospace,monospace;letter-spacing:.3em;text-align:center;margin-bottom:16px}
.chalk-item{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px dashed rgba(255,255,255,.08);color:rgba(255,255,255,.7);font:14px "Kaiti SC",serif;position:relative}
.chalk-price{color:rgba(255,255,255,.4);font:12px ui-monospace,monospace}
.chalk-price::before{content:"\\00A5";margin-right:2px}
.chalk-note{position:absolute;right:-4px;top:-6px;color:#e8c878;font:9px "Kaiti SC",serif;transform:rotate(-5deg)}
.her-item{color:rgba(232,200,120,.8)}
.chalk-divider{height:1px;background:rgba(255,255,255,.06);margin:14px 0}
.chalk-special{text-align:center}
.chalk-special small{color:rgba(255,255,255,.3);font:8px ui-monospace,monospace;letter-spacing:.2em;display:block;margin-bottom:6px}
.chalk-special span{color:rgba(232,200,120,.6);font:16px "Songti SC",serif}

/* ═══ 两杯 ═══ */
.cups{padding:32px 24px;text-align:center}
.cup-pair{display:flex;justify-content:center;gap:48px}
.cup{text-align:center}
.cup-body{width:72px;height:56px;background:#f0e8d8;border-radius:4px 4px 20px 20px;position:relative;border:2px solid #d8d0c0;display:inline-block}
.cup-body.hot{background:#5a3a28;border-color:#4a2a18}
.latte-surface{width:56px;height:20px;margin:8px auto 0;border-radius:50%;background:#e0d4c0}
.ruined-art{width:20px;height:12px;margin:4px auto 0;border-radius:50%;background:rgba(255,255,255,.4);filter:blur(3px)}
.cocoa-surface{width:56px;height:20px;margin:8px auto 0;border-radius:50%;background:#3a2218}
.cup-handle{width:16px;height:24px;border:2px solid #d8d0c0;border-left:none;border-radius:0 12px 12px 0;position:absolute;right:-16px;top:14px}
.hot .cup-handle,.hot+.cup-handle{border-color:#4a2a18}
.cup small{display:block;margin-top:12px;color:#8a7a68;font:10px/1.5 "Kaiti SC",serif}
.steam{position:absolute;top:-28px;left:50%;transform:translateX(-50%);width:40px;height:30px}
.steam-line{position:absolute;bottom:0;width:2px;background:rgba(255,255,255,.2);border-radius:1px;animation:rise 3s ease-in-out infinite}
.s1{left:10px;height:16px;animation-delay:0s}
.s2{left:20px;height:22px;animation-delay:.5s}
.s3{left:30px;height:14px;animation-delay:1s}
@keyframes rise{0%{opacity:0;transform:translateY(0) scaleX(1)}40%{opacity:.6}100%{opacity:0;transform:translateY(-24px) scaleX(1.8)}}
.cups-text{margin-top:24px;color:#6a9ab0;font:18px "Songti SC",serif}

/* ═══ 餐巾纸 ═══ */
.napkin-section{padding:40px 24px;background:linear-gradient(175deg,#f5e8d8,#efe4d4)}
.napkin-section>small{color:#b0a090;font:10px ui-monospace,monospace;letter-spacing:.1em}
.napkin{margin-top:20px;cursor:pointer}
.napkin-folded{background:#fff;padding:24px;border-radius:2px;box-shadow:2px 3px 10px rgba(0,0,0,.06);text-align:center;transform:rotate(-1deg)}
.napkin-folded p{color:#c0b0a0;font:16px "Kaiti SC",serif;letter-spacing:.1em}
.napkin-folded small{color:#c8b8a8;font:10px ui-monospace,monospace;display:block;margin-top:8px}
.napkin-open{display:none;background:#fff;padding:32px 24px;border-radius:2px;box-shadow:2px 3px 10px rgba(0,0,0,.06);transform:rotate(.5deg)}
.napkin.unfolded .napkin-folded{display:none}
.napkin.unfolded .napkin-open{display:block}
.nap-line{color:#6a5a48;font:18px/2.2 "Kaiti SC",serif;padding:8px 0;border-bottom:1px solid rgba(0,0,0,.04)}
.nap-line:last-of-type{border-bottom:none}
.nap-footer{margin-top:16px;padding-top:12px;border-top:1px dashed rgba(0,0,0,.06)}
.nap-footer small{color:#b0a090;font:10px/1.6 "Kaiti SC",serif}

/* ═══ 潮汐表 ═══ */
.tidal{padding:40px 24px;background:transparent}
.tidal-header small{color:#8a9aa8;font:10px ui-monospace,monospace;letter-spacing:.12em}
.tidal-header h2{color:#e0d8cc;font:22px "Songti SC",serif;font-weight:400;margin-top:8px}
.tidal-chart{margin-top:24px}
.tidal-chart svg{width:100%;height:80px;display:block}
.tidal-labels{display:flex;justify-content:space-between;margin-top:8px;padding:0 4px}
.tidal-labels span{color:#7a8a98;font:10px ui-monospace,monospace;text-align:center}
.tidal-labels small{color:#6a7a88;display:block;margin-top:2px;font:9px "Kaiti SC",serif}
.tidal-labels .highlight{color:#e8c878}
.tidal-labels .highlight small{color:#d0b868}
.tidal-note{margin-top:20px;color:#a0988a;font:13px/1.8 "Kaiti SC",serif}

/* ═══ 窗外的问题 ═══ */
.question{padding:48px 24px;text-align:center}
.question-glass{display:inline-block;padding:28px 32px;background:rgba(255,255,255,.06);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.08);border-radius:16px}
.question-glass p{color:#c8bcaa;font:20px/1.8 "Songti SC",serif}
.question>small{display:block;margin-top:18px;color:#7a8a98;font:10px ui-monospace,monospace;letter-spacing:.08em}

/* ═══ footer ═══ */
footer{padding:20px 24px 38px;background:transparent}
.tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.tags span{color:#6a9ab0;font-size:10px;font-family:ui-monospace,monospace;padding:4px 10px;border:1px solid rgba(255,255,255,.06);border-radius:20px}`,

`document.getElementById('napkin').onclick=function(){
  this.classList.toggle('unfolded');
};`, 2400)
}


/* ═══════════════════════════════════════════
   谢长安 · 石阶灯
   媒介：竹林山门 — 水墨竹林 + 石阶灯 + 竹简药包 + 讲义对比 + 雨幕 + 手
   ═══════════════════════════════════════════ */
export function XieChanganProfile({ profile }: Props) {
  const n = e(profile.display_name || '谢长安'), tg = tagHtml(profile)
  return frame(profile, '石阶灯', `
<main class="mountain">

<!-- ── 水墨竹林 ── -->
<section class="ink-header">
  <div class="bamboo-forest">
    <div class="bamboo b1"></div>
    <div class="bamboo b2"></div>
    <div class="bamboo b3"></div>
    <div class="bamboo b4"></div>
    <div class="bamboo b5"></div>
    <div class="bamboo b6"></div>
    <div class="bamboo b7"></div>
  </div>
  <div class="mist m1"></div>
  <div class="mist m2"></div>
  <div class="ink-title">
    <small>CHAPTER / 叙引</small>
    <h1>${n}</h1>
    <p>灯火不熄的温润师兄</p>
  </div>
</section>

<!-- ── 石阶灯 ── -->
<section class="lantern-section">
  <div class="stone-steps">
    <div class="step-stone s1"></div>
    <div class="step-stone s2"></div>
    <div class="step-stone s3"></div>
    <div class="lantern" id="lantern">
      <div class="lantern-top"></div>
      <div class="lantern-body">
        <div class="lantern-flame"></div>
      </div>
      <div class="lantern-bottom"></div>
      <div class="lantern-glow"></div>
    </div>
  </div>
  <p class="lantern-text">这盏灯每天都亮着。<br>从你来宗门第一年起。</p>
  <div class="lantern-story" id="lanternStory">
    <p>你有一次半夜失眠走出来。</p>
    <p>看见他蹲在石阶旁边换灯芯。</p>
    <p>他的手被灯油烫了一下，嘶了一声，然后继续换。</p>
    <p>他没发现你看见了。你也假装自己没看见。</p>
    <p class="story-end">那盏灯后来一天都没有灭过。</p>
  </div>
  <button id="lanternBtn">看看深夜的石阶</button>
</section>

<!-- ── 竹简药包 ── -->
<section class="scroll-section">
  <div class="bamboo-scroll">
    <div class="scroll-rod top"></div>
    <div class="scroll-body">
      <div class="scroll-title">行囊药材清单</div>
      <small>提前三天整理 · 分门别类</small>
      <div class="scroll-items">
        <div class="scroll-row">
          <span class="herb-name">伤寒药</span>
          <span class="herb-count">x3</span>
          <small>她可能用到的</small>
        </div>
        <div class="scroll-row">
          <span class="herb-name">跌打药</span>
          <span class="herb-count">x2</span>
          <small>她可能用到的</small>
        </div>
        <div class="scroll-row">
          <span class="herb-name">解毒散</span>
          <span class="herb-count">x1</span>
          <small>她可能用到的</small>
        </div>
        <div class="scroll-row">
          <span class="herb-name">止血粉</span>
          <span class="herb-count">x2</span>
          <small>她可能用到的</small>
        </div>
      </div>
      <div class="scroll-note">药材我帮你装好了。<br>——不是催你。就是问一下你什么时候回来。</div>
    </div>
    <div class="scroll-rod bottom"></div>
  </div>
</section>

<!-- ── 讲义对比 ── -->
<section class="compare">
  <small>COMPARISON / 他自己可能都没有意识到的区别</small>
  <h2>同一个问题，两种回答</h2>
  <div class="compare-cards">
    <div class="compare-card other">
      <div class="compare-label">对师弟</div>
      <div class="compare-content">
        <p>"去藏经阁翻第三排第七本。"</p>
        <small>3句话。结束。</small>
      </div>
      <div class="compare-time">用时：约30秒</div>
    </div>
    <div class="compare-card you">
      <div class="compare-label">对你</div>
      <div class="compare-content">
        <p>画了经脉图 x3</p>
        <p>展开了每一种可能的情况</p>
        <p>"如果气感偏左怎么调"也讲了</p>
        <p>"来，我再给你画一下。"</p>
      </div>
      <div class="compare-time">用时：整整一个时辰</div>
    </div>
  </div>
  <p class="compare-note">他不觉得这是偏心。<br>他觉得这是"你比较笨，需要多讲一点"。<br><em>但其他人都看得出来。</em></p>
</section>

<!-- ── 雨幕 ── -->
<section class="rain-scene">
  <div class="rain-bg">
    <div class="rain-drops">
      ${Array.from({length:40},(_,i)=>'<div class="drop" style="left:'+((i*2.5)%100)+'%;animation-delay:'+(i*0.12).toFixed(2)+'s;animation-duration:'+(0.6+Math.random()*0.4).toFixed(2)+'s"></div>').join('')}
    </div>
    <div class="rain-bamboos">
      <div class="rb rb1"></div>
      <div class="rb rb2"></div>
      <div class="rb rb3"></div>
    </div>
    <div class="silhouette">
      <div class="umbrella">
        <div class="umbrella-top"></div>
        <div class="umbrella-pole"></div>
      </div>
      <div class="person"></div>
    </div>
  </div>
  <p class="rain-text">他的道袍左边几乎全湿了，右边却是干的。<br>他一直把伞偏向你会来的方向——自己站在雨里。</p>
</section>

<!-- ── 那只手 ── -->
<section class="hand-section">
  <div class="hand-reveal" id="handReveal">
    <p class="hand-text">他还站在原地。</p>
    <p class="hand-text">靛蓝色的衣摆被晚风轻轻掀起。</p>
    <p class="hand-text">他没有看你——</p>
    <p class="hand-text last">他在低头看自己的手。<br><em>就是刚才碰过你脸颊的那只手。</em></p>
  </div>
</section>

<!-- ── 收尾 ── -->
<section class="ending">
  <blockquote>别谢我。师兄做这些是应该的。<br><em>……灯不是给你留的，是我忘记吹了。</em></blockquote>
</section>

<footer>
  <div class="tags">${tg}</div>
</footer>
</main>`,

`*{box-sizing:border-box;margin:0}
html,body{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif;-webkit-font-smoothing:antialiased}
.mountain{max-width:680px;margin:0 auto;background:transparent}

/* ═══ 水墨竹林 ═══ */
.ink-header{position:relative;min-height:320px;overflow:hidden;padding:60px 24px 40px}
.bamboo-forest{position:absolute;inset:0;overflow:hidden}
.bamboo{position:absolute;bottom:0;width:3px;background:linear-gradient(0deg,#3a5a40,#4a6a48 40%,#5a7a58);border-radius:2px;opacity:.3}
.b1{left:8%;height:280px;transform:rotate(-.5deg)}
.b2{left:18%;height:310px;transform:rotate(.3deg);opacity:.2}
.b3{left:35%;height:260px;transform:rotate(-.8deg);opacity:.15}
.b4{left:55%;height:300px;transform:rotate(.4deg);opacity:.25}
.b5{left:72%;height:270px;transform:rotate(-.3deg);opacity:.2}
.b6{left:85%;height:290px;transform:rotate(.6deg);opacity:.15}
.b7{left:92%;height:250px;transform:rotate(-.4deg);opacity:.1}
.mist{position:absolute;width:200%;height:40px;background:rgba(255,255,255,.04);filter:blur(20px)}
.m1{top:40%;left:-20%;animation:mistDrift 20s ease-in-out infinite}
.m2{top:60%;left:-50%;animation:mistDrift 25s ease-in-out infinite reverse;opacity:.5}
@keyframes mistDrift{0%,100%{transform:translateX(0)}50%{transform:translateX(15%)}}
.ink-title{position:relative;z-index:1;text-align:center}
.ink-title small{color:#6a8a68;font:9px ui-monospace,monospace;letter-spacing:.18em}
.ink-title h1{color:#e0d8c8;font:36px "Songti SC",serif;font-weight:400;margin-top:12px;letter-spacing:.08em}
.ink-title p{color:#8a9a80;font:12px "Kaiti SC",serif;margin-top:8px;letter-spacing:.06em}

/* ═══ 石阶灯 ═══ */
.lantern-section{padding:40px 24px;text-align:center}
.stone-steps{position:relative;width:200px;margin:0 auto;height:160px}
.step-stone{position:absolute;left:50%;transform:translateX(-50%);height:12px;background:linear-gradient(90deg,#3a3830,#4a4840,#3a3830);border-radius:3px}
.s1{bottom:0;width:180px}
.s2{bottom:18px;width:150px}
.s3{bottom:36px;width:120px}
.lantern{position:absolute;bottom:50px;left:50%;transform:translateX(-50%);cursor:pointer;z-index:2}
.lantern-top{width:20px;height:4px;background:#8a7050;border-radius:2px 2px 0 0;margin:0 auto}
.lantern-body{width:28px;height:36px;background:rgba(232,200,120,.2);border:1.5px solid #c8a860;border-radius:4px;position:relative;overflow:hidden}
.lantern-flame{position:absolute;bottom:6px;left:50%;transform:translateX(-50%);width:6px;height:12px;background:radial-gradient(ellipse,#ffcc44,#ff8800 60%,transparent);border-radius:50% 50% 30% 30%;animation:flicker 2s ease-in-out infinite}
@keyframes flicker{0%,100%{transform:translateX(-50%) scaleY(1) scaleX(1)}25%{transform:translateX(-50%) scaleY(1.1) scaleX(.9)}50%{transform:translateX(-50%) scaleY(.9) scaleX(1.1)}75%{transform:translateX(-50%) scaleY(1.05) scaleX(.95)}}
.lantern-bottom{width:16px;height:3px;background:#8a7050;border-radius:0 0 2px 2px;margin:0 auto}
.lantern-glow{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:80px;height:80px;border-radius:50%;background:radial-gradient(circle,rgba(232,200,120,.15),transparent 70%);animation:glowPulse 4s ease-in-out infinite;pointer-events:none}
@keyframes glowPulse{0%,100%{opacity:.6;transform:translate(-50%,-50%) scale(1)}50%{opacity:1;transform:translate(-50%,-50%) scale(1.2)}}
.lantern-text{margin-top:24px;color:#c8b888;font:15px/1.8 "Kaiti SC",serif}
.lantern-story{display:none;margin-top:20px;text-align:left;padding:20px;background:rgba(232,200,120,.04);border-radius:8px;border:1px solid rgba(232,200,120,.1)}
.lantern-story.show{display:block}
.lantern-story p{color:#b0a080;font:13px/2 "Kaiti SC",serif;opacity:0;animation:fadeIn .8s ease forwards}
.lantern-story p:nth-child(1){animation-delay:0s}
.lantern-story p:nth-child(2){animation-delay:.6s}
.lantern-story p:nth-child(3){animation-delay:1.2s}
.lantern-story p:nth-child(4){animation-delay:1.8s}
.story-end{color:#e8c878;animation-delay:2.4s}
@keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
.lantern-section button{margin-top:16px;border:1px solid rgba(232,200,120,.2);background:transparent;color:#c8a860;font:11px ui-monospace,monospace;padding:8px 16px;border-radius:20px;cursor:pointer;transition:.3s}
.lantern-section button:hover{background:rgba(232,200,120,.08)}

/* ═══ 竹简 ═══ */
.scroll-section{padding:32px 20px}
.bamboo-scroll{position:relative}
.scroll-rod{width:100%;height:10px;background:linear-gradient(90deg,#6a5a42,#8a7a60,#6a5a42);border-radius:5px;position:relative;z-index:1}
.scroll-rod::before,.scroll-rod::after{content:"";position:absolute;top:-3px;width:16px;height:16px;border-radius:50%;background:linear-gradient(135deg,#8a7a60,#5a4a32);border:1px solid #4a3a22}
.scroll-rod::before{left:-4px}
.scroll-rod::after{right:-4px}
.scroll-body{background:#f5f0e0;padding:24px 20px;margin:0 8px;border-left:4px solid #d8d0b8;border-right:4px solid #d8d0b8}
.scroll-title{color:#4a3a28;font:18px "Songti SC",serif;text-align:center}
.scroll-body>small{color:#8a7a60;font:10px ui-monospace,monospace;letter-spacing:.1em;display:block;text-align:center;margin-top:4px}
.scroll-items{margin-top:18px;display:flex;flex-direction:column;gap:6px}
.scroll-row{display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid rgba(0,0,0,.04)}
.herb-name{color:#4a3a28;font:14px "Songti SC",serif;min-width:60px}
.herb-count{color:#8a7a60;font:11px ui-monospace,monospace}
.scroll-row small{color:#a09878;font:10px "Kaiti SC",serif;margin-left:auto;font-style:italic}
.scroll-note{margin-top:18px;text-align:center;color:#6a5a48;font:13px/1.8 "Kaiti SC",serif;padding-top:14px;border-top:1px dashed #d0c8b0}

/* ═══ 讲义对比 ═══ */
.compare{padding:40px 24px;background:transparent}
.compare>small{color:#6a8a68;font:10px ui-monospace,monospace;letter-spacing:.1em}
.compare h2{color:#e0d8c8;font:22px "Songti SC",serif;font-weight:400;margin-top:10px}
.compare-cards{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:24px}
.compare-card{border-radius:10px;padding:18px 14px;position:relative}
.compare-card.other{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.06)}
.compare-card.you{background:rgba(74,104,72,.1);border:1px solid rgba(74,104,72,.2)}
.compare-label{font:9px ui-monospace,monospace;letter-spacing:.12em;margin-bottom:10px}
.other .compare-label{color:#7a8a78}
.you .compare-label{color:#8aba88}
.compare-content p{font:12px/1.8 "Kaiti SC",serif}
.other .compare-content p{color:#8a9a88}
.other .compare-content small{color:#6a7a68;font-size:10px}
.you .compare-content p{color:#c0d0b8}
.compare-time{margin-top:12px;font:10px ui-monospace,monospace}
.other .compare-time{color:#5a6a58}
.you .compare-time{color:#e8c878}
.compare-note{margin-top:24px;color:#a0b098;font:14px/1.8 "Kaiti SC",serif}
.compare-note em{color:#8aba88;font-style:normal}

/* ═══ 雨幕 ═══ */
.rain-scene{padding:0;position:relative;overflow:hidden}
.rain-bg{position:relative;min-height:280px;background:linear-gradient(180deg,#1a2828,#2a3838);overflow:hidden}
.rain-drops{position:absolute;inset:0}
.drop{position:absolute;top:-10px;width:1px;height:14px;background:rgba(200,220,230,.15);animation:rainFall .8s linear infinite}
@keyframes rainFall{0%{transform:translateY(-10px);opacity:0}10%{opacity:.6}90%{opacity:.6}100%{transform:translateY(300px);opacity:0}}
.rain-bamboos{position:absolute;bottom:0;left:0;right:0;height:100%}
.rb{position:absolute;bottom:0;width:3px;background:rgba(74,104,72,.3);border-radius:1px}
.rb1{left:15%;height:240px;transform:rotate(-.3deg)}
.rb2{left:70%;height:260px;transform:rotate(.4deg);opacity:.6}
.rb3{left:88%;height:220px;transform:rotate(-.5deg);opacity:.4}
.silhouette{position:absolute;bottom:20px;left:40%;transform:translateX(-50%)}
.umbrella{position:relative;margin-bottom:-4px}
.umbrella-top{width:70px;height:35px;background:rgba(100,130,120,.4);border-radius:70px 70px 0 0;position:relative;left:-15px}
.umbrella-pole{width:2px;height:40px;background:rgba(100,130,120,.3);margin:0 auto;position:relative;left:-15px}
.person{width:16px;height:50px;background:rgba(60,80,90,.4);border-radius:4px 4px 2px 2px;margin:0 auto;position:relative;left:0}
.rain-text{padding:24px;color:#a0b0a0;font:13px/1.8 "Kaiti SC",serif;text-align:center}

/* ═══ 那只手 ═══ */
.hand-section{padding:48px 24px;text-align:center}
.hand-text{color:#c8bcaa;font:16px/2.2 "Songti SC",serif;opacity:0;animation:fadeIn 1s ease forwards}
.hand-text:nth-child(1){animation-delay:0s}
.hand-text:nth-child(2){animation-delay:.8s}
.hand-text:nth-child(3){animation-delay:1.6s}
.hand-text.last{animation-delay:2.4s;font-size:18px;margin-top:8px}
.hand-text em{color:#e8c878;font-style:normal}

/* ═══ 收尾 ═══ */
.ending{padding:32px 24px;text-align:center}
.ending blockquote{color:#c0b8a0;font:18px/1.8 "Songti SC",serif}
.ending em{color:#8aba88;font-style:normal;display:block;margin-top:8px;font-size:14px}

/* ═══ footer ═══ */
footer{padding:20px 24px 38px;background:transparent}
.tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.tags span{color:#6a8a68;font-size:10px;font-family:ui-monospace,monospace;padding:4px 10px;border:1px solid rgba(255,255,255,.06);border-radius:20px}`,

`document.getElementById('lanternBtn').onclick=function(){
  var s=document.getElementById('lanternStory');
  if(s.classList.contains('show')){
    s.classList.remove('show');
    this.textContent='看看深夜的石阶';
  }else{
    s.classList.add('show');
    this.textContent='收起';
  }
};`, 2600)
}
/* ═══════════════════════════════════════════
   霍清吟 · 无声世界
   媒介：默片胶片 — 听力图 + 字幕卡 + 手语 + 逆转
   ═══════════════════════════════════════════ */
export function HuoQingyinProfile({ profile }: Props) {
  const n = e(profile.display_name || '霍清吟'), tg = tagHtml(profile)
  return frame(profile, '无声世界', `
<main class="film">

<!-- ── 默片片头 ── -->
<section class="title-card">
  <div class="film-grain"></div>
  <div class="title-border">
    <div class="corner tl"></div><div class="corner tr"></div>
    <div class="corner bl"></div><div class="corner br"></div>
    <h1>无声世界</h1>
    <p class="subtitle">A SILENT WORLD</p>
    <div class="reel-line"></div>
    <p class="meta">${n} · 先天失聪 · 轻度自闭</p>
  </div>
</section>

<!-- ── 听力图 ── -->
<section class="audiogram">
  <div class="ag-head">
    <small>AUDIOGRAM / 纯音听力测试</small>
    <h2>他的世界，没有声音</h2>
  </div>
  <div class="ag-chart">
    <div class="ag-y">
      <span>0dB</span><span>20</span><span>40</span><span>60</span><span>80</span><span>100</span>
    </div>
    <div class="ag-bars">
      <div class="ag-col"><div class="ag-bar" data-h="95"></div><small>125Hz</small></div>
      <div class="ag-col"><div class="ag-bar" data-h="98"></div><small>250</small></div>
      <div class="ag-col"><div class="ag-bar" data-h="96"></div><small>500</small></div>
      <div class="ag-col"><div class="ag-bar" data-h="99"></div><small>1k</small></div>
      <div class="ag-col"><div class="ag-bar" data-h="97"></div><small>2k</small></div>
      <div class="ag-col"><div class="ag-bar rising" data-h="45"></div><small>4k</small></div>
      <div class="ag-col"><div class="ag-bar" data-h="94"></div><small>8k</small></div>
    </div>
  </div>
  <p class="ag-note">助听器植入后，4kHz 频段首次产生反应。<br>那是人声所在的频率。</p>
</section>

<!-- ── 默片字幕卡序列 ── -->
<section class="intertitles">
  <div class="film-grain"></div>
  <div class="inter-card" id="ic1">
    <div class="ic-frame"></div>
    <p>你蹲下来，把面包撕成小块。</p>
  </div>
  <div class="inter-card" id="ic2">
    <div class="ic-frame"></div>
    <p>他扑上去，整个人趴在地上，<br>把面包塞进嘴里。</p>
  </div>
  <div class="inter-card" id="ic3">
    <div class="ic-frame"></div>
    <p>他舔了一下你的手指<br>——上面沾了面包屑。</p>
  </div>
  <div class="inter-card" id="ic4">
    <div class="ic-frame"></div>
    <p>你走了。<br>他撞了一下墙。又撞了一下。</p>
  </div>
  <div class="inter-card fire" id="ic5">
    <div class="ic-frame"></div>
    <p>三年后。火灾。<br>你冲了进去。</p>
  </div>
  <div class="inter-card" id="ic6">
    <div class="ic-frame"></div>
    <p>你的声音没有了。</p>
  </div>
</section>

<!-- ── 手语 ── -->
<section class="signs">
  <small>SIGN LANGUAGE / 他在学的词</small>
  <div class="sign-row">
    <div class="sign-card">
      <svg viewBox="0 0 60 70" fill="none" stroke="#a09080" stroke-width="1.2" stroke-linecap="round">
        <path d="M20 55 L20 30 Q20 20 28 18 L28 12"/>
        <path d="M28 18 Q36 20 36 30 L36 55"/>
        <path d="M24 28 L24 16 Q24 10 30 10 Q36 10 36 16"/>
        <path d="M32 28 L32 14 Q32 8 38 10 L40 16"/>
        <circle cx="28" cy="58" r="6" stroke-dasharray="2 2"/>
      </svg>
      <b>我在</b>
    </div>
    <div class="sign-card">
      <svg viewBox="0 0 60 70" fill="none" stroke="#a09080" stroke-width="1.2" stroke-linecap="round">
        <path d="M18 50 Q18 25 30 20 Q42 25 42 50"/>
        <path d="M24 35 L24 20"/><path d="M36 35 L36 20"/>
        <path d="M30 45 L30 55"/>
        <path d="M22 50 L38 50"/>
      </svg>
      <b>别走</b>
    </div>
    <div class="sign-card">
      <svg viewBox="0 0 60 70" fill="none" stroke="#a09080" stroke-width="1.2" stroke-linecap="round">
        <path d="M15 45 Q15 25 30 18 Q45 25 45 45"/>
        <path d="M25 30 Q30 22 35 30"/>
        <circle cx="30" cy="40" r="4"/>
        <path d="M22 55 L38 55"/>
      </svg>
      <b>没关系</b>
    </div>
  </div>
</section>

<!-- ── 逆转 ── -->
<section class="reversal">
  <div class="rev-split">
    <div class="rev-left">
      <div class="rev-icon">
        <svg viewBox="0 0 40 40" fill="none" stroke="#6a5e50" stroke-width="1.5">
          <circle cx="20" cy="20" r="14"/>
          <line x1="8" y1="8" x2="32" y2="32"/>
        </svg>
      </div>
      <p>他的世界<br><b>无声</b></p>
      <small>先天失聪 · 15年</small>
    </div>
    <div class="rev-divider">
      <div class="rev-arrow">&#x27F7;</div>
    </div>
    <div class="rev-right">
      <div class="rev-icon">
        <svg viewBox="0 0 40 40" fill="none" stroke="#c44a20" stroke-width="1.5">
          <path d="M14 10 Q14 6 18 6 L22 6 Q26 6 26 10 L26 18 Q26 22 30 24"/>
          <path d="M14 10 L14 18 Q14 22 10 24"/>
          <circle cx="20" cy="30" r="4"/>
          <line x1="12" y1="28" x2="28" y2="32" stroke="#c44a20" stroke-width="2"/>
        </svg>
      </div>
      <p>你的声音<br><b class="fire-text">消失了</b></p>
      <small>声带烧伤 · 永久</small>
    </div>
  </div>
  <div class="rev-text">他终于能听见了。<br>你却再也说不出口了。</div>
</section>

<!-- ── 他的声音（学说话） ── -->
<section class="speech">
  <small>HIS VOICE / 他学会的第一句完整的话</small>
  <div class="speech-box" id="speechBox">
    <span class="caret"></span>
  </div>
  <button id="playBtn">播放他的声音 &#9654;</button>
  <p class="speech-note">沙哑的。咬字含糊的。<br>像一个人在黑暗里摸索着拼凑语言的碎片。</p>
</section>

<!-- ── 结语 ── -->
<section class="ending">
  <div class="film-grain"></div>
  <blockquote>"我以前听不见。现在能听见了。<br>但最想听的声音没有了。"</blockquote>
  <div class="reel-end">
    <div class="reel-hole"></div>
    <div class="reel-hole"></div>
    <div class="reel-hole"></div>
    <small>- FIN -</small>
    <div class="reel-hole"></div>
    <div class="reel-hole"></div>
    <div class="reel-hole"></div>
  </div>
</section>

<footer><div class="tags">${tg}</div></footer>
</main>`,

`*{box-sizing:border-box;margin:0}
html,body{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif;-webkit-font-smoothing:antialiased}
.film{max-width:680px;margin:0 auto;background:transparent}

/* ═══ 胶片颗粒 ═══ */
.film-grain{position:absolute;inset:0;pointer-events:none;opacity:.12;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E");animation:grain .3s steps(4) infinite}
@keyframes grain{0%{transform:translate(0,0)}25%{transform:translate(-2px,2px)}50%{transform:translate(2px,-1px)}75%{transform:translate(-1px,-2px)}100%{transform:translate(0,0)}}

/* ═══ 默片片头 ═══ */
.title-card{position:relative;padding:48px 24px 40px;background:#1a1814;text-align:center;overflow:hidden}
.title-border{border:2px solid #8a7e68;padding:36px 24px;position:relative}
.corner{position:absolute;width:18px;height:18px;border:2px solid #a89878}
.tl{top:-2px;left:-2px;border-right:none;border-bottom:none}
.tr{top:-2px;right:-2px;border-left:none;border-bottom:none}
.bl{bottom:-2px;left:-2px;border-right:none;border-top:none}
.br{bottom:-2px;right:-2px;border-left:none;border-top:none}
.title-card h1{color:#e8dcc8;font:36px/1.2 "Songti SC","SimSun",serif;font-weight:400;letter-spacing:.2em}
.subtitle{color:#8a7e68;font:11px ui-monospace,monospace;letter-spacing:.3em;margin-top:8px}
.reel-line{width:60%;height:1px;background:#5a5040;margin:18px auto}
.meta{color:#a89878;font:12px "Kaiti SC",serif}

/* ═══ 听力图 ═══ */
.audiogram{padding:40px 24px;background:linear-gradient(175deg,#221e18,#181510)}
.ag-head small{color:#8a7e68;font:10px ui-monospace,monospace;letter-spacing:.12em}
.ag-head h2{margin-top:12px;color:#e8dcc8;font:24px "Songti SC",serif;font-weight:400}
.ag-chart{display:flex;gap:4px;margin-top:24px;height:180px;align-items:flex-end;padding-left:36px;position:relative}
.ag-y{position:absolute;left:0;top:0;bottom:20px;display:flex;flex-direction:column;justify-content:space-between}
.ag-y span{color:#6a5e50;font:8px ui-monospace,monospace}
.ag-bars{display:flex;gap:12px;flex:1;align-items:flex-end;height:160px}
.ag-col{display:flex;flex-direction:column;align-items:center;flex:1;height:100%}
.ag-bar{width:100%;background:#4a3e30;border-radius:2px 2px 0 0;transition:height 2s ease;height:0}
.ag-bar.rising{background:linear-gradient(0deg,#c0c0c0,#e8dcc8)}
.ag-col small{color:#6a5e50;font:8px ui-monospace,monospace;margin-top:6px}
.ag-note{margin-top:18px;color:#a89878;font:12px/1.7 "Kaiti SC",serif;text-align:center}

/* ═══ 字幕卡 ═══ */
.intertitles{position:relative;padding:10px 0;overflow:hidden}
.inter-card{padding:32px 24px;background:#1a1814;text-align:center;opacity:0;transform:translateY(12px);transition:opacity .8s,transform .8s;margin:2px 0}
.inter-card.show{opacity:1;transform:translateY(0)}
.ic-frame{width:60%;height:1px;background:#5a5040;margin:0 auto 18px}
.inter-card p{color:#e8dcc8;font:16px/1.8 "Songti SC",serif}
.inter-card.fire p{color:#c44a20}
.inter-card::after{content:'';display:block;width:60%;height:1px;background:#5a5040;margin:18px auto 0}

/* ═══ 手语 ═══ */
.signs{padding:40px 24px;background:linear-gradient(175deg,#201c16,#161210)}
.signs small{color:#8a7e68;font:10px ui-monospace,monospace;letter-spacing:.12em;display:block}
.sign-row{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:24px}
.sign-card{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);border-radius:12px;padding:16px;text-align:center}
.sign-card svg{width:50px;height:58px;display:block;margin:0 auto}
.sign-card b{display:block;margin-top:10px;color:#c8baa8;font-size:12px}

/* ═══ 逆转 ═══ */
.reversal{padding:40px 24px;background:#1a1814}
.rev-split{display:grid;grid-template-columns:1fr 40px 1fr;gap:8px;align-items:center}
.rev-left,.rev-right{text-align:center;padding:20px 12px;background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.05);border-radius:12px}
.rev-icon{margin:0 auto 12px}
.rev-icon svg{width:40px;height:40px}
.rev-left p,.rev-right p{color:#c8baa8;font:14px "Kaiti SC",serif;line-height:1.6}
.rev-left b{color:#c0c0c0}.rev-right b{color:#c44a20}
.rev-left small,.rev-right small{color:#6a5e50;font:9px ui-monospace,monospace;display:block;margin-top:6px}
.fire-text{text-shadow:0 0 12px rgba(196,74,32,.4)}
.rev-divider{text-align:center;color:#6a5e50;font-size:20px}
.rev-arrow{animation:pulse 3s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:.4}50%{opacity:1}}
.rev-text{margin-top:24px;text-align:center;color:#e8dcc8;font:18px/1.7 "Songti SC",serif;padding:20px;border-top:1px solid #3a3428;border-bottom:1px solid #3a3428}

/* ═══ 学说话 ═══ */
.speech{padding:40px 24px;background:linear-gradient(175deg,#221e18,#181510);text-align:center}
.speech small{color:#8a7e68;font:10px ui-monospace,monospace;letter-spacing:.12em}
.speech-box{min-height:60px;margin-top:20px;color:#e8dcc8;font:20px/1.8 "Kaiti SC",serif;text-align:left;padding:18px;background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.05);border-radius:8px;position:relative}
.caret{display:inline-block;width:2px;height:1.2em;background:#c0c0c0;vertical-align:text-bottom;animation:blink .8s step-end infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}
.speech button{margin-top:16px;border:1px solid #5a5040;background:transparent;color:#a89878;font:11px ui-monospace,monospace;padding:8px 20px;border-radius:20px;cursor:pointer;transition:.3s}
.speech button:hover{background:rgba(255,255,255,.05);color:#e8dcc8}
.speech-note{margin-top:16px;color:#6a5e50;font:11px/1.6 "Kaiti SC",serif}

/* ═══ 结尾 ═══ */
.ending{position:relative;padding:48px 24px 20px;background:#1a1814;text-align:center;overflow:hidden}
.ending blockquote{color:#c8baa8;font:17px/1.8 "Songti SC",serif;padding:0 16px}
.reel-end{display:flex;align-items:center;justify-content:center;gap:12px;margin-top:28px}
.reel-hole{width:10px;height:10px;border-radius:50%;border:1px solid #5a5040}
.reel-end small{color:#6a5e50;font:10px ui-monospace,monospace;letter-spacing:.3em}

footer{padding:20px 24px 38px;background:transparent}
.tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.tags span{color:#8a7e68;font-size:10px;font-family:ui-monospace,monospace;padding:4px 10px;border:1px solid rgba(255,255,255,.06);border-radius:20px}`,

`// Audiogram bars animate on load
setTimeout(()=>{
  document.querySelectorAll('.ag-bar').forEach(b=>{
    b.style.height=b.dataset.h+'%';
  });
},300);

// Intertitle cards fade in on scroll
const obs=new IntersectionObserver((entries)=>{
  entries.forEach(en=>{if(en.isIntersecting){en.target.classList.add('show');obs.unobserve(en.target);}});
},{threshold:.3});
document.querySelectorAll('.inter-card').forEach(c=>obs.observe(c));

// Speech typing effect
const speechText='你……现在……好像我当初……求你别走的……样子。';
let speechPlayed=false;
document.getElementById('playBtn').onclick=()=>{
  if(speechPlayed)return;speechPlayed=true;
  const box=document.getElementById('speechBox');
  box.innerHTML='<span class="caret"></span>';
  let i=0;
  const timer=setInterval(()=>{
    if(i>=speechText.length){clearInterval(timer);return;}
    const ch=speechText[i];
    box.insertBefore(document.createTextNode(ch),box.querySelector('.caret'));
    i++;
    if(ch==='…')clearInterval(timer),setTimeout(()=>{
      const t2=setInterval(()=>{
        if(i>=speechText.length){clearInterval(t2);return;}
        const c2=speechText[i];
        box.insertBefore(document.createTextNode(c2),box.querySelector('.caret'));
        i++;
        if(c2==='…'||c2==='。'){clearInterval(t2);setTimeout(()=>{
          const t3=setInterval(()=>{
            if(i>=speechText.length){clearInterval(t3);return;}
            const c3=speechText[i];
            box.insertBefore(document.createTextNode(c3),box.querySelector('.caret'));
            i++;
          },120);
        },600);}
      },120);
    },800);
  },120);
};`, 2800)
}


/* ═══════════════════════════════════════════
   沈知序 · 公寓异常
   媒介：智能家居面板 — 异常日志 + 镜面留言 + 鬼魂轮廓
   ═══════════════════════════════════════════ */
export function ShenZhixuProfile({ profile }: Props) {
  const tg = tagHtml(profile)
  return frame(profile, '公寓异常', `
<main class="apt">

<!-- ── 智能家居面板 ── -->
<section class="dashboard">
  <div class="dash-header">
    <small>HOME CONTROL / 公寓智能系统</small>
    <div class="dash-status">
      <span class="status-dot"></span>
      <span>异常检测中</span>
    </div>
  </div>
  <div class="dash-grid">
    <div class="dash-card glitch-hover">
      <div class="dc-icon"><svg viewBox="0 0 24 24" fill="none" stroke="#6a8a98" stroke-width="1.5"><path d="M12 2a8 8 0 0 0-8 8v2h2v-2a6 6 0 1 1 12 0v2h2v-2a8 8 0 0 0-8-8z"/><rect x="6" y="12" width="12" height="8" rx="2"/><line x1="12" y1="16" x2="12" y2="18"/></svg></div>
      <b>室温</b>
      <div class="dc-val flicker">18°C</div>
      <small>比昨天低2°C</small>
    </div>
    <div class="dash-card glitch-hover">
      <div class="dc-icon"><svg viewBox="0 0 24 24" fill="none" stroke="#6a8a98" stroke-width="1.5"><rect x="3" y="4" width="18" height="16" rx="2"/><line x1="3" y1="12" x2="21" y2="12"/></svg></div>
      <b>窗帘</b>
      <div class="dc-val">已关闭</div>
      <small>03:17 自动关闭</small>
    </div>
    <div class="dash-card glitch-hover">
      <div class="dc-icon"><svg viewBox="0 0 24 24" fill="none" stroke="#6a8a98" stroke-width="1.5"><circle cx="12" cy="12" r="4"/><path d="M12 2v4m0 12v4M2 12h4m12 0h4"/></svg></div>
      <b>灯光</b>
      <div class="dc-val warn">异常闪烁</div>
      <small>区域: 卧室</small>
    </div>
    <div class="dash-card glitch-hover">
      <div class="dc-icon"><svg viewBox="0 0 24 24" fill="none" stroke="#6a8a98" stroke-width="1.5"><rect x="5" y="2" width="14" height="20" rx="2"/><circle cx="12" cy="16" r="2"/><line x1="12" y1="10" x2="12" y2="14"/></svg></div>
      <b>门锁</b>
      <div class="dc-val">已锁定</div>
      <small>无人操作</small>
    </div>
  </div>
</section>

<!-- ── 镜面留言 ── -->
<section class="mirror">
  <div class="mirror-glass">
    <div class="mirror-fog"></div>
    <div class="mirror-text" id="mirrorText">早点回来</div>
    <div class="mirror-sub">——浴室镜面，每天早上八点</div>
  </div>
</section>

<!-- ── 异常日志 ── -->
<section class="anomaly">
  <div class="ano-header">
    <small>ANOMALY LOG / 异常记录</small>
    <h2>过去24小时</h2>
  </div>
  <div class="ano-list">
    <div class="ano-row glitch-text">
      <span class="ano-time">02:14</span>
      <span class="ano-desc">杯子位置变化 <em>(左→右)</em></span>
      <span class="ano-tag">物体移动</span>
    </div>
    <div class="ano-row glitch-text">
      <span class="ano-time">03:17</span>
      <span class="ano-desc">被角被掖紧</span>
      <span class="ano-tag">触觉异常</span>
    </div>
    <div class="ano-row glitch-text">
      <span class="ano-time">03:22</span>
      <span class="ano-desc">室温下降 <em>1.5°C</em></span>
      <span class="ano-tag">温度波动</span>
    </div>
    <div class="ano-row glitch-text">
      <span class="ano-time">04:08</span>
      <span class="ano-desc">卧室灯光闪烁 <em>x3</em></span>
      <span class="ano-tag">电气异常</span>
    </div>
    <div class="ano-row glitch-text">
      <span class="ano-time">23:47</span>
      <span class="ano-desc">回家时间记录 <em>比昨天晚23分钟</em></span>
      <span class="ano-tag warn">超时</span>
    </div>
  </div>
</section>

<!-- ── 他的轮廓 ── -->
<section class="presence" id="presenceArea">
  <div class="ghost-silhouette" id="ghost">
    <svg viewBox="0 0 120 200" fill="none">
      <defs>
        <radialGradient id="glow" cx="50%" cy="30%" r="60%">
          <stop offset="0%" stop-color="rgba(200,208,216,.15)"/>
          <stop offset="100%" stop-color="rgba(200,208,216,0)"/>
        </radialGradient>
      </defs>
      <ellipse cx="60" cy="30" rx="20" ry="24" fill="url(#glow)"/>
      <path d="M40 55 Q40 15 60 10 Q80 15 80 55 L80 160 Q80 180 60 185 Q40 180 40 160 Z" stroke="rgba(200,208,216,.12)" stroke-width="1" fill="none"/>
      <path d="M45 24 Q55 18 60 10 Q65 18 75 24" stroke="rgba(220,225,230,.15)" stroke-width=".8" fill="none"/>
      <circle cx="52" cy="32" r="1.5" fill="rgba(200,208,216,.2)"/>
      <circle cx="68" cy="32" r="1.5" fill="rgba(200,208,216,.2)"/>
    </svg>
  </div>
  <div class="presence-text">
    <p>他在这里。<br>你感觉得到。</p>
    <button id="callBtn">……知序？</button>
  </div>
  <div class="ghost-reply" id="ghostReply"></div>
</section>

<!-- ── 公约 ── -->
<section class="covenant">
  <small>LIFE COVENANT / 同居公约（仍在执行）</small>
  <div class="cov-list">
    <div class="cov-item checked">
      <span class="cov-check">&#10003;</span>
      <span>不要晚归</span>
    </div>
    <div class="cov-item checked">
      <span class="cov-check">&#10003;</span>
      <span>不要让陌生男人进门</span>
    </div>
    <div class="cov-item checked">
      <span class="cov-check">&#10003;</span>
      <span>睡觉睡他那边</span>
    </div>
    <div class="cov-item unchecked">
      <span class="cov-check">&#x2610;</span>
      <span class="strikethrough">不要离开</span>
      <em class="cov-note">这条我做不到了。</em>
    </div>
  </div>
</section>

<!-- ── 结语 ── -->
<section class="ending">
  <blockquote>"他没有消失。<br>他只是你看不见了而已。"</blockquote>
  <p class="end-sub">公寓里的灯，每晚十一点四十七分会闪一次。<br>那是他记得的你回家的时间。</p>
</section>

<footer><div class="tags">${tg}</div></footer>
</main>`,

`*{box-sizing:border-box;margin:0}
html,body{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif;-webkit-font-smoothing:antialiased}
.apt{max-width:680px;margin:0 auto;background:transparent}

/* ═══ 智能面板 ═══ */
.dashboard{padding:28px 20px;background:linear-gradient(175deg,#141820,#0e1218)}
.dash-header{display:flex;justify-content:space-between;align-items:center}
.dash-header small{color:#4a6070;font:10px ui-monospace,monospace;letter-spacing:.12em}
.dash-status{display:flex;align-items:center;gap:6px;color:#6a8a98;font:10px ui-monospace,monospace}
.status-dot{width:6px;height:6px;border-radius:50%;background:#4a8a70;animation:dotpulse 2s infinite}
@keyframes dotpulse{0%,100%{opacity:.4}50%{opacity:1}}
.dash-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:18px}
.dash-card{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.05);border-radius:10px;padding:16px 14px;position:relative;overflow:hidden}
.dc-icon{margin-bottom:8px}
.dc-icon svg{width:20px;height:20px}
.dash-card b{color:#8a9aa8;font-size:11px;font-weight:500;display:block}
.dc-val{color:#c8d0d8;font:18px ui-monospace,monospace;margin-top:4px}
.dc-val.warn{color:#a04040}
.dash-card small{color:#4a5a68;font:9px ui-monospace,monospace;display:block;margin-top:4px}
.flicker{animation:flicker 3s infinite}
@keyframes flicker{0%,95%,100%{opacity:1}96%{opacity:.3}97%{opacity:1}98%{opacity:.2}99%{opacity:.8}}

/* glitch hover */
.glitch-hover{transition:.3s}
.glitch-hover:hover{transform:translate(-1px,0);box-shadow:2px 0 0 rgba(100,160,200,.15),-2px 0 0 rgba(200,100,100,.1)}

/* ═══ 镜面留言 ═══ */
.mirror{padding:36px 24px;background:#0e1218}
.mirror-glass{position:relative;border-radius:12px;padding:48px 20px 36px;background:linear-gradient(145deg,rgba(255,255,255,.04),rgba(255,255,255,.01));border:1px solid rgba(255,255,255,.06);text-align:center;overflow:hidden}
.mirror-fog{position:absolute;inset:0;background:radial-gradient(ellipse at 50% 40%,rgba(200,210,220,.06),transparent 70%);pointer-events:none}
.mirror-text{color:rgba(200,210,220,.08);font:32px "Kaiti SC",serif;transition:color 3s,text-shadow 3s;letter-spacing:.15em}
.mirror-text.visible{color:rgba(200,210,220,.5);text-shadow:0 0 30px rgba(200,210,220,.15)}
.mirror-text.fade{color:rgba(200,210,220,.04);text-shadow:none}
.mirror-sub{color:#3a4a58;font:10px ui-monospace,monospace;margin-top:12px}

/* ═══ 异常日志 ═══ */
.anomaly{padding:36px 20px;background:linear-gradient(175deg,#141820,#0e1218)}
.ano-header small{color:#4a6070;font:10px ui-monospace,monospace;letter-spacing:.12em}
.ano-header h2{margin-top:10px;color:#c8d0d8;font:20px "Songti SC",serif;font-weight:400}
.ano-list{margin-top:20px;display:flex;flex-direction:column;gap:1px}
.ano-row{display:flex;align-items:center;gap:12px;padding:10px 12px;background:rgba(255,255,255,.02);border-left:2px solid #2a3a48;position:relative}
.ano-time{flex-shrink:0;width:40px;color:#4a6a78;font:10px ui-monospace,monospace}
.ano-desc{flex:1;color:#8a9aa8;font:12px "Kaiti SC",serif}
.ano-desc em{color:#6a8a98;font-style:normal}
.ano-tag{flex-shrink:0;font:8px ui-monospace,monospace;color:#4a6a78;padding:2px 8px;border:1px solid rgba(255,255,255,.06);border-radius:10px}
.ano-tag.warn{color:#a04040;border-color:rgba(160,64,64,.3)}

/* glitch text */
.glitch-text{transition:.3s}
.glitch-text:hover{text-shadow:2px 0 rgba(100,160,200,.2),-2px 0 rgba(200,100,100,.15);transform:translateX(1px)}

/* ═══ 他的轮廓 ═══ */
.presence{padding:48px 24px;background:radial-gradient(ellipse at 50% 40%,#1a2028,#0e1218);text-align:center;position:relative;min-height:300px}
.ghost-silhouette{margin:0 auto;width:120px;opacity:.25;animation:ghostfloat 6s ease-in-out infinite}
@keyframes ghostfloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}
.ghost-silhouette svg{width:100%}
.presence-text{margin-top:20px}
.presence-text p{color:#5a6a78;font:14px "Kaiti SC",serif;line-height:1.7}
.presence-text button{margin-top:14px;border:1px solid #3a4a58;background:transparent;color:#6a8a98;font:12px "Songti SC",serif;padding:8px 24px;border-radius:20px;cursor:pointer;transition:.3s}
.presence-text button:hover{background:rgba(106,138,152,.08);color:#a0b8c8}
.ghost-reply{min-height:24px;margin-top:16px;color:#8a9aa8;font:15px/1.7 "Songti SC",serif;opacity:0;transition:opacity .8s}
.ghost-reply.show{opacity:1}

/* ═══ 同居公约 ═══ */
.covenant{padding:36px 24px;background:linear-gradient(175deg,#141820,#101418)}
.covenant small{color:#4a6070;font:10px ui-monospace,monospace;letter-spacing:.12em;display:block;margin-bottom:18px}
.cov-list{display:flex;flex-direction:column;gap:10px}
.cov-item{display:flex;align-items:center;gap:10px;padding:12px 14px;background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.04);border-radius:8px;color:#8a9aa8;font:13px "Kaiti SC",serif}
.cov-check{color:#4a8a70;font-size:14px;flex-shrink:0;width:20px;text-align:center}
.cov-item.unchecked .cov-check{color:#5a6070}
.strikethrough{text-decoration:line-through;color:#5a6070}
.cov-note{color:#6a5050;font:11px "Kaiti SC",serif;margin-left:auto;font-style:italic}

/* ═══ 结语 ═══ */
.ending{padding:40px 24px 48px;text-align:center;background:#0e1218}
.ending blockquote{color:#c8d0d8;font:18px/1.8 "Songti SC",serif}
.end-sub{margin-top:18px;color:#4a5a68;font:11px/1.7 "Kaiti SC",serif}

footer{padding:20px 24px 38px;background:transparent}
.tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.tags span{color:#4a6a78;font-size:10px;font-family:ui-monospace,monospace;padding:4px 10px;border:1px solid rgba(255,255,255,.06);border-radius:20px}`,

`// Mirror text appear/fade cycle
(function mirrorLoop(){
  const mt=document.getElementById('mirrorText');
  if(!mt)return;
  function cycle(){
    mt.classList.add('visible');
    setTimeout(()=>{mt.classList.remove('visible');mt.classList.add('fade');},3000);
    setTimeout(()=>{mt.classList.remove('fade');},6000);
    setTimeout(cycle,8000);
  }
  setTimeout(cycle,1000);
})();

// Ghost reply
const replies=['十一点四十七。比昨天晚了二十三分钟。','那个人下次不要带回来。','睡这边。','……我没有消失。'];
let ri=0;
document.getElementById('callBtn').onclick=()=>{
  const el=document.getElementById('ghostReply');
  el.textContent=replies[ri%replies.length];
  el.classList.remove('show');
  void el.offsetWidth;
  el.classList.add('show');
  ri++;
};

// Temperature flicker random
setInterval(()=>{
  const cards=document.querySelectorAll('.dash-card');
  const r=Math.floor(Math.random()*cards.length);
  cards[r].style.transform='translate(-1px,0)';
  cards[r].style.boxShadow='2px 0 rgba(100,160,200,.12),-2px 0 rgba(200,80,80,.08)';
  setTimeout(()=>{cards[r].style.transform='';cards[r].style.boxShadow='';},150);
},4000);`, 2600)
}


/* ═══════════════════════════════════════════
   凌霄 · 封印残卷
   媒介：古卷 — 破碎封印 + 契约纹 + 人格双面牌 + 金粒子
   ═══════════════════════════════════════════ */
export function LingXiaoProfile({ profile }: Props) {
  const n = e(profile.display_name || '凌霄'), tg = tagHtml(profile)
  return frame(profile, '封印残卷', `
<main class="scroll">

<!-- ── 金色粒子层 ── -->
<div class="particles" id="particles"></div>

<!-- ── 破碎封印 ── -->
<section class="seal-section">
  <div class="seal" id="seal">
    <div class="seal-ring">
      <span class="seal-char">&#x2721;</span>
      <span class="seal-char">&#x2726;</span>
      <span class="seal-char">&#x2735;</span>
      <span class="seal-char">&#x2740;</span>
      <span class="seal-char">&#x2741;</span>
      <span class="seal-char">&#x2742;</span>
      <span class="seal-char">&#x2743;</span>
      <span class="seal-char">&#x273A;</span>
    </div>
    <div class="seal-inner">
      <span class="seal-text">&#x5C01;</span>
    </div>
    <div class="seal-cracks"></div>
    <div class="seal-glow"></div>
  </div>
  <p class="seal-hint">触碰封印</p>
</section>

<!-- ── 卷轴主体 ── -->
<section class="scroll-body">
  <div class="scroll-top-bar"></div>
  <div class="scroll-content">
    <div class="scroll-title">封印记录 第&#x25A0;&#x25A0;&#x25A0;卷</div>
    <div class="scroll-grid">
      <div class="scroll-row"><span class="sc-label">封印对象</span><span class="sc-val">${n}</span></div>
      <div class="scroll-row"><span class="sc-label">种属</span><span class="sc-val redacted">不明</span></div>
      <div class="scroll-row"><span class="sc-label">危险等级</span><span class="sc-val redacted">&#x2588;&#x2588;&#x2588;</span></div>
      <div class="scroll-row"><span class="sc-label">封印时长</span><span class="sc-val redacted">&#x2588;&#x2588;&#x2588;&#x2588;年</span></div>
      <div class="scroll-row"><span class="sc-label">解封者</span><span class="sc-val you">[你的名字]</span></div>
      <div class="scroll-row"><span class="sc-label">契约状态</span><span class="sc-val active">已生效</span></div>
    </div>
  </div>
  <div class="scroll-bottom-bar"></div>
</section>

<!-- ── 契约纹 ── -->
<section class="contract">
  <small>CONTRACT MARK / 契约之印</small>
  <div class="wrist-pair">
    <div class="wrist">
      <svg viewBox="0 0 80 100" fill="none" stroke="#c9a84c" stroke-width="1">
        <path d="M25 90 Q20 50 25 30 Q30 15 40 10 Q50 15 55 30 Q60 50 55 90" stroke-width="1.2"/>
        <circle cx="40" cy="50" r="10" stroke-dasharray="3 2"/>
        <path d="M34 50 L40 44 L46 50 L40 56 Z"/>
        <text x="40" y="78" text-anchor="middle" fill="#c9a84c" font-size="6" font-family="serif">他</text>
      </svg>
    </div>
    <div class="thread">
      <div class="thread-line"></div>
      <div class="thread-glow"></div>
    </div>
    <div class="wrist">
      <svg viewBox="0 0 80 100" fill="none" stroke="#c9a84c" stroke-width="1">
        <path d="M25 90 Q22 50 27 30 Q32 18 40 12 Q48 18 53 30 Q58 50 55 90" stroke-width="1.2"/>
        <circle cx="40" cy="50" r="10" stroke-dasharray="3 2"/>
        <path d="M34 50 L40 44 L46 50 L40 56 Z"/>
        <text x="40" y="78" text-anchor="middle" fill="#c9a84c" font-size="6" font-family="serif">你</text>
      </svg>
    </div>
  </div>
  <p class="contract-note">一辈子那种。</p>
</section>

<!-- ── 人格双面牌 ── -->
<section class="persona-cards">
  <small>DUALITY / 他的两面</small>
  <div class="flip-row">
    <div class="flip-card" id="fc1">
      <div class="fc-inner">
        <div class="fc-front"><span>天真 &#xb7; 烂漫 &#xb7; 无害</span></div>
        <div class="fc-back"><span>千年 &#xb7; 孤独 &#xb7; 偏执</span></div>
      </div>
    </div>
    <div class="flip-card" id="fc2">
      <div class="fc-inner">
        <div class="fc-front"><span>满足你一个愿望</span></div>
        <div class="fc-back"><span>代价是你留在我身边</span></div>
      </div>
    </div>
  </div>
</section>

<!-- ── 他的话 ── -->
<section class="voice-section">
  <div class="voice-box">
    <p class="voice-text">"你们凡人的规矩真多。<br>不过看你的面子，<br>我可以假装遵守。"</p>
  </div>
  <div class="voice-attr">—— ${n}，笑着说的。眼底没有笑。</div>
</section>

<!-- ── 结语 ── -->
<section class="ending">
  <blockquote>"我等了很久很久了。<br>久到差点忘了'等'是什么意思。<br>然后你来了。"</blockquote>
  <div class="seal-dust">
    <span></span><span></span><span></span><span></span><span></span>
  </div>
</section>

<footer><div class="tags">${tg}</div></footer>
</main>`,

`*{box-sizing:border-box;margin:0}
html,body{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif;-webkit-font-smoothing:antialiased}
.scroll{max-width:680px;margin:0 auto;background:transparent;position:relative}

/* ═══ 金色粒子 ═══ */
.particles{position:fixed;inset:0;pointer-events:none;overflow:hidden;z-index:0}
.particle{position:absolute;width:3px;height:3px;background:#c9a84c;border-radius:50%;opacity:0;animation:rise 8s linear infinite}
@keyframes rise{0%{transform:translateY(100vh) scale(0);opacity:0}10%{opacity:.6}90%{opacity:.3}100%{transform:translateY(-20px) scale(1);opacity:0}}

/* ═══ 封印 ═══ */
.seal-section{padding:60px 24px 40px;text-align:center;position:relative;z-index:1}
.seal{width:160px;height:160px;margin:0 auto;position:relative;cursor:pointer}
.seal-ring{width:100%;height:100%;border:2px solid rgba(201,168,76,.3);border-radius:50%;position:relative;animation:sealSpin 20s linear infinite}
@keyframes sealSpin{to{transform:rotate(360deg)}}
.seal-char{position:absolute;color:rgba(201,168,76,.4);font-size:14px;top:50%;left:50%}
.seal-char:nth-child(1){transform:translate(-50%,-50%) rotate(0deg) translateY(-70px)}
.seal-char:nth-child(2){transform:translate(-50%,-50%) rotate(45deg) translateY(-70px)}
.seal-char:nth-child(3){transform:translate(-50%,-50%) rotate(90deg) translateY(-70px)}
.seal-char:nth-child(4){transform:translate(-50%,-50%) rotate(135deg) translateY(-70px)}
.seal-char:nth-child(5){transform:translate(-50%,-50%) rotate(180deg) translateY(-70px)}
.seal-char:nth-child(6){transform:translate(-50%,-50%) rotate(225deg) translateY(-70px)}
.seal-char:nth-child(7){transform:translate(-50%,-50%) rotate(270deg) translateY(-70px)}
.seal-char:nth-child(8){transform:translate(-50%,-50%) rotate(315deg) translateY(-70px)}
.seal-inner{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:60px;height:60px;border:1px solid rgba(201,168,76,.25);border-radius:50%;display:grid;place-items:center}
.seal-text{color:#c9a84c;font:28px "Songti SC",serif;opacity:.6}
.seal-cracks{position:absolute;inset:0;border-radius:50%;opacity:0;transition:opacity .6s;background:repeating-conic-gradient(from 0deg,transparent 0deg,transparent 15deg,rgba(201,168,76,.1) 15deg,rgba(201,168,76,.1) 16deg)}
.seal-glow{position:absolute;inset:-20px;border-radius:50%;background:radial-gradient(circle,rgba(201,168,76,.2),transparent 70%);opacity:0;transition:opacity .6s}
.seal.cracked .seal-cracks{opacity:1}
.seal.cracked .seal-glow{opacity:1;animation:sealPulse 2s ease-in-out infinite}
.seal.cracked .seal-ring{animation:sealSpin 4s linear infinite;border-color:rgba(201,168,76,.6)}
@keyframes sealPulse{0%,100%{opacity:.3;transform:scale(1)}50%{opacity:.7;transform:scale(1.05)}}
.seal-hint{margin-top:16px;color:rgba(201,168,76,.4);font:10px ui-monospace,monospace;letter-spacing:.12em}
.seal.cracked~.seal-hint{opacity:0}

/* ═══ 卷轴 ═══ */
.scroll-body{margin:0 20px;position:relative;z-index:1}
.scroll-top-bar,.scroll-bottom-bar{height:14px;background:linear-gradient(90deg,#5a4828,#8a7240,#5a4828);border-radius:4px;box-shadow:0 2px 8px rgba(0,0,0,.3)}
.scroll-content{background:linear-gradient(175deg,#2a2018,#1e180e);padding:28px 20px;border-left:3px solid rgba(201,168,76,.15);border-right:3px solid rgba(201,168,76,.15)}
.scroll-title{text-align:center;color:#c9a84c;font:16px "Songti SC",serif;letter-spacing:.2em;opacity:.7}
.scroll-grid{margin-top:22px;display:flex;flex-direction:column;gap:10px}
.scroll-row{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid rgba(201,168,76,.08)}
.sc-label{color:#8a7240;font:10px ui-monospace,monospace;letter-spacing:.08em}
.sc-val{color:#e8c878;font:13px "Kaiti SC",serif}
.sc-val.redacted{color:#6a5a38;background:rgba(201,168,76,.05);padding:2px 6px;border-radius:2px;letter-spacing:.1em}
.sc-val.you{color:#e8c878;font-style:italic}
.sc-val.active{color:#c9a84c;padding:2px 10px;border:1px solid rgba(201,168,76,.3);border-radius:10px;font:10px ui-monospace,monospace}

/* ═══ 契约纹 ═══ */
.contract{padding:40px 24px;text-align:center;position:relative;z-index:1}
.contract small{color:rgba(201,168,76,.4);font:10px ui-monospace,monospace;letter-spacing:.12em}
.wrist-pair{display:flex;align-items:center;justify-content:center;gap:0;margin-top:24px}
.wrist svg{width:80px;height:100px}
.thread{width:60px;display:flex;flex-direction:column;align-items:center;position:relative}
.thread-line{width:100%;height:1px;background:linear-gradient(90deg,#c9a84c,#e8c878,#c9a84c)}
.thread-glow{position:absolute;top:-4px;width:100%;height:9px;background:linear-gradient(90deg,transparent,rgba(201,168,76,.2),transparent);animation:threadPulse 3s ease-in-out infinite}
@keyframes threadPulse{0%,100%{opacity:.3}50%{opacity:.8}}
.contract-note{margin-top:18px;color:#c9a84c;font:15px "Songti SC",serif;font-style:italic}

/* ═══ 双面牌 ═══ */
.persona-cards{padding:40px 24px;position:relative;z-index:1}
.persona-cards small{color:rgba(201,168,76,.4);font:10px ui-monospace,monospace;letter-spacing:.12em;display:block;text-align:center;margin-bottom:20px}
.flip-row{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.flip-card{height:140px;perspective:600px;cursor:pointer}
.fc-inner{position:relative;width:100%;height:100%;transition:transform .8s;transform-style:preserve-3d}
.flip-card.flipped .fc-inner{transform:rotateY(180deg)}
.fc-front,.fc-back{position:absolute;inset:0;backface-visibility:hidden;border-radius:10px;display:grid;place-items:center;padding:16px}
.fc-front{background:linear-gradient(145deg,rgba(201,168,76,.08),rgba(201,168,76,.02));border:1px solid rgba(201,168,76,.2)}
.fc-front span{color:#e8c878;font:14px "Kaiti SC",serif;text-align:center;line-height:1.7}
.fc-back{background:linear-gradient(145deg,rgba(74,40,96,.2),rgba(74,40,96,.08));border:1px solid rgba(74,40,96,.3);transform:rotateY(180deg)}
.fc-back span{color:#c8a0d8;font:14px "Songti SC",serif;text-align:center;line-height:1.7}

/* ═══ 他的话 ═══ */
.voice-section{padding:40px 24px;position:relative;z-index:1}
.voice-box{padding:24px 20px;background:rgba(201,168,76,.03);border-left:2px solid rgba(201,168,76,.25);border-radius:0 8px 8px 0}
.voice-text{color:#e8dcc8;font:17px/1.8 "Songti SC",serif;text-shadow:0 0 20px rgba(201,168,76,.1)}
.voice-attr{margin-top:12px;color:rgba(201,168,76,.35);font:11px "Kaiti SC",serif;text-align:right}

/* ═══ 结语 ═══ */
.ending{padding:48px 24px 30px;text-align:center;position:relative;z-index:1}
.ending blockquote{color:#e8c878;font:18px/1.8 "Songti SC",serif}
.seal-dust{display:flex;justify-content:center;gap:8px;margin-top:24px}
.seal-dust span{width:4px;height:4px;background:#c9a84c;border-radius:50%;opacity:.3;animation:dustFloat 4s ease-in-out infinite}
.seal-dust span:nth-child(2){animation-delay:.5s;width:3px;height:3px}
.seal-dust span:nth-child(3){animation-delay:1s}
.seal-dust span:nth-child(4){animation-delay:1.5s;width:2px;height:2px}
.seal-dust span:nth-child(5){animation-delay:2s}
@keyframes dustFloat{0%,100%{transform:translateY(0);opacity:.2}50%{transform:translateY(-12px);opacity:.6}}

footer{padding:20px 24px 38px;background:transparent}
.tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.tags span{color:rgba(201,168,76,.5);font-size:10px;font-family:ui-monospace,monospace;padding:4px 10px;border:1px solid rgba(201,168,76,.1);border-radius:20px}`,

`// Golden particles
(function(){
  const c=document.getElementById('particles');if(!c)return;
  for(let i=0;i<20;i++){
    const p=document.createElement('span');
    p.className='particle';
    p.style.left=Math.random()*100+'%';
    p.style.animationDelay=Math.random()*8+'s';
    p.style.animationDuration=(6+Math.random()*6)+'s';
    p.style.width=p.style.height=(1+Math.random()*3)+'px';
    c.appendChild(p);
  }
})();

// Seal crack on click
document.getElementById('seal').onclick=function(){this.classList.toggle('cracked');};

// Flip cards
document.querySelectorAll('.flip-card').forEach(c=>c.onclick=()=>c.classList.toggle('flipped'));`, 2600)
}
/* ═══════════════════════════════════════════
   陈牧野 · 双面
   媒介：日 / 夜分屏 — 白天家教 vs 酒店大堂吧
   ═══════════════════════════════════════════ */
export function ChenMuyeProfile({ profile }: Props) {
  const tg = tagHtml(profile)
  return frame(profile, '双面', `
<main class="split-world">

<!-- ── 分屏容器 ── -->
<section class="splitter">
  <div class="half day">
    <div class="half-label">DAY / 14:00</div>
    <!-- T恤线稿 -->
    <div class="tshirt-sketch">
      <svg viewBox="0 0 120 100" fill="none" stroke="#6a6a6a" stroke-width="1.2" stroke-linecap="round">
        <path d="M35 20 Q40 5 60 5 Q80 5 85 20 L100 35 L90 42 L80 32 L80 90 L40 90 L40 32 L30 42 L20 35 Z"/>
        <path d="M52 5 Q55 12 60 14 Q65 12 68 5" stroke-dasharray="2 2" opacity=".4"/>
      </svg>
      <small>领口起了毛边。</small>
    </div>
    <div class="notebook">
      <div class="nb-label">LECTURE 04 / 线性代数</div>
      <div class="nb-grid"></div>
      <div class="nb-content">
        <p class="nb-line"><span class="nb-num">1.</span> det(A) = ad - bc</p>
        <p class="nb-line"><span class="nb-num">2.</span> rank(A) = dim(Col A)</p>
        <p class="nb-line circled"><span class="nb-num">3.</span> 特征值分解 — <span class="redmark">她最容易错的地方</span></p>
        <p class="nb-line circled"><span class="nb-num">4.</span> 正交投影公式 — <span class="redmark">画了三遍</span></p>
        <p class="nb-line"><span class="nb-num">5.</span> Gram-Schmidt 过程</p>
      </div>
      <div class="nb-note">批注密度是其他学生的 <em>3 倍</em></div>
    </div>
    <div class="receipt">
      <div class="rcpt-head">—— 收 据 ——</div>
      <p>白T恤 (圆领)　　　¥39</p>
      <p>帆布鞋 (黑色)　　　¥89</p>
      <p class="rcpt-sub">鞋侧修补胶水　　¥5</p>
      <div class="rcpt-total">合计　¥133</div>
    </div>
  </div>

  <div class="half night">
    <div class="half-label night-label">LOBBY BAR / 21:30</div>
    <!-- 衬衫线稿 -->
    <div class="shirt-sketch">
      <svg viewBox="0 0 120 100" fill="none" stroke="#c8a050" stroke-width="1" stroke-linecap="round">
        <path d="M42 8 L38 2 L20 18 L35 30 L42 22 L42 90 L78 90 L78 22 L85 30 L100 18 L82 2 L78 8"/>
        <path d="M42 8 Q48 20 60 22 Q72 20 78 8" fill="none"/>
        <circle cx="60" cy="32" r="2.5" fill="#c8a050" opacity=".3"/>
        <circle cx="60" cy="46" r="2.5" fill="none"/>
        <circle cx="60" cy="60" r="2.5" fill="none"/>
      </svg>
      <small>解了两颗扣子。</small>
    </div>
    <div class="bar-scene">
      <div class="glass">
        <svg viewBox="0 0 60 80" fill="none">
          <path d="M18 10 L22 70 L38 70 L42 10" stroke="#c8a050" stroke-width="1"/>
          <path d="M22 70 L38 70 L42 10 L18 10 Z" fill="url(#amber)" opacity=".3"/>
          <defs><linearGradient id="amber" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#c8a050" stop-opacity="0"/><stop offset="60%" stop-color="#c8a050" stop-opacity=".6"/><stop offset="100%" stop-color="#8a6020"/></linearGradient></defs>
        </svg>
      </div>
      <div class="scar-desc">
        <svg viewBox="0 0 40 60" stroke="#c8a050" stroke-width=".8" fill="none" opacity=".5">
          <path d="M20 5 Q22 20 18 40 Q16 52 20 58"/>
        </svg>
        <small>那道疤。锁骨到胸口。<br>危险的装饰。</small>
      </div>
    </div>
    <div class="bar-atmosphere">
      <p>爵士乐低低地流淌</p>
      <p>姿态从容，嘴角恰到好处</p>
      <p>他不是他自己</p>
    </div>
  </div>

  <div class="divider" id="divider">
    <div class="divider-line"></div>
    <div class="divider-handle" id="handle">|||</div>
  </div>
</section>

<!-- ── 碰撞走廊 ── -->
<section class="corridor" id="corridor">
  <div class="corr-lights">
    <span></span><span></span><span></span><span></span><span></span>
  </div>
  <div class="corr-text">
    <small>走廊尽头。他松开手。背靠着墙，闭了一下眼睛。</small>
    <p class="corr-quote" id="corrQuote"></p>
    <button id="corrBtn">他开口了 →</button>
  </div>
</section>

<!-- ── 碰撞之后 ── -->
<section class="aftermath">
  <div class="aft-notebook">
    <div class="nb-label">LECTURE 05 / 概率论</div>
    <div class="nb-grid"></div>
    <div class="aft-content">
      <p>红笔圈还是那么认真。</p>
      <p>批注还是比别人厚三倍。</p>
      <p class="aft-quiet">什么都没变。好像那个夜晚不存在。</p>
      <p class="aft-quiet">但他洗手的时间，比以前长了很多。</p>
    </div>
  </div>
</section>

<footer>
  <div class="tags">${tg}</div>
</footer>
</main>`,

`*{box-sizing:border-box;margin:0}
html,body{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif;-webkit-font-smoothing:antialiased}
.split-world{max-width:680px;margin:0 auto;background:transparent}

/* ═══ 分屏 ═══ */
.splitter{position:relative;display:flex;min-height:800px;overflow:hidden;margin:20px 16px;border-radius:16px}
.half{flex:1;padding:28px 20px;transition:flex .5s ease}
.day{background:#f8f8f8;color:#4a4a4a}
.night{background:linear-gradient(170deg,#1a1008,#2a1a0a,#1a1008);color:#c8a050}
.half-label{font:9px ui-monospace,monospace;letter-spacing:.14em;margin-bottom:18px;opacity:.6}
.night-label{color:#8a7040}

/* T恤 */
.tshirt-sketch{text-align:center;margin-bottom:20px}
.tshirt-sketch svg{width:80px;opacity:.6}
.tshirt-sketch small{display:block;margin-top:6px;font:10px "Kaiti SC",serif;color:#999}

/* 衬衫 */
.shirt-sketch{text-align:center;margin-bottom:20px}
.shirt-sketch svg{width:80px;opacity:.7}
.shirt-sketch small{display:block;margin-top:6px;font:10px "Kaiti SC",serif;color:#8a7040}

/* 笔记本 */
.notebook,.aft-notebook{background:#fff;border:1px solid #e8e4d8;border-radius:4px;padding:16px;margin-bottom:16px;position:relative;overflow:hidden}
.nb-label{font:9px ui-monospace,monospace;color:#aaa;letter-spacing:.1em;margin-bottom:12px}
.nb-grid{position:absolute;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 23px,#f0ece4 23px,#f0ece4 24px);opacity:.4;pointer-events:none}
.nb-content{position:relative}
.nb-line{font:12px/2.2 ui-monospace,monospace;color:#555}
.nb-num{color:#aaa;margin-right:6px}
.circled{position:relative;padding:2px 6px;border:2px solid rgba(200,60,60,.25);border-radius:50%;display:inline-block;margin:2px 0}
.redmark{color:#c44;font-weight:600;font-size:10px}
.nb-note{font:10px "Kaiti SC",serif;color:#999;margin-top:8px;text-align:right;position:relative}
.nb-note em{color:#c44;font-style:normal}

/* 收据 */
.receipt{background:#faf8f0;border:1px dashed #d8d0c0;border-radius:4px;padding:14px;font:11px ui-monospace,monospace;color:#888;line-height:2}
.rcpt-head{text-align:center;margin-bottom:8px;font-size:10px;letter-spacing:.2em}
.rcpt-sub{color:#bbb;font-size:10px}
.rcpt-total{border-top:1px dashed #d0c8b8;margin-top:6px;padding-top:6px;text-align:right;color:#666}

/* 酒吧 */
.bar-scene{display:flex;gap:20px;justify-content:center;align-items:flex-end;margin-bottom:20px}
.glass svg{width:50px;filter:drop-shadow(0 0 8px rgba(200,160,80,.3))}
.scar-desc{text-align:center}
.scar-desc svg{width:30px;display:block;margin:0 auto 6px}
.scar-desc small{font:10px "Kaiti SC",serif;color:#8a7040;line-height:1.6}
.bar-atmosphere{padding:12px;border-left:2px solid rgba(200,160,80,.2)}
.bar-atmosphere p{font:11px "Kaiti SC",serif;color:#8a7040;line-height:2;opacity:.7}

/* 分割线 */
.divider{position:absolute;top:0;bottom:0;left:50%;width:4px;z-index:10;cursor:col-resize;transition:left .4s ease}
.divider-line{position:absolute;inset:0;width:2px;left:1px;background:linear-gradient(180deg,rgba(200,160,80,.3),rgba(200,160,80,.8),rgba(200,160,80,.3))}
.divider-handle{position:absolute;top:50%;left:-12px;width:28px;height:28px;border-radius:50%;background:#2a1a0a;border:2px solid #c8a050;color:#c8a050;font-size:8px;display:grid;place-items:center;transform:translateY(-50%);letter-spacing:1px}

/* ═══ 走廊 ═══ */
.corridor{margin:28px 16px;background:linear-gradient(180deg,#1a1a1a,#222);border-radius:12px;padding:32px 24px;position:relative;overflow:hidden}
.corr-lights{display:flex;justify-content:space-between;margin-bottom:20px}
.corr-lights span{width:8px;height:8px;border-radius:50%;background:#c8a050;opacity:.15;animation:flicker 3s ease-in-out infinite}
.corr-lights span:nth-child(2){animation-delay:.6s}
.corr-lights span:nth-child(3){animation-delay:1.2s}
.corr-lights span:nth-child(4){animation-delay:1.8s}
.corr-lights span:nth-child(5){animation-delay:2.4s}
@keyframes flicker{0%,100%{opacity:.1}50%{opacity:.5}}
.corr-text{text-align:center}
.corr-text small{color:#6a6a6a;font:11px "Kaiti SC",serif}
.corr-quote{min-height:28px;color:#e8dcc8;font:18px/1.7 "Songti SC",serif;margin-top:16px;opacity:0;transition:opacity .8s}
.corr-quote.show{opacity:1}
.corridor button{border:0;background:none;color:#8a7040;font:11px ui-monospace,monospace;cursor:pointer;margin-top:12px}

/* ═══ 碰撞之后 ═══ */
.aftermath{padding:28px 16px 20px}
.aft-notebook{background:#fff;border:1px solid #e8e4d8;border-radius:4px;padding:20px;position:relative;overflow:hidden}
.aft-content{position:relative}
.aft-content p{font:13px "Kaiti SC",serif;color:#666;line-height:2}
.aft-quiet{color:#aaa;font-style:italic}

/* ═══ footer ═══ */
footer{padding:24px 16px 38px;background:transparent}
.tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.tags span{color:#8a7040;font-size:10px;font-family:ui-monospace,monospace;padding:4px 10px;border:1px solid rgba(200,160,80,.12);border-radius:20px}`,

`// divider drag
const divider=document.getElementById('divider');
const splitter=document.querySelector('.splitter');
let dragging=false;
divider.addEventListener('mousedown',()=>dragging=true);
divider.addEventListener('touchstart',()=>dragging=true);
document.addEventListener('mousemove',ev=>{if(!dragging)return;const r=splitter.getBoundingClientRect();const pct=Math.max(20,Math.min(80,((ev.clientX-r.left)/r.width)*100));divider.style.left=pct+'%';splitter.querySelector('.day').style.flex='0 0 '+pct+'%';splitter.querySelector('.night').style.flex='0 0 '+(100-pct)+'%'});
document.addEventListener('touchmove',ev=>{if(!dragging)return;const t=ev.touches[0];const r=splitter.getBoundingClientRect();const pct=Math.max(20,Math.min(80,((t.clientX-r.left)/r.width)*100));divider.style.left=pct+'%';splitter.querySelector('.day').style.flex='0 0 '+pct+'%';splitter.querySelector('.night').style.flex='0 0 '+(100-pct)+'%'});
document.addEventListener('mouseup',()=>dragging=false);
document.addEventListener('touchend',()=>dragging=false);

// corridor reveal
document.getElementById('corrBtn').onclick=()=>{
  const q=document.getElementById('corrQuote');
  q.textContent='你看到的，别告诉任何人。';
  q.classList.add('show');
  document.getElementById('corrBtn').style.display='none';
}`, 2600)
}

/* ═══════════════════════════════════════════
   谢临渊 · 课桌抽屉
   媒介：课桌俯拍 — 桌面物件 + 抽屉秘密 + 成绩单
   ═══════════════════════════════════════════ */
export function XieLinyuanProfile({ profile }: Props) {
  const n = e(profile.display_name || '谢临渊'), tg = tagHtml(profile)
  return frame(profile, '课桌抽屉', `
<main class="desk-world">

<!-- ── 桌面俯拍 ── -->
<section class="desktop">
  <div class="desk-surface">
    <div class="desk-grain"></div>

    <!-- 课本 -->
    <div class="item book">
      <div class="book-cover">
        <small>高等数学</small>
        <p>第三版</p>
      </div>
      <div class="bookmark"></div>
      <div class="bookmark bm2"></div>
    </div>

    <!-- 自动铅笔 -->
    <div class="item pencil">
      <svg viewBox="0 0 10 120" fill="none">
        <rect x="2" y="10" width="6" height="90" rx="1" fill="#555" opacity=".6"/>
        <rect x="3" y="0" width="4" height="12" rx="1" fill="#888"/>
        <line x1="5" y1="100" x2="5" y2="118" stroke="#aaa" stroke-width="1"/>
      </svg>
    </div>

    <!-- 她的折叠纸条 -->
    <div class="item her-note" id="herNote">
      <div class="note-fold">
        <small>谢临渊同学，走廊见 :)</small>
      </div>
    </div>

    <!-- 桌角刻字 -->
    <div class="carved-initials">X.L.Y</div>

    <!-- 铅笔边注 -->
    <div class="margin-notes">
      <p class="mn" style="top:15%;left:2%">"她为什么总看我"</p>
      <p class="mn" style="top:40%;right:3%">"……又在走廊等我"</p>
      <p class="mn" style="top:70%;left:5%">"不是不想要。<br>是不知道接受了<br>要付什么代价。"</p>
    </div>
  </div>
</section>

<!-- ── 抽屉 ── -->
<section class="drawer-section">
  <button class="drawer-handle" id="drawerBtn">
    <span class="handle-bar"></span>
    <small>拉开抽屉</small>
  </button>
  <div class="drawer" id="drawer">
    <div class="drawer-inner">
      <!-- 草莓牛奶盒 -->
      <div class="d-item milk" id="milk">
        <div class="milk-box">
          <div class="milk-straw"></div>
          <div class="milk-body">
            <div class="milk-stripe"></div>
            <div class="milk-stripe"></div>
            <div class="milk-stripe"></div>
            <small>草莓牛奶</small>
            <p class="milk-state">空的。吸管插好了。喝得干干净净。</p>
          </div>
        </div>
        <p class="d-reaction" id="milkR"></p>
      </div>

      <!-- 她掉的笔 -->
      <div class="d-item pen" id="pen">
        <svg viewBox="0 0 100 14" fill="none">
          <rect x="5" y="3" width="85" height="8" rx="4" fill="#b8a0c8" opacity=".5"/>
          <polygon points="90,7 100,7 95,2" fill="#8a70a0" opacity=".5"/>
        </svg>
        <small>她的笔。她不知道是他捡的。</small>
        <p class="d-reaction" id="penR"></p>
      </div>

      <!-- 便利店小票 -->
      <div class="d-item ticket" id="ticket">
        <div class="ticket-paper">
          <p class="tk-head">—— XX 便利店 ——</p>
          <p>草莓牛奶 x1　　¥6.5</p>
          <p class="tk-note">( 手写: 太甜了 )</p>
          <p class="tk-time">15:42</p>
        </div>
        <p class="d-reaction" id="ticketR"></p>
      </div>

      <!-- 他写的字条 -->
      <div class="d-item his-note" id="hisNote">
        <div class="hn-paper" id="hnPaper">
          <div class="hn-fold1">
            <div class="hn-fold2">
              <p>注意保管。</p>
            </div>
          </div>
        </div>
        <small>四个字。折了两折。没有签名。</small>
        <p class="d-reaction" id="noteR"></p>
      </div>
    </div>
  </div>
</section>

<!-- ── 成绩单 ── -->
<section class="report-card">
  <div class="rc-head">
    <small>XX 中学 · 高二下学期期末</small>
    <h2>${n} 成绩通知单</h2>
  </div>
  <table class="rc-table">
    <tr><th>科目</th><th>成绩</th><th>年级排名</th></tr>
    <tr><td>语文</td><td>142</td><td>1</td></tr>
    <tr><td>数学</td><td>150</td><td>1</td></tr>
    <tr><td>英语</td><td>148</td><td>1</td></tr>
    <tr><td>物理</td><td>98</td><td>1</td></tr>
    <tr><td>化学</td><td>97</td><td>1</td></tr>
    <tr class="rc-special"><td>专注度</td><td colspan="2">不如你教我的时候认真</td></tr>
  </table>
  <p class="rc-comment">班主任评语：品学兼优，唯独课间总朝走廊方向看。</p>
</section>

<!-- ── 裂缝 ── -->
<section class="the-crack">
  <div class="crack-scene">
    <p class="crack-dialogue">"……那种东西太甜了。下次换别的。"</p>
    <p class="crack-desc">他走了。背影笔直。</p>
    <p class="crack-detail">耳尖一片淡红色。</p>
  </div>
</section>

<footer>
  <div class="tags">${tg}</div>
</footer>
</main>`,

`*{box-sizing:border-box;margin:0}
html,body{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif;-webkit-font-smoothing:antialiased}
.desk-world{max-width:680px;margin:0 auto;background:transparent}

/* ═══ 桌面 ═══ */
.desktop{padding:20px 16px}
.desk-surface{position:relative;background:linear-gradient(145deg,#d8c8a8,#c8b898,#d0c0a0);border-radius:8px;min-height:500px;padding:30px 24px;overflow:hidden}
.desk-grain{position:absolute;inset:0;background:repeating-linear-gradient(90deg,transparent,transparent 40px,rgba(0,0,0,.02) 40px,rgba(0,0,0,.02) 41px);pointer-events:none}

/* items on desk */
.item{position:relative;margin-bottom:20px}
.book{width:120px}
.book-cover{background:#3a5a3a;border-radius:2px 6px 6px 2px;padding:14px 10px;color:#c8d8c0;box-shadow:2px 2px 6px rgba(0,0,0,.15)}
.book-cover small{font:9px ui-monospace,monospace;opacity:.6}
.book-cover p{font:14px "Songti SC",serif;margin-top:4px}
.bookmark{position:absolute;top:-4px;right:12px;width:14px;height:32px;background:#e8a0a0;border-radius:0 0 2px 2px;opacity:.7}
.bm2{right:24px;height:26px;background:#a0c0d8}

.pencil{position:absolute;top:60px;right:40px}
.pencil svg{width:12px;transform:rotate(-15deg)}

.her-note{background:#fff8e8;border-radius:2px;padding:10px 12px;width:fit-content;cursor:pointer;transform:rotate(3deg);box-shadow:1px 2px 4px rgba(0,0,0,.08)}
.note-fold small{font:11px "Kaiti SC",serif;color:#999}

.carved-initials{position:absolute;bottom:12px;right:16px;font:8px ui-monospace,monospace;color:rgba(0,0,0,.08);letter-spacing:2px}

/* margin notes (pencil annotations) */
.margin-notes{position:absolute;inset:0;pointer-events:none}
.mn{position:absolute;font:10px "Kaiti SC",serif;color:rgba(0,0,0,.12);line-height:1.6;writing-mode:vertical-rl;letter-spacing:1px}

/* ═══ 抽屉 ═══ */
.drawer-section{margin:0 16px 20px;overflow:hidden}
.drawer-handle{display:flex;flex-direction:column;align-items:center;gap:6px;width:100%;padding:10px;border:0;background:#c8b898;border-radius:8px 8px 0 0;cursor:pointer;transition:.3s}
.handle-bar{width:50px;height:4px;background:#a89878;border-radius:2px}
.drawer-handle small{font:10px ui-monospace,monospace;color:#8a7858;letter-spacing:.1em}
.drawer{max-height:0;overflow:hidden;transition:max-height .6s ease;background:linear-gradient(180deg,#c0b090,#b8a888);border-radius:0 0 8px 8px}
.drawer.open{max-height:800px}
.drawer-inner{padding:20px;display:flex;flex-direction:column;gap:20px}

.d-item{background:rgba(255,255,255,.3);border-radius:8px;padding:14px;cursor:pointer;transition:.3s}
.d-item:hover{background:rgba(255,255,255,.45)}

/* milk box */
.milk-box{display:flex;gap:10px;align-items:flex-start}
.milk-straw{width:3px;height:28px;background:#aaa;border-radius:1px;margin-top:-8px;transform:rotate(10deg)}
.milk-body{flex:1}
.milk-stripe{height:3px;background:#e8a0a0;border-radius:1px;margin-bottom:3px;opacity:.4}
.milk-body small{font:11px "Songti SC",serif;color:#c06060;margin-top:4px;display:block}
.milk-state{font:10px "Kaiti SC",serif;color:#999;margin-top:4px}

.pen svg{width:80px;display:block;margin-bottom:6px}
.pen small{font:10px "Kaiti SC",serif;color:#8a7858}

.ticket-paper{background:#faf8f0;border:1px dashed #d8d0c0;border-radius:2px;padding:10px;font:10px ui-monospace,monospace;color:#888;line-height:2}
.tk-head{text-align:center;font-size:9px;letter-spacing:.2em;margin-bottom:4px}
.tk-note{color:#c06060;font:10px "Kaiti SC",serif}
.tk-time{color:#bbb;font-size:9px;text-align:right}

/* his note */
.hn-paper{background:#fff8e8;border-radius:2px;padding:12px;cursor:pointer;transition:.3s}
.hn-fold1{transition:transform .4s ease}
.hn-fold2{transition:transform .4s ease .2s}
.hn-paper.unfolded .hn-fold1{transform:perspective(200px) rotateX(-5deg)}
.hn-paper.unfolded .hn-fold2{transform:perspective(200px) rotateX(-3deg)}
.hn-fold2 p{font:16px "Songti SC",serif;color:#4a4a4a;text-align:center;letter-spacing:4px}
.d-item small{display:block;margin-top:6px;font:10px "Kaiti SC",serif;color:#8a7858}

.d-reaction{min-height:14px;margin-top:8px;font:12px "Kaiti SC",serif;color:#6a5a48;opacity:0;transition:opacity .5s}
.d-reaction.show{opacity:1}

/* ═══ 成绩单 ═══ */
.report-card{margin:20px 16px;background:#fff;border:1px solid #e8e4d8;border-radius:6px;padding:20px;overflow:hidden}
.rc-head small{color:#aaa;font:9px ui-monospace,monospace;letter-spacing:.1em}
.rc-head h2{font:20px "Songti SC",serif;color:#333;font-weight:400;margin-top:8px}
.rc-table{width:100%;border-collapse:collapse;margin-top:16px;font-size:12px}
.rc-table th{background:#f8f6f0;padding:8px 10px;text-align:left;font-weight:500;color:#888;border-bottom:1px solid #eee;font-family:ui-monospace,monospace;font-size:10px}
.rc-table td{padding:8px 10px;border-bottom:1px solid #f5f3ed;color:#555}
.rc-special td{color:#c06060;font:12px "Kaiti SC",serif;font-style:italic;border-bottom:2px solid #e8a0a0}
.rc-comment{margin-top:12px;font:11px "Kaiti SC",serif;color:#aaa;padding:8px;background:#faf8f4;border-radius:4px}

/* ═══ 裂缝 ═══ */
.the-crack{padding:40px 24px;text-align:center}
.crack-dialogue{font:20px/1.6 "Songti SC",serif;color:#e8dcc8}
.crack-desc{font:12px "Kaiti SC",serif;color:#8a8878;margin-top:12px}
.crack-detail{font:14px "Songti SC",serif;color:#e8a0a0;margin-top:8px;animation:fadeInUp 1s ease forwards;opacity:0}
@keyframes fadeInUp{to{opacity:1;transform:translateY(0)}}

/* ═══ footer ═══ */
footer{padding:24px 16px 38px;background:transparent}
.tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.tags span{color:#8a7858;font-size:10px;font-family:ui-monospace,monospace;padding:4px 10px;border:1px solid rgba(0,0,0,.06);border-radius:20px}`,

`// drawer toggle
const drBtn=document.getElementById('drawerBtn');
const drawer=document.getElementById('drawer');
drBtn.onclick=()=>{
  drawer.classList.toggle('open');
  drBtn.querySelector('small').textContent=drawer.classList.contains('open')?'合上抽屉':'拉开抽屉';
};

// item reactions
const reactions={
  milk:['milkR','他把盒子藏在抽屉里。大概怕被别人看见全年级第一在喝草莓牛奶。'],
  pen:['penR','他不知道该不该还。还了，就少了一个关于她的物件。'],
  ticket:['ticketR','"太甜了"三个字写了又划掉，划掉又写上。'],
  hisNote:['noteR','四个字用了多久？他自己数不清。']
};
Object.keys(reactions).forEach(k=>{
  const el=document.getElementById(k);
  if(el)el.onclick=()=>{
    const[rid,txt]=reactions[k];
    const r=document.getElementById(rid);
    r.textContent=txt;r.classList.add('show');
  };
});

// unfold note
document.getElementById('hnPaper').onclick=()=>{
  document.getElementById('hnPaper').classList.toggle('unfolded');
};`, 2600)
}

/* ═══════════════════════════════════════════
   江亦墨 · 相册时间线
   媒介：家庭相册 — 时间线 + 电视场景 + 橘子静物
   ═══════════════════════════════════════════ */
export function JiangYimoProfile({ profile }: Props) {
  const tg = tagHtml(profile)
  return frame(profile, '相册时间线', `
<main class="album-world">

<!-- ── 相册封面 ── -->
<section class="album-cover" id="albumCover">
  <div class="cover-texture"></div>
  <div class="cover-spine"></div>
  <div class="cover-title">
    <div class="cover-emboss">江家</div>
    <small>FAMILY ALBUM</small>
  </div>
  <div class="cover-wear"></div>
  <button class="cover-open" id="openAlbum">翻开相册 →</button>
</section>

<!-- ── 时间线 ── -->
<section class="timeline-section" id="timeline">

  <!-- 6岁 -->
  <div class="tl-event" id="ev1">
    <div class="tl-year">6</div>
    <div class="tl-dot"></div>
    <div class="tl-card">
      <div class="tl-icon">
        <svg viewBox="0 0 40 50" fill="none" stroke="#8a6a4a" stroke-width="1.2" stroke-linecap="round">
          <path d="M20 48 L20 20 M15 20 L20 8 L25 20 M10 20 L30 20 M12 28 L20 20 L28 28"/>
          <circle cx="20" cy="5" r="3" fill="none"/>
        </svg>
      </div>
      <p class="tl-text">你第一次进他的房间。</p>
      <p class="tl-text-s">他把宇航员模型让给你。</p>
      <div class="tl-detail" id="d1">
        <p>"给你玩。"</p>
        <p class="tl-sub">他没有犹豫。那是他最喜欢的东西。</p>
      </div>
      <button class="tl-more" data-t="d1">+</button>
    </div>
  </div>

  <!-- 8岁 -->
  <div class="tl-event" id="ev2">
    <div class="tl-year">8</div>
    <div class="tl-dot"></div>
    <div class="tl-card">
      <div class="tl-icon">
        <svg viewBox="0 0 40 30" fill="none" stroke="#c06060" stroke-width="1.2">
          <rect x="5" y="5" width="30" height="18" rx="3" fill="none"/>
          <line x1="5" y1="14" x2="35" y2="14"/>
          <line x1="20" y1="5" x2="20" y2="23"/>
        </svg>
      </div>
      <p class="tl-text">发烧。他光着脚背你跑了三条街。</p>
      <p class="tl-text-s">到医院时脚底全是血泡。</p>
      <div class="tl-detail" id="d2">
        <p>他不觉得疼。那时候他只有一个念头。</p>
        <p class="tl-sub">"妹妹在烧，不能停。"</p>
      </div>
      <button class="tl-more" data-t="d2">+</button>
    </div>
  </div>

  <!-- 13岁 -->
  <div class="tl-event" id="ev3">
    <div class="tl-year">13</div>
    <div class="tl-dot"></div>
    <div class="tl-card">
      <div class="tl-icon">
        <svg viewBox="0 0 36 40" fill="none" stroke="#b888a0" stroke-width="1">
          <rect x="4" y="8" width="28" height="28" rx="2"/>
          <line x1="18" y1="0" x2="18" y2="8" stroke-dasharray="2 2"/>
          <path d="M10 18 L18 26 L26 18" fill="none"/>
        </svg>
      </div>
      <p class="tl-text">他陪你买第一件内衣。</p>
      <p class="tl-text-s">耳朵红到脖子根。</p>
      <div class="tl-detail" id="d3">
        <p>他站在店外面等，手插在口袋里，假装在看手机。</p>
        <p class="tl-sub">店员问他是你男朋友吗。他说"我是她哥"。声音太大了。</p>
      </div>
      <button class="tl-more" data-t="d3">+</button>
    </div>
  </div>

  <!-- 17岁 -->
  <div class="tl-event" id="ev4">
    <div class="tl-year">17</div>
    <div class="tl-dot sunset-dot"></div>
    <div class="tl-card sunset-card">
      <div class="tl-sunset"></div>
      <p class="tl-text">白裙子。夕阳。</p>
      <p class="tl-text-s">他移开视线的速度太快了。</p>
      <div class="tl-detail" id="d4">
        <p>你穿着白色碎花裙从教室门口走出来，笑着朝他挥手。</p>
        <p class="tl-sub">那天晚上他失眠到凌晨三点。对着天花板问自己到底怎么了。</p>
      </div>
      <button class="tl-more" data-t="d4">+</button>
    </div>
  </div>

  <!-- 22岁 -->
  <div class="tl-event" id="ev5">
    <div class="tl-year">22</div>
    <div class="tl-dot dark-dot"></div>
    <div class="tl-card dark-card">
      <div class="tl-icon">
        <svg viewBox="0 0 50 36" fill="none">
          <rect x="2" y="2" width="46" height="30" rx="3" stroke="#5a6a80" stroke-width="1.5"/>
          <rect x="6" y="6" width="38" height="22" rx="1" fill="#1a1a2a" class="tv-screen"/>
        </svg>
      </div>
      <p class="tl-text">客厅。电视。他问出了那句话。</p>
      <div class="tl-detail" id="d5">
        <p>五秒钟的沉默。电视里的女主角在哭。</p>
        <p class="tl-sub">他的手不知道什么时候搭上了你的后脑勺。</p>
      </div>
      <button class="tl-more" data-t="d5">+</button>
    </div>
  </div>
</section>

<!-- ── 电视场景 ── -->
<section class="tv-scene">
  <div class="tv-frame">
    <div class="tv-static" id="tvStatic">
      <canvas id="tvCanvas" width="320" height="180"></canvas>
    </div>
    <div class="tv-overlay">
      <p>告诉哥哥。</p>
      <p class="tv-big">你们亲过没有？</p>
    </div>
  </div>
  <div class="tv-light"></div>
</section>

<!-- ── 橘子静物 ── -->
<section class="orange-scene">
  <div class="orange-table">
    <div class="orange-fruit">
      <svg viewBox="0 0 60 60" fill="none">
        <circle cx="30" cy="32" r="22" fill="#e8a060" opacity=".7"/>
        <path d="M30 10 Q32 16 30 20" stroke="#5a8040" stroke-width="1.5"/>
        <ellipse cx="30" cy="10" rx="4" ry="2" fill="#5a8040" opacity=".5"/>
      </svg>
      <div class="peel-bits">
        <span style="left:10px;top:50px;transform:rotate(15deg)"></span>
        <span style="left:60px;top:55px;transform:rotate(-20deg)"></span>
        <span style="left:35px;top:60px;transform:rotate(5deg)"></span>
      </div>
    </div>
    <div class="shadows">
      <div class="shadow-a"></div>
      <div class="shadow-b"></div>
    </div>
  </div>
  <p class="orange-text">茶几上是吃了一半的橘子。</p>
  <p class="orange-text-s">果皮卷成松散的一团。两个人的影子投在墙上。一个在慢慢靠近另一个。</p>
</section>

<!-- ── 接近的手 ── -->
<section class="hand-scene">
  <div class="hand-anim">
    <div class="hand-fingers" id="handFingers">
      <svg viewBox="0 0 80 40" fill="none" stroke="#5a4a3a" stroke-width="1" stroke-linecap="round">
        <path d="M5 30 Q15 28 25 20 Q32 14 40 12 Q48 10 55 12 Q62 14 68 18 Q72 22 75 28"/>
        <path d="M25 20 Q27 14 30 10"/>
        <path d="M35 14 Q36 8 38 5"/>
        <path d="M45 12 Q46 6 47 3"/>
        <path d="M55 14 Q55 8 56 5"/>
      </svg>
    </div>
    <p class="hand-text">他的手不知道什么时候搭上了你的后脑勺——</p>
    <p class="hand-sub">指尖插在你的发间，力度暧昧地悬在"温柔"和"攥紧"之间。</p>
  </div>
</section>

<!-- ── 尾声 ── -->
<section class="ending">
  <blockquote>
    六岁到二十二岁。<br>
    十六年的好哥哥。<br>
    <em>今晚是第一次失败。</em>
  </blockquote>
</section>

<footer>
  <div class="tags">${tg}</div>
</footer>
</main>`,

`*{box-sizing:border-box;margin:0}
html,body{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans SC",sans-serif;-webkit-font-smoothing:antialiased}
.album-world{max-width:680px;margin:0 auto;background:transparent}

/* ═══ 相册封面 ═══ */
.album-cover{margin:20px 16px;background:linear-gradient(145deg,#4a3a28,#3a2a1a,#4a3a28);border-radius:4px 12px 12px 4px;padding:48px 32px;position:relative;overflow:hidden;min-height:280px}
.cover-texture{position:absolute;inset:0;background:url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"><rect width="4" height="4" fill="none"/><rect x="0" y="0" width="1" height="1" fill="rgba(255,255,255,.02)"/></svg>');pointer-events:none}
.cover-spine{position:absolute;left:0;top:0;bottom:0;width:18px;background:linear-gradient(90deg,#2a1a0a,#3a2a18,#2a1a0a);border-radius:4px 0 0 4px}
.cover-title{position:relative;text-align:center;padding-top:40px}
.cover-emboss{font:36px "Songti SC",serif;color:rgba(200,180,140,.25);letter-spacing:12px;text-shadow:1px 1px 0 rgba(200,180,140,.1),-1px -1px 0 rgba(0,0,0,.3)}
.cover-title small{display:block;margin-top:8px;font:9px ui-monospace,monospace;color:rgba(200,180,140,.15);letter-spacing:.2em}
.cover-wear{position:absolute;bottom:20px;right:20px;width:60px;height:60px;border-radius:50%;background:radial-gradient(circle,rgba(255,255,255,.03),transparent);pointer-events:none}
.cover-open{border:0;background:none;color:rgba(200,180,140,.35);font:11px ui-monospace,monospace;cursor:pointer;position:relative;margin-top:40px}

/* ═══ 时间线 ═══ */
.timeline-section{padding:20px 16px 20px 48px;position:relative;display:none}
.timeline-section.show{display:block;animation:fadeIn .6s ease}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}

.tl-event{position:relative;padding:0 0 28px 28px;border-left:2px solid rgba(200,180,140,.15)}
.tl-event:last-child{border-left:none}

.tl-year{position:absolute;left:-38px;top:0;font:24px ui-monospace,monospace;color:rgba(200,180,140,.2);font-weight:700}
.tl-dot{position:absolute;left:-7px;top:6px;width:12px;height:12px;border-radius:50%;background:#e8dcc8;border:3px solid #3a2a1a}
.sunset-dot{background:#e8a060;border-color:#4a2a1a}
.dark-dot{background:#4060a0;border-color:#1a1a2a}

.tl-card{background:rgba(255,255,255,.03);border:1px solid rgba(200,180,140,.08);border-radius:8px;padding:16px;position:relative}
.sunset-card{background:linear-gradient(135deg,rgba(232,160,96,.06),rgba(232,160,96,.02));border-color:rgba(232,160,96,.12)}
.dark-card{background:linear-gradient(135deg,rgba(64,96,160,.06),rgba(64,96,160,.02));border-color:rgba(64,96,160,.12)}

.tl-sunset{position:absolute;top:0;right:0;width:80px;height:60px;background:linear-gradient(180deg,#e8a060,#e86040,#4a2060);opacity:.08;border-radius:0 8px 0 0}

.tl-icon{margin-bottom:8px}
.tl-icon svg{width:30px;height:30px}
.tl-text{font:14px "Songti SC",serif;color:#e8dcc8;line-height:1.6}
.tl-text-s{font:12px "Kaiti SC",serif;color:#8a7a68;margin-top:4px}

.tl-detail{display:none;margin-top:12px;padding:10px;background:rgba(0,0,0,.1);border-radius:4px;animation:fadeIn .4s ease}
.tl-detail.show{display:block}
.tl-detail p{font:13px "Kaiti SC",serif;color:#c8b8a0;line-height:1.7}
.tl-sub{color:#8a7a68;font-size:11px;margin-top:4px;font-style:italic}

.tl-more{position:absolute;top:12px;right:12px;border:1px solid rgba(200,180,140,.15);background:none;color:#8a7a68;width:24px;height:24px;border-radius:50%;cursor:pointer;font-size:14px;line-height:1}

/* ═══ 电视场景 ═══ */
.tv-scene{margin:20px 16px;position:relative}
.tv-frame{background:#1a1a2a;border-radius:8px;padding:16px;position:relative;overflow:hidden}
.tv-static{position:relative;border-radius:4px;overflow:hidden}
.tv-static canvas{width:100%;height:auto;display:block;opacity:.3}
.tv-overlay{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:2}
.tv-overlay p{font:16px "Songti SC",serif;color:rgba(232,220,200,.7)}
.tv-big{font:28px "Songti SC",serif;color:#e8dcc8;margin-top:8px;letter-spacing:4px}
.tv-light{height:4px;background:linear-gradient(90deg,transparent,rgba(64,96,160,.2),transparent);margin-top:2px;border-radius:0 0 4px 4px}

/* ═══ 橘子 ═══ */
.orange-scene{padding:32px 24px;text-align:center}
.orange-table{position:relative;width:fit-content;margin:0 auto 20px}
.orange-fruit{position:relative}
.orange-fruit svg{width:60px}
.peel-bits span{position:absolute;display:block;width:14px;height:8px;background:#e8a060;border-radius:50%;opacity:.3}
.shadows{display:flex;gap:8px;justify-content:center;margin-top:12px}
.shadow-a,.shadow-b{width:30px;height:60px;border-radius:50%;background:rgba(0,0,0,.06)}
.shadow-b{transform:translateX(-8px);animation:lean 4s ease-in-out infinite}
@keyframes lean{0%,100%{transform:translateX(-8px)}50%{transform:translateX(-14px) rotate(-3deg)}}
.orange-text{font:14px "Songti SC",serif;color:#c8b8a0}
.orange-text-s{font:12px "Kaiti SC",serif;color:#8a7a68;margin-top:8px;line-height:1.7}

/* ═══ 手 ═══ */
.hand-scene{padding:32px 24px;text-align:center}
.hand-anim{position:relative}
.hand-fingers{opacity:0;animation:reachOut 3s ease forwards 1s}
@keyframes reachOut{0%{opacity:0;transform:translateX(40px)}100%{opacity:.6;transform:translateX(0)}}
.hand-fingers svg{width:80px;display:block;margin:0 auto}
.hand-text{font:14px "Songti SC",serif;color:#c8b8a0;margin-top:16px}
.hand-sub{font:12px "Kaiti SC",serif;color:#8a7a68;margin-top:8px;line-height:1.7}

/* ═══ 尾声 ═══ */
.ending{padding:40px 24px;text-align:center}
.ending blockquote{color:#c8b8a0;font:20px/1.7 "Songti SC",serif;border:none;padding:0}
.ending em{color:#e8a060;font-style:normal}

/* ═══ footer ═══ */
footer{padding:24px 16px 38px;background:transparent}
.tags{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.tags span{color:#8a7a68;font-size:10px;font-family:ui-monospace,monospace;padding:4px 10px;border:1px solid rgba(200,180,140,.08);border-radius:20px}`,

`// open album
document.getElementById('openAlbum').onclick=()=>{
  document.getElementById('albumCover').style.display='none';
  document.getElementById('timeline').classList.add('show');
};

// timeline expand
document.querySelectorAll('.tl-more').forEach(btn=>{
  btn.onclick=()=>{
    const d=document.getElementById(btn.dataset.t);
    d.classList.toggle('show');
    btn.textContent=d.classList.contains('show')?'−':'+';
  };
});

// TV static
const canvas=document.getElementById('tvCanvas');
if(canvas){
  const ctx=canvas.getContext('2d');
  function drawStatic(){
    const img=ctx.createImageData(320,180);
    for(let i=0;i<img.data.length;i+=4){
      const v=Math.random()*255;
      img.data[i]=v;img.data[i+1]=v;img.data[i+2]=v+Math.random()*20;img.data[i+3]=255;
    }
    ctx.putImageData(img,0,0);
    requestAnimationFrame(drawStatic);
  }
  drawStatic();
}`, 2800)
}
