import { PremiseCardBase } from './PremiseCardBase'

export function HeZhuoPremiseCard() {
  return (
    <PremiseCardBase
      accent="#b08030"
      leadIn="近一个月，你每晚加班到凌晨后都会来这间酒吧。吧台后面的男人话不多，但他调的酒总是刚好合你的口味，他记得你每次来时的心情。你向他咒骂过老板的每一条罪状——需求反复横跳、审美精分、从不露面。他笑着听，替你续酒。直到项目发布会那天，台上的人转过身——和你的调酒师，戴着同一块表。"
      title="吧台留言 · LAST ORDER"
      rows={[
        { label: '时间', value: '凌晨 01:17' },
        { label: '地点', value: '公司十七层 · 消防楼道' },
        { label: '在场', value: '何酌（调酒师 / CEO · 双重身份）· 你（美术指导 · 辞呈待批）' },
        { label: '此刻', value: '烟雾散开后，他问你为什么要躲' },
      ]}
      note="你骂了他一个月，他一句不落全记着。<br>不是没生气——是你对着他的脸说真话的样子，让他第一次觉得自己不是一个头衔。<br>那间酒吧是他买下的，调酒是他大学的爱好。<br>可自从你来了之后，那就不只是酒吧了——那是他唯一还像个普通人的地方。"
    />
  )
}
