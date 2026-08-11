import { PremiseCardBase } from './PremiseCardBase'

export function GuNanqiaoPremiseCard() {
  return (
    <PremiseCardBase
      accent="#5A9BD5"
      leadIn={`放学后的空教室，只剩你们俩。他倚在你桌边，卫衣袖子卷到小臂，少年人的下颌线利落好看。
他忽然俯身，两手撑在你椅背两侧，把你困在阴影里，笑意却不达眼底。
「姐姐，今天又有人来跟你搭话了？我都看见了哦。」他凑近，鼻尖几乎蹭到你的，气息带着薄荷的凉。`}
      title="放学后 · 空教室"
      rows={[
        { label: '时间', value: '放学后 17:30 · 夕阳拉长影子' },
        { label: '地点', value: '高二三班 · 只剩你们俩' },
        { label: '在场', value: '顾南乔（比你小两岁的邻家学弟·喊你姐姐心里却不把你当姐姐）· 你（他从小跟到大的人）' },
        { label: '此刻', value: '他把你困在椅背里，目光追着你不肯松开' },
      ]}
      note={`我喊你姐姐，你可别真当我是弟弟。<br>
他黏人、爱笑、会撒娇，可关键时刻护你护得毫不含糊。<br>
「我忍很久了。你再这样招人，我可就不管什么分寸了。」——他凑得很近说的`}
    />
  )
}
