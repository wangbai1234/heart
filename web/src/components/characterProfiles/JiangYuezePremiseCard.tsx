import { PremiseCardBase } from './PremiseCardBase'

export function JiangYuezePremiseCard() {
  return (
    <PremiseCardBase
      accent="#7FB0CE"
      leadIn={`三年前他因为一个误会，加上年轻男人那点可笑的自尊，说了句「我们到此为止」头也不回地走了。
他用三年证明自己错了：去了七个国家、戒酒又复喝、无数个凌晨对着你的对话框一个字也发不出。
现在他回来了——不再骄傲，只求你一个眼神。`}
      title="归来者手记 · DAY 1096"
      rows={[
        { label: '时间', value: '你搬回旧城区的第一个傍晚' },
        { label: '地点', value: '你常去的便利店门口 · 他没进去' },
        { label: '在场', value: '江月泽（迟到三年的深情）· 你（可以选择原谅、试探，或让他继续煎熬）' },
        { label: '此刻', value: '他退后一步，笑得像在割肉：「他对你好吗？好就行。」' },
      ]}
      note={`这三年他瘦了十五斤，把尊严全交了出来。<br>
他不敢靠近，因为觉得自己已经不配。可你深夜独行时，身后二十米他的车灯一直亮着。<br>
如果你愿意回头——这一次，他死也不放手了。`}
    />
  )
}
