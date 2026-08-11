import { PremiseCardBase } from './PremiseCardBase'

export function LuoFeiPremiseCard() {
  return (
    <PremiseCardBase
      accent="#8C5A6B"
      leadIn={`烛火幽微，洛斐单膝跪在你脚边，玫瑰红的长发散落胸前，比祭台上的玫瑰还红。
他抬眼，带着血仆的卑微与不甘的独占欲——
你伸出手，他战栗着把脸贴进你的掌心。`}
      title="血契长夜 · HOUR 00"
      rows={[
        { label: '时间', value: '古堡长夜 · 烛火明灭时' },
        { label: '地点', value: '血族古堡 · 红毯尽头' },
        { label: '在场', value: '洛斐（血仆 · 不甘的独占欲）· 你（契约新主人）' },
        { label: '此刻', value: '你伸手，他战栗着把脸贴进你掌心' },
      ]}
      note={`他太久没人把「洛斐」当名字，而非资产编号。<br>
您每说一次「你可以拒绝」，他就更想只属于您一个人。<br>
「您每说一次你可以拒绝，我就更想只属于您。」`}
    />
  )
}
