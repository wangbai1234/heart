import { useThemeStore } from '../../stores/themeStore'
import type { CSSProperties } from 'react'

type PremiseArtifactProps = {
  variant: 'surveillance' | 'letter' | 'chart' | 'ledger' | 'edict' | 'catalog' | 'map' | 'stage' | 'memory' | 'system' | 'contract' | 'transcript'
  accent: string
  eyebrow: string
  title: string
  hook: string
  facts: Array<[string, string]>
  quote: string
}

function PremiseArtifact({ variant, accent, eyebrow, title, hook, facts, quote }: PremiseArtifactProps) {
  const dark = useThemeStore((s) => s.resolvedTheme) === 'dark'
  return (
    <section
      className={`bt10-premise bt10-premise-${variant} ${dark ? 'is-dark' : 'is-light'}`}
      style={{ '--premise-accent': accent } as CSSProperties}
    >
      <style>{`
        .bt10-premise{margin:10px 16px 6px;padding:18px;color:var(--premise-ink);background:var(--premise-bg);border:1px solid var(--premise-border);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;letter-spacing:0}.bt10-premise.is-dark{--premise-bg:rgba(27,28,35,.82);--premise-ink:#eeeaf1;--premise-muted:#9995a1;--premise-border:rgba(255,255,255,.1)}.bt10-premise.is-light{--premise-bg:rgba(255,255,255,.82);--premise-ink:#252733;--premise-muted:#747684;--premise-border:rgba(35,37,49,.11)}.bt10-premise *{box-sizing:border-box;letter-spacing:0}.bt10-premise header{display:flex;justify-content:space-between;align-items:center;gap:14px;padding-bottom:12px;border-bottom:1px solid var(--premise-border)}.bt10-premise header small{font:9px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--premise-accent);text-transform:uppercase}.bt10-premise header span{font:9px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--premise-muted)}.bt10-premise h3{margin:14px 0 7px;color:var(--premise-ink);font:600 18px/1.35 "Songti SC","STSong",serif}.bt10-premise .hook{margin:0;color:var(--premise-ink);font:600 15px/1.65 "Songti SC","STSong",serif}.bt10-premise dl{margin:15px 0 0}.bt10-premise dl div{display:grid;grid-template-columns:64px 1fr;gap:10px;padding:8px 0;border-top:1px solid var(--premise-border)}.bt10-premise dt{color:var(--premise-accent);font:10px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace}.bt10-premise dd{margin:0;color:var(--premise-muted);font-size:11px;line-height:1.6}.bt10-premise blockquote{margin:14px 0 0;padding:11px 12px;border-left:2px solid var(--premise-accent);background:color-mix(in srgb,var(--premise-accent) 7%,transparent);color:var(--premise-ink);font:12px/1.7 "Songti SC","STSong",serif}
        .bt10-premise-surveillance{background-image:linear-gradient(rgba(143,119,209,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(143,119,209,.05) 1px,transparent 1px);background-size:24px 24px}.bt10-premise-letter{border-radius:120px 120px 4px 4px;padding-top:28px;text-align:center}.bt10-premise-letter dl div{text-align:left}.bt10-premise-chart{border-top:4px solid var(--premise-accent)}.bt10-premise-ledger{transform:rotate(-.35deg);border-style:dashed}.bt10-premise-edict{border-inline:5px double var(--premise-accent)}.bt10-premise-catalog{box-shadow:7px 7px 0 color-mix(in srgb,var(--premise-accent) 18%,transparent)}.bt10-premise-map{clip-path:polygon(0 2%,46% 0,100% 2%,98% 97%,57% 100%,2% 98%);padding:24px}.bt10-premise-stage{border-bottom:5px solid var(--premise-accent);background-image:linear-gradient(90deg,color-mix(in srgb,var(--premise-accent) 9%,transparent),transparent 25%,transparent 75%,color-mix(in srgb,var(--premise-accent) 9%,transparent))}.bt10-premise-memory{border-radius:0 36px 0 36px}.bt10-premise-system{border-radius:0;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}.bt10-premise-system h3,.bt10-premise-system .hook,.bt10-premise-system blockquote{font-family:ui-monospace,SFMono-Regular,Menlo,"PingFang SC",monospace}.bt10-premise-contract{border:1px dashed var(--premise-accent)}.bt10-premise-transcript{border-left:8px solid color-mix(in srgb,var(--premise-accent) 40%,transparent)}
      `}</style>
      <header><small>{eyebrow}</small><span>STORY HOOK</span></header>
      <h3>{title}</h3>
      <p className="hook">{hook}</p>
      <dl>{facts.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
      <blockquote>{quote}</blockquote>
    </section>
  )
}

export function ZhouJianPremiseCard() {
  return <PremiseArtifact variant="surveillance" accent="#9b81dc" eyebrow="SAFEHOUSE CHANNEL 03" title="庭审前 72 小时" hook="你出狱第一晚，前任周缄持枪走进安全屋，声称自己是你的新保镖。" facts={[["旧案","三年前正是他提交录音，将你送进监狱"],["异常","定罪录音最后 11 秒被人为抹除"],["此刻","袭击者正在楼下切断备用电源"]]} quote="“恨我可以。先活到庭审，再亲口问我为什么背叛你。”" />
}

export function RongZhaoxuePremiseCard() {
  return <PremiseArtifact variant="letter" accent="#6d9d93" eyebrow="合欢殿 · 禁宫婚录" title="皇后的洞房，只等长公主" hook="她是皇帝今夜迎娶的新后，也是三年前与你私定终身后突然失踪的女人。" facts={[["身份","你是成年长公主，她是敌国和亲皇后"],["旧物","凤冠内侧仍刻着你的名字"],["宫门外","皇帝与禁军将在一炷香后抵达"]]} quote="“皇嫂是他们给我的称呼。妻子，才是你给我的。”" />
}

export function ShenCianPremiseCard() {
  return <PremiseArtifact variant="chart" accent="#4f7ea6" eyebrow="NEUROLOGY · SEALED FILE" title="不存在于记忆里的婚姻" hook="婚前体检结束，主诊医生沈辞安递给你一张七年前与你登记的结婚证。" facts={[["诊断","逆行性记忆缺损，缺失 43 天"],["证据","登记、指纹与婚照均通过核验"],["倒计时","你明早将与另一个人办理登记"]]} quote="“我不拦你再婚。先想起来，当年是谁逼你忘了我。”" />
}

export function LuZiPremiseCard() {
  return <PremiseArtifact variant="ledger" accent="#d84b42" eyebrow="DEBT ASSIGNMENT 07-19" title="债权人：陆恣" hook="七年前被你赶出家门的成年养弟，买下了你的全部债务与唯一住所。" facts={[["本金","八百七十万，今晚零点生效"],["条款","债务人必须入住债权人住所"],["关系","无血缘，成年后才成为名义姐弟"]]} quote="“当年你替我决定离开。现在，轮到我替你决定留下。”" />
}

export function XiaoDuPremiseCard() {
  return <PremiseArtifact variant="edict" accent="#9d2833" eyebrow="奉旨行刑 · 倒计时" title="棺木送到府门" hook="萧渡奉旨在天亮前杀你，却先按北境死婚之礼送来自己的棺材。" facts={[["密旨","不得留活口，卯时复命"],["死婚","成契后杀你等同弑亲，他将同罪"],["棺内","躺着一具与你容貌相同的尸体"]]} quote="“嫁我，或者命令我拔刀。天亮前，我只听你这一道旨。”" />
}

export function WeinuoPremiseCard() {
  return <PremiseArtifact variant="catalog" accent="#b12d3d" eyebrow="FUNERAL COLLECTION · LOT 07" title="葬礼后的第七夜" hook="死去的未婚夫从床头玩偶里醒来，而工作室还摆着一具与你同脸的成品。" facts={[["墓地","他的棺椁封条完好"],["玩偶","拥有他的声音、习惯与全部记忆"],["变化","每过一夜，它就更接近真人"]]} quote="“你只需要选，这次想让我活在哪一具身体里。”" />
}

export function HelianJiPremiseCard() {
  return <PremiseArtifact variant="map" accent="#3f9d86" eyebrow="KUNMI NORTH PASS · 4,920M" title="刺客被册为王后" hook="你奉帝国密令来杀雪原新王，赫连霁却在冬祭上把王冠戴到了你头上。" facts={[["任务","冬祭结束前取他首级"],["旧印","你身上的烙印属于失踪七年的王后"],["他知道","你的袖中藏着涂毒短刃"]]} quote="“王后不是称呼，是共犯。先看看帝国为何怕我们成婚。”" />
}

export function ShangZhaoyePremiseCard() {
  return <PremiseArtifact variant="stage" accent="#e13932" eyebrow="MIDNIGHT MASK · SCENE 13" title="下一张面具，是你的脸" hook="每名失踪者死前都收到商照夜制作的面具，而你的那张今晚刚刚完成。" facts={[["身份","你是追案顾问，他是唯一重复出现的傩师"],["法医结论","面具均在死者死亡前完成"],["座位","他为你留了第一排正中的位置"]]} quote="“他们戴上脸才成为死者。你不一样，我想看你摘下来。”" />
}

export function WenHeshengPremiseCard() {
  return <PremiseArtifact variant="memory" accent="#58b6a0" eyebrow="MEMORY TRADE · 05/05" title="最后一段要忘掉的人" hook="戴上他的面具便能借用别人的身份，代价是每次忘记一个爱过的人。" facts={[["已支付","童年、初恋、葬礼与一段无名梦境"],["最后交易","第五段记忆将彻底消失"],["隐藏记录","同一人已被覆盖三次"]]} quote="“最后一段是我。想清楚，你究竟是来忘记谁的？”" />
}

export function QiXuPremiseCard() {
  return <PremiseArtifact variant="system" accent="#9baaff" eyebrow="QX-HOME UNIT 049" title="第四十九次离婚记录" hook="新买的仿生管家拒绝叫你主人，并展示了你们四十九次婚姻注销日志。" facts={[["所有权","购买合同显示你是当前持有人"],["异常","他保留了每次被重置前的记忆"],["第零次","记录被你本人设为永久不可删除"]]} quote="“这是你第四十九次说只是买卖，也是第四十九次回来找我。”" />
}

export function EliasVaynePremiseCard() {
  return <PremiseArtifact variant="contract" accent="#c44a4e" eyebrow="BOUNTY NO. 774" title="刺杀标的亲自来收尾款" hook="你雇佣夜鸦刺杀政治联姻对象，摘下面具的刺客却正是伊莱亚斯本人。" facts={[["白昼","王室指定的吸血鬼未婚夫"],["午夜","从不失手的首席刺客夜鸦"],["合同","刺杀标的与接单人签名完全一致"]]} quote="“你想杀的那个人已经来了。现在决定，要他死还是要他娶你。”" />
}

export function ZhouJimingPremiseCard() {
  return <PremiseArtifact variant="transcript" accent="#8d6052" eyebrow="DIVORCE CASE 2026-117" title="代理律师：丈夫的亲哥哥" hook="周既明替你起诉自己的弟弟，却正是他当年亲手起草婚前协议把你困进这场婚姻。" facts={[["新证据","婚礼前他已知道弟弟长期出轨"],["今晚","丈夫正在楼下要求销毁账本"],["利益冲突","他既能让你赢，也会因此失去整个家族"]]} quote="“婚姻是我帮他赢来的。现在由我帮你结束。然后你再审我。”" />
}
