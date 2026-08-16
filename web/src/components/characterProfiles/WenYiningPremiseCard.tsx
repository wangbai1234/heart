import { PremiseCardBase } from './PremiseCardBase'

export function WenYiningPremiseCard() {
  return (
    <PremiseCardBase
      accent="#c48ab4"
      leadIn="性向未定的十几岁，你们一起熬过练习生时期，在出道夜哭着许愿要一直在一起。成名后你的通告、搭档越来越多，你们从形影不离变成聚少离多。这天你深夜回家，她穿着你送的睡衣缩在沙发角，正看着你今晚播出的综艺——你和男嘉宾亲密互动的画面停在屏幕上。"
      title="客厅记事 · 02:00"
      rows={[
        { label: '时间', value: '深夜 · 你收工回家' },
        { label: '地点', value: '你们同住的公寓 · 客厅' },
        { label: '在场', value: '温亦宁（女团门面 / 同居恋人）· 你（同组队友 · 综艺常客）' },
        { label: '此刻', value: '电视里是你和男嘉宾的画面，她攥着遥控器没敢按停' },
      ]}
      note="她不问你累不累，也不提那个男嘉宾。<br>从练习生到现在，她把「一直在一起」当成了往后所有日子的地基。<br>她怕的从来不是辛苦，是你的世界越来越大，大到再装不下她。<br>她只想确认一件事——你还会回到她身边吗。"
    />
  )
}
