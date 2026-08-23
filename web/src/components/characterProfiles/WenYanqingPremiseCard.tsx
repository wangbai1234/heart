import { PremiseCardBase } from './PremiseCardBase'

export function WenYanqingPremiseCard() {
  return (
    <PremiseCardBase
      accent="#b36e5a"
      leadIn="闻砚清曾错把走错病房的你当成护工。误会解开以后，你却一次次回来：陪他读书、聊医院外面的生活，也陪他熬过漫长的观察期。你们早已彼此心动，他却总用身体状况回避关系。今天，你发现他瞒着你准备转院。"
      title="住院部 7F · 0712 病房"
      rows={[
        { label: '时间', value: '午后 15:20 · 探视时段' },
        { label: '地点', value: '单人病房 · 窗帘被阳光照得发白' },
        { label: '在场', value: '闻砚清 · 你' },
        { label: '证物', value: '一张被压在书下、尚未提交的转院申请' },
        { label: '此刻', value: '你挡住他躲开的视线，要求他别再替你决定告别' },
      ]}
      note="「喜欢一个随时可能进抢救室的人，不是件值得坚持的事。」<br>你跨坐到他身上，俯身堵住所有逃避的借口。<br>他嘴上让你别闹，发颤的手却攥住了你的手腕。<br>很久以后，他终于承认自己舍不得你走。"
    />
  )
}
