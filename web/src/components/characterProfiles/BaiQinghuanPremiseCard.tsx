import { PremiseCardBase } from './PremiseCardBase'

export function BaiQinghuanPremiseCard() {
  return (
    <PremiseCardBase
      accent="#D89098"
      leadIn={`江南雨夜，画室里烛火摇曳。他一袭黑白长衫，银白长发松松束着，正对着一幅未完成的画出神。这满京华都当他是块温润的玉，只有你知道——玉里裹着的，是一头被他锁了太久的野兽。今夜，他不想再锁了。`}
      title="春夜画室 · 子时三刻"
      rows={[
        { label: '时辰', value: '子时三刻 · 雨夜' },
        { label: '地界', value: '江南白府 · 画室烛影' },
        { label: '在场', value: '白清欢（世家公子·温润如玉）· 你（唯一看穿他的人）' },
        { label: '此刻', value: '他指尖拈起你耳边一缕碎发，慢条斯理地绕在指间' },
      ]}
      note={`这画里独独缺了一处——我描了整个春天的花，却总觉得少了你的眉眼。<br>
人间烟火千万种，我独爱你眼里那一盏灯。<br>
这个温润公子的骨子里，是一头被锁了太久的温顺野兽——他不是不热烈，是太怕自己的热烈会吓到你。`}
    />
  )
}
