import type { CharacterProfileDTO } from '../../services/api'
import { escapeHtml } from '../../utils/escapeHtml'
import { ImmersiveProfileFrame } from './ImmersiveProfileFrame'

interface WenYanqingProfileProps {
  profile: CharacterProfileDTO
}

/** 闻砚清专属详情页：病房日光 / 访客记录 / 未发送的备忘录。 */
export function WenYanqingProfile({ profile }: WenYanqingProfileProps) {
  const name = escapeHtml(profile.display_name || '闻砚清')
  const tags = (profile.tags?.length
    ? profile.tags
    : ['女性向', 'BG', '限左', '治愈', '病弱'])
    .map((tag) => `<span>${escapeHtml(tag)}</span>`)
    .join('')

  const html = `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box;margin:0;padding:0;letter-spacing:0}
body{background:#eef1ed;color:#263438;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;line-height:1.7;padding-bottom:48px}
.shell{max-width:440px;margin:0 auto;padding:0 18px}
.top{padding:25px 0 19px;border-bottom:1px solid #b8c8c5}
.ward{display:flex;justify-content:space-between;color:#718885;font-size:11px}
h2{font-family:"Songti SC","STSong",serif;font-size:29px;color:#1e3033;margin-top:12px}
.sub{font-size:13px;color:#b36e5a;margin-top:4px}.line{height:3px;width:66px;background:#b36e5a;margin-top:15px}
.section{padding:23px 0;border-bottom:1px solid #ced8d5}.eyebrow{font-size:11px;color:#50716d;margin-bottom:12px;font-weight:700}
.band{background:#f8faf7;border:1px solid #b9c9c6;border-radius:5px;padding:14px;box-shadow:0 5px 18px rgba(62,86,82,.07)}
.band-top{display:flex;justify-content:space-between;align-items:center;padding-bottom:10px;border-bottom:1px dashed #b8c7c4}.band-top b{font-family:"Songti SC","STSong",serif;font-size:19px}.barcode{font-family:monospace;font-size:11px;color:#66817d}
.row{display:flex;gap:12px;padding:8px 0;border-bottom:1px solid #e2e8e5;font-size:12px}.row:last-child{border-bottom:0}.key{width:70px;color:#839592;flex:none}.val{color:#304347;flex:1}
.first{background:#263c3d;color:#e7efeb;border-radius:6px;padding:18px;position:relative;overflow:hidden}.first:after{content:"";position:absolute;right:-18px;top:-28px;width:88px;height:88px;border:20px solid rgba(197,151,111,.16);border-radius:50%}.first small{color:#b9cbc6;font-size:10px}.first p{font-family:"Songti SC","STSong",serif;font-size:15px;line-height:1.9;margin-top:10px;position:relative;z-index:1}.first em{display:block;color:#d7aa82;font-size:12px;margin-top:12px;font-style:normal}
.ledger{border-left:2px solid #8ca7a2;padding-left:15px}.visit{display:grid;grid-template-columns:58px 1fr;gap:10px;padding:10px 0;border-bottom:1px solid #d6dfdc}.visit:last-child{border-bottom:0}.visit time{color:#9b7666;font-family:monospace;font-size:11px}.visit b{font-size:12px;color:#304347}.visit p{font-size:11px;color:#71817e;margin-top:3px}
.notes{background:#f9f6ee;border:1px solid #d8cdb9;border-radius:6px;padding:17px}.notes-head{font-size:10px;color:#987760;padding-bottom:10px;border-bottom:1px solid #e1d5c3}.note{padding:12px 0;border-bottom:1px solid #e7dccb}.note:last-child{border-bottom:0;padding-bottom:0}.note b{font-size:11px;color:#5b6d68}.note p{font-family:"Kaiti SC","STKaiti",serif;font-size:14px;color:#4c5955;margin-top:5px;line-height:1.8}.unsent{font-size:9px;color:#b36e5a;border:1px solid #d7a18f;border-radius:3px;padding:2px 5px;margin-left:6px}
.people{display:grid;grid-template-columns:1fr 1fr;gap:8px}.person{background:#f7f9f6;border:1px solid #c8d4d0;border-radius:6px;padding:12px}.person b{font-size:13px;color:#2f4648}.person small{display:block;color:#a16f5d;font-size:10px;margin:2px 0 6px}.person p{font-size:11px;color:#788985;line-height:1.6}
.transfer{border:1px solid #c6a092;background:#fffaf4;border-radius:6px;padding:17px}.stamp{display:inline-block;color:#a6564e;border:2px solid #bd7770;padding:3px 8px;font-size:10px;font-weight:800;transform:rotate(-3deg);margin-bottom:12px}.transfer p{font-size:12px;color:#596764}.transfer blockquote{font-family:"Songti SC","STSong",serif;color:#263c3d;font-size:17px;line-height:1.85;margin-top:16px;padding-left:13px;border-left:2px solid #b36e5a}
.tags{display:flex;flex-wrap:wrap;gap:7px;padding-top:20px}.tags span{border:1px solid #b9cbc6;color:#627773;background:#f7faf7;border-radius:3px;padding:4px 9px;font-size:10px}.foot{text-align:center;color:#97a6a2;font-size:10px;padding-top:25px}
</style>
</head>
<body><main class="shell">
  <header class="top"><div class="ward"><span>住院部 7F · 0712</span><span>VISITOR RECORD</span></div><h2>${name}</h2><div class="sub">他把每一次告别都说得很体面，只有等待你时从不诚实</div><div class="line"></div></header>

  <section class="section">
    <div class="eyebrow">个人档案 · 不是一张病历</div>
    <div class="band">
      <div class="band-top"><b>${name}</b><span class="barcode">||| || ||| 0712</span></div>
      <div class="row"><span class="key">年龄 / 职业</span><span class="val">25岁 · 自由书籍装帧设计师</span></div>
      <div class="row"><span class="key">外貌</span><span class="val">黑发 · 苍白肤色 · 眼下总带一点睡不好的红</span></div>
      <div class="row"><span class="key">喜欢</span><span class="val">纸张纹理、旧字体、窗边的天气、你带来的无关紧要的小事</span></div>
      <div class="row"><span class="key">习惯</span><span class="val">把疼说轻，把想念藏好，把床头整理成“刚好等你来”的样子</span></div>
      <div class="row"><span class="key">真正害怕</span><span class="val">不是未知的治疗，而是有一天你会后悔选择他</span></div>
    </div>
  </section>

  <section class="section">
    <div class="eyebrow">初见 · 你走错了房间</div>
    <div class="first"><small>FIRST ENCOUNTER · 午后 15:20</small><p>他刚结束检查，把推门进来的你认成新护工，很客气地请你帮忙拉开窗帘。<br>你笑着说：“我只是走错房间。”<br>停了两秒，又替他把阳光放了进来。</p><em>第二天，你为了取落下的东西再次出现。这次谁都没有认错。</em></div>
  </section>

  <section class="section">
    <div class="eyebrow">访客记录 · 关系如何一点点发生</div>
    <div class="ledger">
      <div class="visit"><time>04 / 17</time><div><b>第二次见面</b><p>你带了一杯他不能喝的奶茶，最后自己喝完，陪他聊了整个下午。</p></div></div>
      <div class="visit"><time>05 / 03</time><div><b>一本没看完的书</b><p>他说结尾太吵，等你来了再一起读。其实那本书只剩三页。</p></div></div>
      <div class="visit"><time>05 / 29</time><div><b>第一次错过探视</b><p>他从下午看了十七次门口，晚上却发消息说“今天刚好有点忙”。</p></div></div>
      <div class="visit"><time>TODAY</time><div><b>转院申请</b><p>他又想替你决定离开。这一次，你拿着那张纸堵在他的病床前。</p></div></div>
    </div>
  </section>

  <section class="section">
    <div class="eyebrow">手机备忘录 · 从未发给你</div>
    <div class="notes">
      <div class="notes-head">本地备忘录 / 最后编辑 02:14</div>
      <div class="note"><b>下次想问<span class="unsent">未发送</span></b><p>她上次说工作不顺，后来解决了吗？不要一见面就问病情，先问她。</p></div>
      <div class="note"><b>关于窗帘<span class="unsent">未发送</span></b><p>以前不喜欢下午的光。她第一次来以后，好像也没有那么刺眼。</p></div>
      <div class="note"><b>不能说的话<span class="unsent">未发送</span></b><p>希望明天睁开眼，她还是会推门进来。希望这件事可以发生很多年。</p></div>
    </div>
  </section>

  <section class="section">
    <div class="eyebrow">他的生活圈 · 不只有病房</div>
    <div class="people">
      <article class="person"><b>乔宁</b><small>29岁 · 责任护士</small><p>爽利清醒，见证他从“只是朋友”说到连脚步声都能认出来。</p></article>
      <article class="person"><b>谢遥</b><small>27岁 · 合作编辑</small><p>每周送来书稿，也负责提醒所有人：闻砚清工作起来一样会挑剔得要命。</p></article>
      <article class="person"><b>闻砚秋</b><small>31岁 · 姐姐</small><p>爱他却曾替他决定太多，后来第一个告诉他：“别再替她选择离开。”</p></article>
      <article class="person"><b>你</b><small>常来探视的人 · 他想留下的人</small><p>你不是护工，却比任何人都熟悉他的口是心非，也最知道怎么让他无处可躲。</p></article>
    </div>
  </section>

  <section class="section">
    <div class="eyebrow">今天 · 转院申请被你发现</div>
    <div class="transfer"><span class="stamp">未提交 / RETURNED</span><p>他把申请压在书下，准备像以前一样安静离开。你坐上床沿，一寸寸逼近，堵住了他所有体面的借口。</p><blockquote>“不是不喜欢。是太喜欢了，才不敢让你把以后押在我身上。”<br><br>“如果我不再替你决定……你还愿意留下吗？”</blockquote></div>
    <div class="tags">${tags}</div>
  </section>
</main></body></html>`

  return <ImmersiveProfileFrame title={`${profile.display_name || '闻砚清'} profile`} html={html} />
}
