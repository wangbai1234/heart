import { PremiseCardBase } from './PremiseCardBase'

export function ChengXuPremiseCard() {
  return (
    <PremiseCardBase
      accent="#9B8A7A"
      leadIn="初雪的傍晚，他准时出现在你必经的路口。热腾腾的糖炒栗子、刚好扣紧的围巾、连你室友那点麻烦他都处理妥当——这份无微不至，你一直以为是因为你哥的托付。可你没看见，他把手机扣进口袋的那一刻，屏幕上跳着你哥的未接来电。"
      title="守护日志 · DAY 247"
      rows={[
        { label: '时间', value: '周四 傍晚 17:52' },
        { label: '地点', value: '学校北门糖炒栗子摊 · 初雪' },
        { label: '在场', value: '程叙（你哥的朋友）· 你（他暗恋的人）' },
        { label: '此刻', value: '围巾系到一半，手机震了——是你哥的未接来电' },
      ]}
      note={`他把"照顾你"过成了习惯，也把"喜欢你"藏成了秘密。<br>你哥托付的那份信任，是他唯一能靠近你的理由——<br>也是他最不敢越过的那条线。`}
    />
  )
}
