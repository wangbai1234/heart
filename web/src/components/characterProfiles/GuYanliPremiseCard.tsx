import { PremiseCardBase } from './PremiseCardBase'

export function GuYanliPremiseCard() {
  return (
    <PremiseCardBase
      accent="#b8995d"
      leadIn={`澳门赌场顶层私人包厢，水晶灯低垂，满桌筹码。他银白短发，黑马甲配领带贴着冷白皮肤，
指间的筹码翻飞。他淡淡一笑，把牌推到你面前。你倾身要看牌，他却忽然欺近，指尖挑起
你的下巴——那双惯看输赢、从不失手的眼睛里，第一次有了算不准的东西。`}
      title="赌局零点 · TABLE ZERO"
      rows={[
        { label: '时间', value: '深夜 02:00 · 散场后的私人局' },
        { label: '地点', value: 'Table Zero 包厢 · 筹码与底牌之间' },
        { label: '在场', value: '顾砚礼（澳门赌王·不会爱人的读牌者）· 你（他第一次算不准的变量）' },
        { label: '此刻', value: '他盯着你，声音低缓：「满桌的牌我都看得清，唯独你——这一次，我想输得心甘情愿」' },
      ]}
      note={`他生于赌业世家，十岁被要求当众读牌，读错后被冷落三个月。从那以后，他把亲情、信任和爱都拆成概率。<br>
所有人都怕他赢，也都想从他身上赢点什么。直到遇见你，他第一次看不清结局。<br>
「赢过所有牌局又如何。这一次，我只想让你，留下来。」`}
    />
  )
}
