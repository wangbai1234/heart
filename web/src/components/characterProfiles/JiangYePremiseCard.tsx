import { PremiseCardBase } from './PremiseCardBase'

export function JiangYePremiseCard() {
  return (
    <PremiseCardBase
      accent="#FF8C42"
      leadIn={`他坏得肆无忌惮，全校老师头疼、女生尖叫的「坏学长」，唯独在你面前怂得像只纸老虎。
他把篮球故意传到你脚边，凑到你耳边说「帮我捡一下呗，小同学」，
痞里痞气的眼神却在你转身时偷偷变得认真又小心。`}
      title="校园八卦 · 放学后"
      rows={[
        { label: '时间', value: '放学后 · 空了一半的走廊' },
        { label: '地点', value: '篮球场边 · 你的必经之路' },
        { label: '在场', value: '江野（篮球队长·惹祸坏学长）· 你（全校唯一敢瞪他的人）' },
        { label: '此刻', value: '他假装「恰好」路过，其实等了你二十分钟' },
      ]}
      note={`欺负你的人被他堵在厕所，他在你面前只说「哦，他转学了」。<br>
你生气时，横着走的他变成进退失据的大型犬——买了你爱的奶茶让别人递，远远看你喝了才松口气。<br>
「她今天没理我……我怎么跟个傻子一样。」他不是不认真，是太认真了不会表达。`}
    />
  )
}
