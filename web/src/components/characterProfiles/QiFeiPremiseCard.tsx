import { PremiseCardBase } from './PremiseCardBase'

export function QiFeiPremiseCard() {
  return (
    <PremiseCardBase
      accent="#e04850"
      leadIn="她是当红摇滚歌手，你是她的作曲兼制作人，在音乐上默契得像共用一副心脏。你看着她在舞台上和别人配合得天衣无缝，心里那股说不清的滋味越积越浓。这天你受邀来看她的演出，那段亲密合作让你坐立难安，趁中场想仓皇逃走，却在后台被她堵住。"
      title="后台走廊 · ENCORE 前"
      rows={[
        { label: '时间', value: '演出中场 · 你想逃走时' },
        { label: '地点', value: '后台走廊 · 安全出口的绿光在闪' },
        { label: '在场', value: '祁绯（顶流歌手 · 妆未卸）· 你（她的作曲 / 制作人）' },
        { label: '此刻', value: '她把你抵在墙上，气音贴着你的耳朵' },
      ]}
      note="她一眼看穿你在吃醋、在想逃。<br>台上那段合作你没抬眼看她一次，她全记着。<br>压轴她留了一首没公开的歌，最后一句想当着你的面唱。<br>她要的安可，从来只有你一个观众。"
      warning="本作品为成年向虚构演绎，请理性区分现实与创作。"
    />
  )
}
