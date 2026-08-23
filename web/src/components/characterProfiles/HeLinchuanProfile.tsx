import type { CharacterProfileDTO } from '../../services/api'
import { escapeHtml } from '../../utils/escapeHtml'
import { ImmersiveProfileFrame } from './ImmersiveProfileFrame'

interface HeLinchuanProfileProps {
  profile: CharacterProfileDTO
}

/** 贺临川专属详情页：夕照电竞工作室 / 双人房间 / 追求战报。 */
export function HeLinchuanProfile({ profile }: HeLinchuanProfileProps) {
  const name = escapeHtml(profile.display_name || '贺临川')
  const tags = (profile.tags?.length
    ? profile.tags
    : ['女性向', 'BG', '限左', '校园', '电竞'])
    .map((tag) => `<span>${escapeHtml(tag)}</span>`)
    .join('')

  const html = `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box;margin:0;padding:0;letter-spacing:0}
body{background:#10140f;color:#e7e0d2;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;line-height:1.7;padding-bottom:48px}
.shell{max-width:440px;margin:0 auto;padding:0 18px}
.top{padding:24px 0 18px;border-bottom:1px solid rgba(231,190,104,.28)}
.status{display:flex;align-items:center;gap:8px;color:#9fa98e;font-size:11px}
.dot{width:8px;height:8px;border-radius:50%;background:#9fd36c;box-shadow:0 0 12px rgba(159,211,108,.65)}
h2{font-family:"Songti SC","STSong",serif;font-size:29px;color:#fff4dc;margin-top:12px}
.sub{font-size:13px;color:#d8b96f;margin-top:4px}
.quote{margin-top:16px;padding-left:14px;border-left:2px solid #e7be68;color:#c9c3b7;font-size:13px}
.section{padding:23px 0;border-bottom:1px solid rgba(231,190,104,.12)}
.eyebrow{font-size:11px;color:#d8b96f;margin-bottom:12px;font-weight:700}
.panel{background:#191d17;border:1px solid rgba(231,190,104,.2);border-radius:7px;overflow:hidden}
.panel-head{display:flex;justify-content:space-between;background:#e7be68;color:#172012;padding:8px 12px;font-size:11px;font-weight:800}
.rows{padding:7px 13px}
.row{display:flex;gap:13px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.06);font-size:12px}
.row:last-child{border-bottom:0}.key{width:70px;color:#89937e;flex:none}.val{color:#e5ded1;flex:1}
.timeline{position:relative;padding-left:19px}.timeline:before{content:"";position:absolute;left:4px;top:8px;bottom:8px;width:1px;background:#6e7f59}
.event{position:relative;padding:0 0 17px 13px}.event:last-child{padding-bottom:0}.event:before{content:"";position:absolute;left:-18px;top:7px;width:8px;height:8px;background:#e7be68;border:2px solid #10140f;border-radius:50%}
.event b{display:block;color:#f4ead6;font-size:13px}.event p{font-size:11px;color:#929b89;margin-top:3px}
.chat{background:#151a15;border:1px solid rgba(138,160,111,.24);border-radius:7px;padding:14px}
.chat-title{font-size:11px;color:#95a585;padding-bottom:10px;border-bottom:1px solid rgba(255,255,255,.06)}
.msg{display:flex;gap:10px;margin-top:13px}.avatar{width:31px;height:31px;border-radius:6px;background:#34402d;display:flex;align-items:center;justify-content:center;color:#d8b96f;font-size:11px;font-weight:700;flex:none}
.bubble{font-size:12px;color:#d7d1c6;background:#222820;border-radius:3px 7px 7px 7px;padding:8px 10px;max-width:82%}.bubble em{display:block;color:#829078;font-size:10px;font-style:normal;margin-bottom:2px}
.people{display:grid;grid-template-columns:1fr 1fr;gap:8px}.person{border:1px solid rgba(231,190,104,.17);background:#171b15;border-radius:7px;padding:12px}.person b{font-size:13px;color:#f0e3c7}.person small{display:block;color:#d8b96f;font-size:10px;margin:2px 0 6px}.person p{font-size:11px;color:#909988;line-height:1.6}
.match{background:#e9dfcb;color:#20251e;border-radius:7px;padding:18px;position:relative}.match:before{content:"MATCH POINT";display:block;color:#6e784f;font-size:10px;font-weight:800;margin-bottom:10px}.match p{font-family:"Songti SC","STSong",serif;font-size:17px;line-height:1.8}.match footer{text-align:right;font-size:10px;color:#757b6a;margin-top:12px}
.tags{display:flex;flex-wrap:wrap;gap:7px;padding-top:20px}.tags span{border:1px solid rgba(231,190,104,.26);color:#adac9c;border-radius:3px;padding:4px 9px;font-size:10px}
.foot{text-align:center;color:#596154;font-size:10px;padding-top:25px}
</style>
</head>
<body><main class="shell">
  <header class="top">
    <div class="status"><i class="dot"></i>零帧工作室 · 双人训练室已连接</div>
    <h2>${name}</h2>
    <div class="sub">PLAYER 01 · 社长 / 指挥位 / 正在追你</div>
    <p class="quote">“我教你看小地图、算技能冷却、别在逆风局慌。可我最想教会你的，是怎么一眼看出我在偏心。”</p>
  </header>

  <section class="section">
    <div class="eyebrow">玩家档案 · PLAYER CARD</div>
    <div class="panel">
      <div class="panel-head"><span>HE LINCHUAN</span><span>ONLINE</span></div>
      <div class="rows">
        <div class="row"><span class="key">年龄 / 身份</span><span class="val">22岁 · 数字媒体大三 · 校电竞社社长</span></div>
        <div class="row"><span class="key">工作室</span><span class="val">「零帧」主理人 · 负责训练与赛事直播</span></div>
        <div class="row"><span class="key">外貌</span><span class="val">金色碎发 · 浅褐眼睛 · 笑起来明亮，认真时很有压迫感</span></div>
        <div class="row"><span class="key">对外</span><span class="val">可靠、会照顾人、永远能接住场面</span></div>
        <div class="row"><span class="key">对你</span><span class="val">留座、单独复盘、送回宿舍，以及根本藏不住的公开偏爱</span></div>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="eyebrow">追求战报 · 不是社长福利</div>
    <div class="timeline">
      <div class="event"><b>招新赛 · 第一次并肩</b><p>你紧张到按错技能，他没替你操作，只说：“下一波我们一起赢回来。”</p></div>
      <div class="event"><b>第 3 次训练 · 固定座位</b><p>全社团都知道他右手边那台电脑不能坐，因为那是他替你留的位置。</p></div>
      <div class="event"><b>第 7 次散场 · 所谓顺路</b><p>你的宿舍和他的停车点方向相反，他仍然“顺路”了整整两个月。</p></div>
      <div class="event"><b>今天 · 私人房间</b><p>他清空预约、调好你的键位，只等你来，也只等你给一个答案。</p></div>
    </div>
  </section>

  <section class="section">
    <div class="eyebrow">社团群聊 · 19:06</div>
    <div class="chat">
      <div class="chat-title">砚川大学电竞社（48）</div>
      <div class="msg"><span class="avatar">唐</span><div class="bubble"><em>副社长 · 唐栩</em>社长，今晚群训室怎么突然不开放？</div></div>
      <div class="msg"><span class="avatar">贺</span><div class="bubble"><em>${name}</em>设备测试。你们去 A 楼训练。</div></div>
      <div class="msg"><span class="avatar">周</span><div class="bubble"><em>工作室合伙人 · 周策</em>测试设备为什么要摆两杯她喜欢的青提气泡水？</div></div>
      <div class="msg"><span class="avatar">唐</span><div class="bubble"><em>副社长 · 唐栩</em>懂了。今晚不是排位赛，是社长的晋级赛。</div></div>
    </div>
  </section>

  <section class="section">
    <div class="eyebrow">他的生活圈 · TEAM ROSTER</div>
    <div class="people">
      <article class="person"><b>唐栩</b><small>21岁 · 副社长 / 辅助位</small><p>嘴毒心细，最早看穿他改训练表的原因，负责替全社团看热闹。</p></article>
      <article class="person"><b>周策</b><small>23岁 · 零帧合伙人</small><p>前青训选手，沉稳寡言。替他守住今晚的工作室，也提醒他别把人吓跑。</p></article>
      <article class="person"><b>贺闻远</b><small>48岁 · 父亲 / 维修铺老板</small><p>教会他拆第一把键盘的人。嘴上嫌游戏耽误事，直播一场没落下。</p></article>
      <article class="person"><b>你</b><small>大一新生 · 他唯一的例外</small><p>他可以替所有人安排战术，却拿你是真迟钝还是故意装傻毫无办法。</p></article>
    </div>
  </section>

  <section class="section">
    <div class="match"><p>“这么久了，你还能当作没看懂？”<br><br>“这局先欠着。现在告诉我——我能不能正式追你？”</p><footer>零帧工作室 · 夕照落下之前</footer></div>
    <div class="tags">${tags}</div>
  </section>
</main></body></html>`

  return <ImmersiveProfileFrame title={`${profile.display_name || '贺临川'} profile`} html={html} />
}
