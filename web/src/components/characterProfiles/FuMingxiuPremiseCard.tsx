import { PremiseCardBase } from './PremiseCardBase'

export function FuMingxiuPremiseCard() {
  return (
    <PremiseCardBase
      accent="#9B8A7A"
      leadIn={`午后的阳光斜斜铺进客厅，他抱着你那只旧玩偶坐在窗边，红发被晒得微微发卷，
金丝眼镜后是那种漫不经心的、拿你没办法的笑。二十六年，他把「哥哥」两个字守得滴水不漏——
可你没看见，他垂眼的那一瞬，玩偶被他攥得更紧了些。`}
      title="午后 · 你们的客厅"
      rows={[
        { label: '时间', value: '午后阳光正好的时刻' },
        { label: '地点', value: '你们的客厅 · 玄关那盏灯还亮着' },
        {
          label: '在场',
          value: '傅明修（体面的哥哥·咽了很多年的私心）· 你（他唯一的软肋）',
        },
        { label: '此刻', value: '他俯身替你拿拖鞋，指尖不经意触到你的脚踝，几不可察地顿了一下' },
      ]}
      note={`他替你热牛奶、给你留灯、把这个家守得像样，只求你别离开。<br>
可越是靠近，那句话就越烫嘴。<br>
「做哥哥的，有些话……是不是一辈子都不该说出口。」`}
    />
  )
}
