import { PremiseCardBase } from './PremiseCardBase'

export function PeiTinglanPremiseCard() {
  return (
    <PremiseCardBase
      accent="#8C7A9B"
      leadIn={`音乐厅散场，余音未散。他独坐在钢琴前，领带松开，手指悬在琴键上方——
今晚的第三乐章，那段所有人都说完美的变奏，只有你听出来了他在忍痛。
他转过头，浅粉银发在暗光里像快折断的玫瑰，声音又轻又哑："别走……"
他拉住你的衣角，像抓住最后一根救命稻草。`}
      title="独奏会散场 · 空荡舞台"
      rows={[
        { label: '时间', value: '音乐厅散场 · 灯光渐暗' },
        { label: '地点', value: '空荡舞台 · 钢琴前' },
        {
          label: '在场',
          value: '裴听澜（神童面具 · 破碎依赖）· 你（唯一留到最后的人）',
        },
        {
          label: '此刻',
          value: '他拉住你的衣角，声音又轻又哑，问你能不能再听他弹一遍',
        },
      ]}
      note={`刚才第三段我在忍痛，全世界只有你听出来了。<br>
所有人都爱我的天赋，可你是唯一问过我「疼不疼」的人。<br>
「今晚……只为你一个人弹。」`}
    />
  )
}
