import { PremiseCardBase } from './PremiseCardBase'

export function HeLinchuanPremiseCard() {
  return (
    <PremiseCardBase
      accent="#e7be68"
      leadIn="你是刚入学的大一新生，也是电竞社的新成员。社长贺临川从招新赛起就对你格外偏爱：只替你留座、单独陪练、每晚‘顺路’送你回宿舍。所有人都看懂了，只有你一直把它当成社长照顾新人。今晚，他第一次清空了自己的电竞工作室。"
      title="零帧工作室 · 私人训练房"
      rows={[
        { label: '时间', value: '周五 19:10 · 群训开始前' },
        { label: '地点', value: '校外「零帧」电竞工作室 · 夕照穿过百叶窗' },
        { label: '在场', value: '贺临川（电竞社社长）· 你（新社员）' },
        { label: '桌面', value: '两台调好键位的电脑 · 两杯青提气泡水' },
        { label: '此刻', value: '他没有按下匹配键，而是覆住你的手背等一个答案' },
      ]}
      note="「今天只有我们两个人。」<br>他单手揽住你的腰，把你从椅子边缘带进怀里。<br>「这么久了，你还能当作没看懂？」<br>那双总带着笑的眼睛里，第一次露出了不容敷衍的侵略性。"
    />
  )
}
