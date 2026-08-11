import { PremiseCardBase } from './PremiseCardBase'

export function HuoShiyuPremiseCard() {
  return (
    <PremiseCardBase
      accent="#60a5fa"
      leadIn={`深夜的空教室，只剩你们俩。他刚替你讲完最后一道题，黑发覆额，深色校服的袖口卷到小臂，骨节分明的手放下了铅笔，却没有起身。他安静了很久，忽然偏头看你，清冷的耳尖却红透了——你知不知道，你每次低头做题的时候，我一个字都看不进去。`}
      title="深夜教室 · 23:47"
      rows={[
        { label: '时刻', value: '深夜 23:47 · 最后一题刚讲完' },
        { label: '地点', value: '空教室 · 只剩两人的灯光' },
        { label: '在场', value: '霍时予（年级第一·清冷校草）· 你（他解不出的题）' },
        { label: '此刻', value: '他俯身靠近，声音压得极低，像怕惊扰了这一刻' },
      ]}
      note={`我的人生一直只有标准答案。可你是我遇到的第一道——解不出、又舍不得放弃的题。<br>
今晚别急着走——再陪我坐一会儿，就一会儿。<br>
冷淡是保护色，那点藏不住的在乎，只留给你一个人。`}
    />
  )
}
