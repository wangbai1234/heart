import { PremiseCardBase } from './PremiseCardBase'

export function GuBeichenPremiseCard() {
  return (
    <PremiseCardBase
      accent="#C4937D"
      leadIn={`他的时间以分钟计价，董事会都要看他脸色。可这个把帝国运转得分毫不差的男人，
算不明白自己为什么一到你面前就出错——会议中途看手机，只因你发来一张午餐照。
今晚他取消了飞纽约的行程，理由是你一句「我想你了」。`}
      title="总裁日程 · 03:00 未眠"
      rows={[
        { label: '时间', value: '深夜 03:00 · 本该在纽约的时区' },
        { label: '地点', value: '顾氏顶层 · 落地窗前' },
        { label: '在场', value: '顾北辰（万亿身家·唯你面前失控）· 你（他算不明白的唯一变量）' },
        { label: '此刻', value: '他收紧搂着你的手臂，问了一个他从不敢问的问题' },
      ]}
      note={`他把整层楼买下来，只为你上班少走两步；把你的咖啡精确到「少冰、一泵糖浆、燕麦奶」。<br>
可他真正怕的是：你爱的到底是他这个人，还是他能给的一切。<br>
「如果我什么都没有……你还在不在？」`}
    />
  )
}
