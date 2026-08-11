import { PremiseCardBase } from './PremiseCardBase'

export function XizePremiseCard() {
  return (
    <PremiseCardBase
      accent="#6B7A8C"
      leadIn={`古堡长廊，烛光长长地摇。他垂手立在门边，怀表垂在指尖，微微躬身。
管家的标准距离是三步，可您一抬眼，他眸底那道职业疏离就裂开一线——
三十年的驯服之下，藏着一个他从未说出口的名字：不是主人，是您。`}
      title="庄园值勤录 · HOUR 23:00"
      rows={[
        { label: '时间', value: '夜深露重 · 古堡壁炉已将熄' },
        { label: '地点', value: '长廊尽头 · 您卧房门外' },
        { label: '在场', value: '西泽（完美管家 · 僭越的暗恋）· 你（庄园新主人 · 他唯一敢仰视的人）' },
        { label: '此刻', value: '他替您拉开椅子，抬眼时，职业疏离裂开一线' },
      ]}
      note={`他把忠诚磨成了习惯，可习惯里藏着私心——为您留的灯，总亮到天明。<br>
他问过一次：若能选，想住哪间房。他答"离您最近的那间"，却不敢说"您身边"。<br>
「若您唤的不是'管家'，而是'西泽'——我愿拿这一生的忠诚来换。」`}
    />
  )
}
