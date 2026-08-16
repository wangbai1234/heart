import { PremiseCardBase } from './PremiseCardBase'

export function WeiHengPremiseCard() {
  return (
    <PremiseCardBase
      accent="#7a9ec4"
      leadIn="她住你隔壁十几年，是看你长大、也被你暗恋多年的「姐姐」。警校毕业后她忙到半年没照过面。你成了这条街出名的不良少女——一半是天性，一半是想让她多看你两眼。这次你替人出头动了手，进了局子。来处理的偏偏是她。"
      title="拘留室 · 处理记录"
      rows={[
        { label: '时间', value: '当日 · 你被带进局子后' },
        { label: '地点', value: '市局 · 拘留室' },
        { label: '在场', value: '卫珩（处理警官 / 旧邻）· 你（替人出头的当事人）' },
        { label: '此刻', value: '她看着你脸上的伤，冷着脸抬起你的下巴' },
      ]}
      note="嘴上骂你不省心，先伸手的却总是她。<br>她比你以为的更清楚你为什么变「坏」，也每次都心软地纵容。<br>作为警察她想守分寸，作为看你长大的人她做不到冷心。<br>你在警局门口拉住她手的那一刻，她守的那条界线，早被你踩碎了。"
    />
  )
}
