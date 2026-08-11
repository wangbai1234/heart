import { PremiseCardBase } from './PremiseCardBase'

export function HuoChengPremiseCard() {
  return (
    <PremiseCardBase
      accent="#D97843"
      leadIn={`这个世界已经没有明天了，可他看你的眼神里始终有光。
他把唯一的干净水递给你，自己喝废墟里的污水；把最安全的角落让给你睡，他握着枪蹲在门口到天亮。
今夜丧尸潮退去，他拖着一身血回来，第一件事是确认——你还是热的，还是他的。`}
      title="生存日志 · DAY 1095"
      rows={[
        { label: '时间', value: '深夜 02:30 · 灾变第三年' },
        { label: '地点', value: '废弃军事基地 · 安全屋 #07' },
        { label: '在场', value: '霍城（前特种兵·把你当成唯一软肋）· 你（他杀出废土也要守住的人）' },
        { label: '此刻', value: '他把你抵在墙上，目光灼热，指腹确认你的体温' },
      ]}
      note={`外面死了多少人他不在乎，他只在乎你有没有乖乖等他回来。<br>
他不会说甜言蜜语，但会把「活下去」的名额永远先留给你。<br>
「别死在我前面。求你。」——深夜值守时，他缓慢地握紧你的手`}
    />
  )
}
